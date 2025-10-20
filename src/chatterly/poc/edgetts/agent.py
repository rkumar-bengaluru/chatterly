import logging
import edge_tts
import asyncio 
import sounddevice as sd 
from pydub import AudioSegment
import numpy as np
import io
from datetime import datetime, timedelta

from chatterly.utils.logger import setup_daily_logger
from chatterly.utils.constants import LOGGER_NAME, LOGGER_DIR
from chatterly.utils.log_exec_time import LogExecutionTime
from chatterly.audio.audio import AudioChunk
from chatterly.poc.edgetts.state import AgentUserInteractionState

import pdb 

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
                        self.session_manager.active_task = task
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
                            self.session_manager.status[task_id]["status"] = AgentUserInteractionState.TIMED_OUT
                            break
                        await asyncio.sleep(0.5)

                    # Finalize task
                    if self.session_manager.state[task_id] == AgentUserInteractionState.COMPLETED:
                        self.session_manager.status[task_id]["status"] = AgentUserInteractionState.COMPLETED
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
