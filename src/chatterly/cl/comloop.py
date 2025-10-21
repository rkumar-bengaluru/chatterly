import asyncio
import sounddevice as sd
import numpy as np
import edge_tts
from pydub import AudioSegment
import io
import soundfile as sf
import threading 
import subprocess
import janus

from chatterly.utils.constants import LOGGER_NAME, LOGGER_DIR
from chatterly.utils.logger import setup_daily_logger
from chatterly.refree.refree import Referee
from chatterly.audio.audio import AudioChunk
from chatterly.loop.cl_agent import ChatterlyCLAgent 
from chatterly.loop.vad import BufferedVADCapture

def launch_agent_thread(agent: ChatterlyCLAgent):
        def thread_target():
            asyncio.run(agent.run())  # Runs the agent loop in this thread's event loop

        t = threading.Thread(target=thread_target, name="AgentThread", daemon=True)
        t.start()
        return t

def launch_vad_thread(user: BufferedVADCapture):
        def thread_user():
            asyncio.run(user.run())  # Runs the agent loop in this thread's event loop

        t1 = threading.Thread(target=thread_user, name="VadThread", daemon=True)
        t1.start()
        return t1

class CommunicationLoop:

    def __init__(self, audio_model, agent_chunk):
        self.logger = setup_daily_logger(name=LOGGER_NAME, log_dir=LOGGER_DIR)
        self.audio_model = audio_model

        # queues
        self.cl_queue = janus.Queue()
        self.agent_queue = janus.Queue()
        self.vad_queue = janus.Queue()

        # agent section
        self.agent_chunk = agent_chunk
        self.agent = ChatterlyCLAgent(self.agent_queue,self.cl_queue)
        self.agent_thread = launch_agent_thread(self.agent)

        self.referee = Referee()

        
        self.vad = BufferedVADCapture(vad_queue=self.vad_queue,cl_queue=self.cl_queue)
        self.vad_thread = launch_vad_thread(self.vad)
        self.user_chunks = []
        
    async def run(self):
        
        # wake up the agent.
        self.agent_queue.sync_q.put(self.agent_chunk)

        try:
            self.agent_signal = await asyncio.wait_for(self.cl_queue.async_q.get(), timeout=30.0)
            self.logger.info(self.agent_signal)
        except asyncio.TimeoutError:
            self.logger.error("⏰ No message received within 5 seconds.")

        self.vad_queue.sync_q.put(self.agent_signal)

        try:
            self.vad_signal = await asyncio.wait_for(self.cl_queue.async_q.get(), timeout=30.0)
            self.logger.info(self.vad_signal)
        except asyncio.TimeoutError:
            self.logger.error("⏰ No message received within 5 seconds.")


        
        # self.user_chunks.append(user_data)
        print(self.agent_chunk, self.vad_signal)

        # if self.user_chunks:
        #     score, followup = await self.referee.analyze(self.agent_chunk, self.user_chunks)
        #     if score >= 0.5:
        #         self.logger.info(f"Loop ended with score {score}")
        #     else:
        #         self.logger.info(f"Low score {score}, follow-up: {followup}")
        #         # await queue.requeue(self)
        # else:
        #     self.logger.info("No valid user chunks, requeuing...")
        #     # await queue.requeue(self)