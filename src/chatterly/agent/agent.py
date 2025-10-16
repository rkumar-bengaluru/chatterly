import logging
import edge_tts
import asyncio 
import sounddevice as sd 
from pydub import AudioSegment
import numpy as np
import io

from chatterly.utils.constants import LOGGER_NAME
from chatterly.utils.log_exec_time import LogExecutionTime
from chatterly.audio.audio import AudioChunk

class ChatterlyAgent:

    def __init__(self,agent_queue,cl_queue):
        self.logger = logging.getLogger(LOGGER_NAME)
        self.state = "BEGIN"
        self.agent_queue = agent_queue 
        self.cl_queue = cl_queue
        

    #@LogExecutionTime(label="Agent speaking")
    async def agent_speaking(self,question):
        self.state = "SPEAKING"
        self.logger.info("🔊 Playing agent audio...")
        await self.generate_agent_audio_in_memory(question)
        sd.play(self.agent_chunk.data, self.agent_chunk.frame_rate)
        await asyncio.sleep(len(self.agent_chunk.data) / self.agent_chunk.frame_rate)  # Wait for playback to finish
        sd.stop()
        self.logger.info("✅ Agent finished speaking, asking vad thread to proceed")
        self.cl_queue.sync_q.put("vad_proceed")


    async def generate_agent_audio_in_memory(self, text):
        communicate = edge_tts.Communicate(text, voice="en-US-AriaNeural")
        mp3_bytes = b""

        # Stream audio chunks
        async for chunk in communicate.stream():
            if chunk["type"] == "audio" and chunk["data"]:
                mp3_bytes += chunk["data"]
            elif chunk["type"] == "Error":
                self.logger.error(f"Error from edge-tts: {chunk}")
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

            return self.agent_chunk
        except Exception as e:
            self.logger.error(f"Error processing audio: {e}")
            return None
        

    async def wait_for_messages(self):
        self.logger.info("waiting for incoming messages...")
        self.state = "WAITING_FOR_MESSAGE"
        
        try:
            question = await asyncio.wait_for(self.agent_queue.async_q.get(), timeout=5.0)
            await self.agent_speaking(question)
        except asyncio.TimeoutError:
            self.logger.warning("⏰ No message received within 5 seconds.")

    async def run(self):
        await self.wait_for_messages()

