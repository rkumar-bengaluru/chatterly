import asyncio
import threading
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
import uuid
from chatterly.utils.logger import setup_daily_logger
from chatterly.utils.log_exec_time import LogExecutionTime
from chatterly.poc.edgetts.user import User 
from chatterly.utils.constants import LOGGER_NAME, LOGGER_DIR
import sounddevice as sd 
import logging
import edge_tts
import asyncio 
import sounddevice as sd 
from pydub import AudioSegment
import numpy as np
import io
from datetime import datetime, timedelta

class AudioChunk:
    def __init__(self, data, frame_rate):
        self.data = data
        self.frame_rate = frame_rate
        self.timestamp = asyncio.get_event_loop().time()

class AgentUserInteractionState(Enum):
    WAITING_FOR_AGENT = "waiting_question"
    AGENT_GENERATING_AUDIO = "agent_generating_audio"
    AGENT_GENERATING_AUDIO_DONE = "agent_generating_audio_done"
    AGENT_SPEAKING = "agent_speaking"
    AGENT_SPEAKING_DONE = "agent_speaking_done"
    WAITING_SUBTASK_1 = "waiting_subtask_1"
    WAITING_SUBTASK_2 = "waiting_subtask_2"
    COMPLETED = "completed"
    TIMED_OUT = "timed_out"
    WAITING_QUESTION = "waiting_question"

class TaskContext:

    def __init__(self, task, timeout, order, status):
        self.task = task 
        self.timeout = timeout 
        self.order = order 
        self.status = status 
        self.subtasks = []

class ChatterlyAgent:

    def __init__(self,session_manager):
        self.logger = setup_daily_logger(name=LOGGER_NAME, log_dir=LOGGER_DIR)
        self.session_manager = session_manager 
        
    @LogExecutionTime(label="Agent speaking")
    async def agent_speaking_with_output_stream(self, audio_chunk):
        self.session_manager.state[self.session_manager.active_task_id] = AgentUserInteractionState.AGENT_SPEAKING
        self.logger.info("🔊 Playing agent audio...")

        audio = audio_chunk.data.astype(np.float32)
        samplerate = audio_chunk.frame_rate

        def callback(outdata, frames, time, status):
            if status:
                self.logger.warning(f"Playback status: {status}")
            chunk = audio[callback.pos:callback.pos + frames]
            if len(chunk) < frames:
                outdata[:len(chunk)] = chunk.reshape(-1, 1)
                outdata[len(chunk):] = 0
                raise sd.CallbackStop()
            else:
                outdata[:] = chunk.reshape(-1, 1)
            callback.pos += frames

        callback.pos = 0

        with sd.OutputStream(samplerate=samplerate, channels=1, dtype='float32', callback=callback):
            duration = len(audio) / samplerate
            await asyncio.sleep(duration)

        self.logger.info("✅ Agent finished speaking, asking vad thread to proceed")
        self.session_manager.state[self.session_manager.active_task_id] = AgentUserInteractionState.AGENT_SPEAKING_DONE


    @LogExecutionTime(label="Agent speaking")
    async def agent_speaking(self,question):
        self.session_manager.state[self.session_manager.active_task_id] = AgentUserInteractionState.AGENT_SPEAKING
        self.logger.info("🔊 Playing agent audio...")
        await self.generate_agent_audio_in_memory(question)
        sd.play(self.agent_chunk.data, self.agent_chunk.frame_rate)
        await asyncio.sleep(len(self.agent_chunk.data) / self.agent_chunk.frame_rate)  # Wait for playback to finish
        sd.stop()
        self.logger.info("✅ Agent finished speaking, asking vad thread to proceed")
        self.session_manager.state[self.session_manager.active_task_id] = AgentUserInteractionState.AGENT_SPEAKING_DONE

    @LogExecutionTime(label="Generating Audio")
    async def generate_agent_audio_in_memory(self, text):
        self.session_manager.state[self.session_manager.active_task_id] = AgentUserInteractionState.AGENT_GENERATING_AUDIO
        communicate = edge_tts.Communicate(text, voice="en-US-AriaNeural")
        
        mp3_bytes = b""
        # Stream audio chunks
        async for chunk in communicate.stream():
            if chunk["type"] == "audio" and chunk["data"]:
                mp3_bytes += chunk["data"]
            elif chunk["type"] == "Error":
                return None
        if not mp3_bytes:
            self.logger.error("Error: No audio data received")
            return None
        try:
            # Decode MP3 to waveform
            audio = AudioSegment.from_file(io.BytesIO(mp3_bytes), format="mp3")
            samples = np.array(audio.get_array_of_samples()).astype("float32")
            if audio.channels == 2:
                samples = samples.reshape((-1, 2))
            # Normalize samples 
            max_val = np.max(np.abs(samples))
            if max_val > 0:
                samples /= max_val
            else:
                self.logger.warning("Warning: Audio samples are empty or silent")

            self.agent_chunk = AudioChunk(samples, audio.frame_rate)
            self.session_manager.state[self.session_manager.active_task_id] = AgentUserInteractionState.AGENT_GENERATING_AUDIO_DONE
            return self.agent_chunk
        except Exception as e:
            self.logger.error(f"Error processing audio: {e}")
            return None
    
    async def speak_question(self, question):
        # Simulate TTS with pyttsx3 (not supported in Pyodide, log instead)
        self.logger.info(f"[Agent] Speaking question: {question}")
        audio_chunk = await self.generate_agent_audio_in_memory(question)
        await self.agent_speaking_with_output_stream(audio_chunk)

        # Placeholder: In a desktop environment, use pyttsx3
        # import pyttsx3
        # self.tts_engine = pyttsx3.init()
        # self.tts_engine.say(question)
        # self.tts_engine.runAndWait()

    async def run(self):
        while not self.session_manager.shutdown_event.is_set():
            if self.session_manager.active_task_id is None:
                try:
                    self.logger.info("waiting for question_queue")
                    task_id, task = await asyncio.wait_for(
                        self.session_manager.question_queue.get(), timeout=5.0
                    )
                    async with self.session_manager.interaction_lock:
                        self.session_manager.active_task_id = task_id
                        self.session_manager.active_task = task.task
                        await self.speak_question(task.task)
                        await self.session_manager.interaction_queue.put(("user_turn", task_id, task.task))
                    self.session_manager.question_queue.task_done()

                    # Passive wait for user response or timeout
                    start_time = datetime.now()
                    while self.session_manager.state.get(task_id) not in [
                        AgentUserInteractionState.COMPLETED,
                        AgentUserInteractionState.TIMED_OUT
                    ]:
                        if (datetime.now() - start_time).total_seconds() > task.timeout:
                            self.session_manager.state[task_id] = AgentUserInteractionState.TIMED_OUT
                            self.session_manager.status[task_id]["status"] = "timeout"
                            break
                        await asyncio.sleep(0.5)

                    # Finalize task
                    if self.session_manager.state[task_id] == AgentUserInteractionState.COMPLETED:
                        self.session_manager.status[task_id]["status"] = "completed"
                    self.session_manager.active_task_id = None

                except asyncio.TimeoutError:
                    await asyncio.sleep(0.5)
                    continue

    # async def process_question(self, task_id, order, timeout):
    #     last_activity = datetime.now()
    #     while self.session_manager.state.get(task_id) not in [AgentUserInteractionState.COMPLETED, AgentUserInteractionState.TIMED_OUT]:
    #         try:
    #             self.logger.info("agent waiting for interaction queue....")
    #             message_type, msg_task_id, data = await asyncio.wait_for(
    #                 self.session_manager.interaction_queue.get(), timeout=5.0
    #             )
    #         except asyncio.TimeoutError:
    #             self.logger.error("agent timing out waiting on interaction queue")
    #             if (datetime.now() - last_activity).total_seconds() >= timeout:
    #                 raise asyncio.TimeoutError
    #             continue

class User:
    def __init__(self, session_manager):
        self.session_manager = session_manager
        self.logger = setup_daily_logger(name=LOGGER_NAME, log_dir=LOGGER_DIR)
        # Placeholder for sounddevice InputStream (STT)
        self.stt_engine = None  # Simulated speech_recognition

    async def capture_response(self, task_id, index):
        # Simulate STT with speech_recognition (not supported in Pyodide, log instead)
        self.logger.info(f"[User] Capturing audio response for Q{task_id[-4:]}")
        # Placeholder: In a desktop environment, use speech_recognition
        # import speech_recognition as sr
        # recognizer = sr.Recognizer()
        # with sr.Microphone() as source:
        #     audio = recognizer.listen(source, timeout=5)
        #     response = recognizer.recognize_google(audio)
        # For now, return hardcoded response
        responses = [
            "Can you clarify that?",
            "Please summarize it.",
            "Give me an example.",
            "Repeat the key point."
        ]
        response = responses[index % len(responses)]
        self.logger.info(f"[User] STT response for Q{task_id[-4:]}: {response}")
        await asyncio.sleep(0.1)  # Simulate audio capture delay
        return response

    async def run(self):
        while not self.session_manager.shutdown_event.is_set():
            try:
                self.logger.info("waiting for interaction_queuec")
                message_type, task_id, data = await asyncio.wait_for(
                    self.session_manager.interaction_queue.get(), timeout=5.0
                )
            except asyncio.TimeoutError:
                continue

            async with self.session_manager.interaction_lock:
                if task_id != self.session_manager.active_task_id:
                    self.session_manager.interaction_queue.task_done()
                    continue

                if message_type == "user_turn" and self.session_manager.state.get(task_id) == AgentUserInteractionState.AGENT_SPEAKING_DONE:
                    self.session_manager.state[task_id] = AgentUserInteractionState.WAITING_SUBTASK_1
                    response1 = await self.capture_response(task_id, 0)
                    self.session_manager.state[task_id] = AgentUserInteractionState.COMPLETED
                    self.session_manager.status[task_id]["status"] = "completed"
                self.session_manager.interaction_queue.task_done()




class SessionManager:
    def __init__(self, session_timeout = 1):
        self.question_queue = asyncio.Queue()
        self.interaction_queue = asyncio.Queue()
        self.status = {}
        self.state = {}
        self.shutdown_event = asyncio.Event()
        self.executor = ThreadPoolExecutor(max_workers=5)
        self.active_task_id = None
        self.active_task = None 
        self.interaction_lock = asyncio.Lock()
        self.logger = setup_daily_logger(name=LOGGER_NAME, log_dir=LOGGER_DIR)
        self.agent = ChatterlyAgent(self)
        self.session_timeout = session_timeout
        self.user = User(self)

    def info(self):
        self.logger.info(f"session manager started with agent & timeout={self.session_timeout}")

    async def producer(self):
        questions = [
            {"id": str(uuid.uuid4()), "question": "How does threading differ from asyncio?", "timeout": 10, "order": 0},
        ]
        for q in questions:
            task_id = q["id"]
            task = TaskContext(q["question"], q["timeout"], q["order"],AgentUserInteractionState.WAITING_FOR_AGENT)
            await self.question_queue.put((task_id, task))
            # await self.question_queue.put((task_id, task))
            self.status[task_id] = {
                "question": q["question"],
                "status": "pending",
                "subtasks": 0,
                "timeout": q["timeout"],
                "order": q["order"]
            }
            self.state[task_id] = AgentUserInteractionState.WAITING_FOR_AGENT
        self.logger.info("[Producer] All questions loaded into queue.")

    # async def clear_interaction_queue(self, task_id):
    #     temp_queue = asyncio.Queue()
    #     while not self.interaction_queue.empty():
    #         message_type, msg_task_id, data = await self.interaction_queue.get()
    #         if msg_task_id != task_id:
    #             await temp_queue.put((message_type, msg_task_id, data))
    #         self.interaction_queue.task_done()
    #     while not temp_queue.empty():
    #         await self.interaction_queue.put(await temp_queue.get())


    async def run(self):
        self.logger.info("[SessionManager] Starting session")
        start_time = datetime.now()
        timeout = timedelta(minutes=self.session_timeout)
        
        self.logger.info("[SessionManager] starting agent...")
        agent_task = asyncio.create_task(self.agent.run())
        user_task = asyncio.create_task(self.user.run())

        # simulating a question to agent.
        await self.producer()

        while datetime.now() - start_time < timeout:
            all_done = (self.question_queue.empty() and 
                        self.interaction_queue.empty() and 
                        all(info["status"] in ["completed", "timeout"] for info in self.status.values()))
            print((datetime.now() - start_time), timeout, all_done,self.interaction_queue.empty())
            if all_done:
                self.logger.info("[SessionManager] All questions answered. Terminating early.")
                break
            await asyncio.sleep(0.5)
        
        self.logger.info("[SessionManager] Shutting down...")
        self.shutdown_event.set()
        agent_task.cancel()
        user_task.cancel()

        try:
            await agent_task
        except asyncio.CancelledError:
            self.logger.info("[SessionManager] Agent task cancelled.")

        try:
            await user_task
        except asyncio.CancelledError:
            self.logger.info("[SessionManager] User task cancelled.")
        
        self.executor.shutdown(wait=True)
        print(self.status.items())
        self.logger.info("[SessionManager] Final status summary:")
        for task_id, info in sorted(self.status.items(), key=lambda x: x[1]["order"]):
            self.logger.info(f"  Q{task_id[-4:]}: {info['status']} ({info['question']}) with {info['subtasks']} subtasks")

def run_session_in_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(SessionManager().run())
    loop.close()

def run_main():
    session_thread = threading.Thread(target=run_session_in_thread)
    session_thread.start()

    try:
        while session_thread.is_alive():
            session_thread.join(timeout=1)
    except KeyboardInterrupt:
        print("\n[Main] Ctrl+C received. Shutting down...")
    finally:
        print("[Main] SessionManager thread exited.")

if __name__ == "__main__":
    run_main()