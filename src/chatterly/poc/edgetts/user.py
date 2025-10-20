import asyncio
import threading
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
import uuid
from chatterly.utils.logger import setup_daily_logger
from chatterly.utils.constants import LOGGER_NAME, LOGGER_DIR
from chatterly.poc.edgetts.state import AgentUserInteractionState

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
                    self.session_manager.state[task_id] = AgentUserInteractionState.WAITING_ANSWER
                    response = await self.capture_response(task_id, 0)
                    self.session_manager.status[task_id]["answer"] = response 
                    self.session_manager.state[task_id] = AgentUserInteractionState.COMPLETED
                    self.session_manager.status[task_id]["status"] = AgentUserInteractionState.COMPLETED
                self.session_manager.interaction_queue.task_done()

