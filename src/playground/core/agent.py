import asyncio
import threading
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
import uuid
from logger import setup_daily_logger

from state import InteractionState

class Agent:
    def __init__(self, session_manager):
        self.session_manager = session_manager
        self.logger = setup_daily_logger()
        # Placeholder for sounddevice OutputStream (TTS)
        self.tts_engine = None  # Simulated pyttsx3

    async def speak_question(self, question):
        # Simulate TTS with pyttsx3 (not supported in Pyodide, log instead)
        self.logger.info(f"[Agent] Speaking question: {question}")
        # Placeholder: In a desktop environment, use pyttsx3
        # import pyttsx3
        # self.tts_engine = pyttsx3.init()
        # self.tts_engine.say(question)
        # self.tts_engine.runAndWait()
        await asyncio.sleep(0.1)  # Simulate audio playback delay

    async def process_subtask(self, task_id, detail, order):
        start = datetime.now()
        if order == 1:  # Simulate timeout for second question (order == 1)
            await asyncio.sleep(11)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(self.session_manager.executor, self.blocking_subtask, detail)
        self.logger.info(f"[Agent] Subtask processing for Q{task_id[-4:]} took {(datetime.now() - start).total_seconds():.2f}s")
        return result

    def blocking_subtask(self, detail):
        import time
        time.sleep(0.1)
        return f"Processed: {detail}"

    async def run(self):
        while not self.session_manager.shutdown_event.is_set():
            if self.session_manager.active_task_id is None:
                try:
                    task_id, question, timeout, order = await asyncio.wait_for(
                        self.session_manager.question_queue.get(), timeout=5.0
                    )
                    async with self.session_manager.interaction_lock:
                        self.session_manager.active_task_id = task_id
                        self.logger.info(f"\n[Agent] Asking user Q{task_id[-4:]}: {question}")
                        await self.speak_question(question)
                        await self.session_manager.interaction_queue.put(("question", task_id, question))
                    self.session_manager.question_queue.task_done()

                    try:
                        await self.process_question(task_id, order, timeout)
                        if self.session_manager.state[task_id] == InteractionState.COMPLETED:
                            self.session_manager.status[task_id]["status"] = "completed"
                        self.session_manager.active_task_id = None
                    except asyncio.TimeoutError:
                        self.logger.info(f"[Agent] Question Q{task_id[-4:]} timed out due to inactivity after {timeout} seconds.")
                        self.session_manager.state[task_id] = InteractionState.TIMED_OUT
                        self.session_manager.status[task_id]["status"] = "timeout"
                        self.session_manager.active_task_id = None
                        await self.session_manager.clear_interaction_queue(task_id)
                except asyncio.TimeoutError:
                    await asyncio.sleep(0.5)
                    continue

    async def process_question(self, task_id, order, timeout):
        last_activity = datetime.now()
        while self.session_manager.state.get(task_id) not in [InteractionState.COMPLETED, InteractionState.TIMED_OUT]:
            try:
                message_type, msg_task_id, data = await asyncio.wait_for(
                    self.session_manager.interaction_queue.get(), timeout=5.0
                )
            except asyncio.TimeoutError:
                if (datetime.now() - last_activity).total_seconds() >= timeout:
                    raise asyncio.TimeoutError
                continue

            async with self.session_manager.interaction_lock:
                if msg_task_id != task_id:
                    self.logger.info(f"[Agent] Ignoring message for Q{msg_task_id[-4:]}: Not active task")
                    self.session_manager.interaction_queue.task_done()
                    continue

                last_activity = datetime.now()
                if message_type == "subtask_1" and self.session_manager.state.get(task_id) == InteractionState.WAITING_SUBTASK_1:
                    try:
                        start = datetime.now()
                        result = await asyncio.wait_for(self.process_subtask(task_id, data, order), timeout=10.0)
                        self.logger.info(f"[Agent] Subtask 1 result for Q{task_id[-4:]}: {result} (took {(datetime.now() - start).total_seconds():.2f}s)")
                        await self.session_manager.interaction_queue.put(("subtask_1_response", task_id, result))
                    except asyncio.TimeoutError:
                        self.logger.info(f"[Agent] Subtask 1 for Q{task_id[-4:]} timed out.")
                        self.session_manager.state[task_id] = InteractionState.TIMED_OUT
                        self.session_manager.status[task_id]["status"] = "timeout"
                        self.session_manager.active_task_id = None
                        break
                elif message_type == "subtask_2" and self.session_manager.state.get(task_id) == InteractionState.WAITING_SUBTASK_2:
                    try:
                        start = datetime.now()
                        result = await asyncio.wait_for(self.process_subtask(task_id, data, order), timeout=10.0)
                        self.logger.info(f"[Agent] Subtask 2 result for Q{task_id[-4:]}: {result} (took {(datetime.now() - start).total_seconds():.2f}s)")
                        await self.session_manager.interaction_queue.put(("subtask_2_response", task_id, result))
                        self.session_manager.status[task_id]["status"] = "completed"
                        self.session_manager.state[task_id] = InteractionState.COMPLETED
                        self.session_manager.active_task_id = None
                        self.logger.info(f"[Agent] State for Q{task_id[-4:]}: {self.session_manager.state[task_id]}")
                    except asyncio.TimeoutError:
                        self.logger.info(f"[Agent] Subtask 2 for Q{task_id[-4:]} timed out.")
                        self.session_manager.state[task_id] = InteractionState.TIMED_OUT
                        self.session_manager.status[task_id]["status"] = "timeout"
                        self.session_manager.active_task_id = None
                        break
                else:
                    self.logger.info(f"[Agent] Ignoring message: {message_type} for Q{msg_task_id[-4:]}")

                self.session_manager.interaction_queue.task_done()
