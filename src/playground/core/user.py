import asyncio
import threading
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
import uuid
from logger import setup_daily_logger
from state import InteractionState

class User:
    def __init__(self, session_manager):
        self.session_manager = session_manager
        self.logger = session_manager.logger
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
                message_type, task_id, data = await asyncio.wait_for(
                    self.session_manager.interaction_queue.get(), timeout=5.0
                )
            except asyncio.TimeoutError:
                continue

            async with self.session_manager.interaction_lock:
                if task_id != self.session_manager.active_task_id:
                    self.logger.info(f"[User] Ignoring message for Q{task_id[-4:]}: Not active task")
                    self.session_manager.interaction_queue.task_done()
                    continue

                if message_type == "question" and self.session_manager.state.get(task_id) == InteractionState.WAITING_QUESTION:
                    self.logger.info(f"[User] Received question Q{task_id[-4:]}: {data}")
                    self.session_manager.state[task_id] = InteractionState.WAITING_SUBTASK_1
                    self.logger.info(f"[User] State for Q{task_id[-4:]}: {self.session_manager.state[task_id]}")
                    response1 = await self.capture_response(task_id, 0)
                    self.logger.info(f"[User] Subtask 1 for Q{task_id[-4:]}: {response1}")
                    await self.session_manager.interaction_queue.put(("subtask_1", task_id, response1))
                    self.session_manager.status[task_id]["subtasks"] = 1
                elif message_type == "subtask_1_response" and self.session_manager.state.get(task_id) == InteractionState.WAITING_SUBTASK_1:
                    self.logger.info(f"[User] Received agent response for Q{task_id[-4:]}: {data}")
                    self.session_manager.state[task_id] = InteractionState.WAITING_SUBTASK_2
                    self.logger.info(f"[User] State for Q{task_id[-4:]}: {self.session_manager.state[task_id]}")
                    response2 = await self.capture_response(task_id, 1)
                    self.logger.info(f"[User] Subtask 2 for Q{task_id[-4:]}: {response2}")
                    await self.session_manager.interaction_queue.put(("subtask_2", task_id, response2))
                    self.session_manager.status[task_id]["subtasks"] = 2
                elif message_type == "subtask_2_response" and self.session_manager.state.get(task_id) == InteractionState.WAITING_SUBTASK_2:
                    self.logger.info(f"[User] Received agent response for Q{task_id[-4:]}: {data}")
                    self.session_manager.state[task_id] = InteractionState.COMPLETED
                    self.logger.info(f"[User] State for Q{task_id[-4:]}: {self.session_manager.state[task_id]}")
                else:
                    self.logger.info(f"[User] Ignoring unexpected message: {message_type} for Q{task_id[-4:]}")

                self.session_manager.interaction_queue.task_done()
