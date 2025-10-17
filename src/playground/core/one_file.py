import asyncio
import threading
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
import uuid
from logger import setup_daily_logger

class InteractionState(Enum):
    WAITING_QUESTION = "waiting_question"
    WAITING_SUBTASK_1 = "waiting_subtask_1"
    WAITING_SUBTASK_2 = "waiting_subtask_2"
    COMPLETED = "completed"
    TIMED_OUT = "timed_out"

class SessionManager:
    def __init__(self):
        self.question_queue = asyncio.Queue()
        self.interaction_queue = asyncio.Queue()
        self.status = {}
        self.state = {}
        self.shutdown_event = asyncio.Event()
        self.executor = ThreadPoolExecutor(max_workers=5)
        self.active_task_id = None
        self.interaction_lock = asyncio.Lock()
        self.logger = setup_daily_logger()

    async def producer(self):
        questions = [
            {"id": str(uuid.uuid4()), "question": "What is Python?", "timeout": 10, "order": 0},
            {"id": str(uuid.uuid4()), "question": "Explain asyncio.", "timeout": 10, "order": 1},
            {"id": str(uuid.uuid4()), "question": "What is a coroutine?", "timeout": 10, "order": 2},
            {"id": str(uuid.uuid4()), "question": "How does threading differ from asyncio?", "timeout": 10, "order": 3},
            {"id": str(uuid.uuid4()), "question": "What is the GIL in Python?", "timeout": 10, "order": 4}
        ]
        for q in questions:
            task_id = q["id"]
            await self.question_queue.put((task_id, q["question"], q["timeout"], q["order"]))
            self.status[task_id] = {
                "question": q["question"],
                "status": "pending",
                "subtasks": 0,
                "timeout": q["timeout"],
                "order": q["order"]
            }
            self.state[task_id] = InteractionState.WAITING_QUESTION
        self.logger.info("[Producer] All questions loaded into queue.")

    async def user(self):
        while not self.shutdown_event.is_set():
            try:
                message_type, task_id, data = await asyncio.wait_for(self.interaction_queue.get(), timeout=5.0)
            except asyncio.TimeoutError:
                continue

            async with self.interaction_lock:
                if task_id != self.active_task_id:
                    self.logger.info(f"[User] Ignoring message for Q{task_id[-4:]}: Not active task")
                    self.interaction_queue.task_done()
                    continue

                if message_type == "question" and self.state.get(task_id) == InteractionState.WAITING_QUESTION:
                    self.logger.info(f"[User] Received question Q{task_id[-4:]}: {data}")
                    self.state[task_id] = InteractionState.WAITING_SUBTASK_1
                    self.logger.info(f"[User] State for Q{task_id[-4:]}: {self.state[task_id]}")
                    await asyncio.sleep(0.1)
                    response1 = self.generate_response(task_id, 0)
                    self.logger.info(f"[User] Subtask 1 for Q{task_id[-4:]}: {response1}")
                    await self.interaction_queue.put(("subtask_1", task_id, response1))
                    self.status[task_id]["subtasks"] = 1
                elif message_type == "subtask_1_response" and self.state.get(task_id) == InteractionState.WAITING_SUBTASK_1:
                    self.logger.info(f"[User] Received agent response for Q{task_id[-4:]}: {data}")
                    self.state[task_id] = InteractionState.WAITING_SUBTASK_2
                    self.logger.info(f"[User] State for Q{task_id[-4:]}: {self.state[task_id]}")
                    await asyncio.sleep(0.1)
                    response2 = self.generate_response(task_id, 1)
                    self.logger.info(f"[User] Subtask 2 for Q{task_id[-4:]}: {response2}")
                    await self.interaction_queue.put(("subtask_2", task_id, response2))
                    self.status[task_id]["subtasks"] = 2
                elif message_type == "subtask_2_response" and self.state.get(task_id) == InteractionState.WAITING_SUBTASK_2:
                    self.logger.info(f"[User] Received agent response for Q{task_id[-4:]}: {data}")
                    self.state[task_id] = InteractionState.COMPLETED
                    self.logger.info(f"[User] State for Q{task_id[-4:]}: {self.state[task_id]}")
                    self.active_task_id = None
                else:
                    self.logger.info(f"[User] Ignoring unexpected message: {message_type} for Q{task_id[-4:]}")

                self.interaction_queue.task_done()

    async def agent(self):
        while not self.shutdown_event.is_set():
            if self.active_task_id is None:
                try:
                    task_id, question, timeout, order = await asyncio.wait_for(self.question_queue.get(), timeout=5.0)
                    async with self.interaction_lock:
                        self.active_task_id = task_id
                        self.logger.info(f"\n[Agent] Asking user Q{task_id[-4:]}: {question}")
                        await self.interaction_queue.put(("question", task_id, question))
                    self.question_queue.task_done()

                    # Process question with inactivity timeout
                    try:
                        await self.process_question(task_id, order, timeout)
                        if self.state[task_id] == InteractionState.COMPLETED:
                            self.status[task_id]["status"] = "completed"
                        self.active_task_id = None
                    except asyncio.TimeoutError:
                        self.logger.info(f"[Agent] Question Q{task_id[-4:]} timed out due to inactivity after {timeout} seconds.")
                        self.state[task_id] = InteractionState.TIMED_OUT
                        self.status[task_id]["status"] = "timeout"
                        self.active_task_id = None
                        # await self.clear_interaction_queue(task_id)
                except asyncio.TimeoutError:
                    await asyncio.sleep(0.5)
                    continue

    async def process_question(self, task_id, order, timeout):
        last_activity = datetime.now()
        while self.state.get(task_id) not in [InteractionState.COMPLETED, InteractionState.TIMED_OUT]:
            try:
                message_type, msg_task_id, data = await asyncio.wait_for(self.interaction_queue.get(), timeout=5.0)
            except asyncio.TimeoutError:
                # Check for inactivity timeout
                if (datetime.now() - last_activity).total_seconds() >= timeout:
                    raise asyncio.TimeoutError
                continue

            async with self.interaction_lock:
                if msg_task_id != task_id:
                    self.logger.info(f"[Agent] Ignoring message for Q{msg_task_id[-4:]}: Not active task")
                    self.interaction_queue.task_done()
                    continue

                last_activity = datetime.now()  # Update activity timestamp
                if message_type == "subtask_1" and self.state.get(task_id) == InteractionState.WAITING_SUBTASK_1:
                    try:
                        start = datetime.now()
                        result = await asyncio.wait_for(self.process_subtask(task_id, data, order), timeout=10.0)
                        self.logger.info(f"[Agent] Subtask 1 result for Q{task_id[-4:]}: {result} (took {(datetime.now() - start).total_seconds():.2f}s)")
                        await self.interaction_queue.put(("subtask_1_response", task_id, result))
                    except asyncio.TimeoutError:
                        self.logger.info(f"[Agent] Subtask 1 for Q{task_id[-4:]} timed out.")
                        self.state[task_id] = InteractionState.TIMED_OUT
                        self.status[task_id]["status"] = "timeout"
                        self.active_task_id = None
                        break
                elif message_type == "subtask_2" and self.state.get(task_id) == InteractionState.WAITING_SUBTASK_2:
                    try:
                        start = datetime.now()
                        result = await asyncio.wait_for(self.process_subtask(task_id, data, order), timeout=10.0)
                        self.logger.info(f"[Agent] Subtask 2 result for Q{task_id[-4:]}: {result} (took {(datetime.now() - start).total_seconds():.2f}s)")
                        await self.interaction_queue.put(("subtask_2_response", task_id, result))
                        self.status[task_id]["status"] = "completed"
                        self.state[task_id] = InteractionState.COMPLETED
                        self.logger.info(f"[User] State for Q{task_id[-4:]}: {self.state[task_id]}")
                        self.active_task_id = None
                    except asyncio.TimeoutError:
                        self.logger.info(f"[Agent] Subtask 2 for Q{task_id[-4:]} timed out.")
                        self.state[task_id] = InteractionState.TIMED_OUT
                        self.status[task_id]["status"] = "timeout"
                        self.active_task_id = None
                        break
                else:
                    self.logger.info(f"[Agent] Ignoring message: {message_type} for Q{task_id[-4:]}")

                self.interaction_queue.task_done()

    async def clear_interaction_queue(self, task_id):
        temp_queue = asyncio.Queue()
        while not self.interaction_queue.empty():
            message_type, msg_task_id, data = await self.interaction_queue.get()
            if msg_task_id != task_id:
                await temp_queue.put((message_type, msg_task_id, data))
            self.interaction_queue.task_done()
        while not temp_queue.empty():
            await self.interaction_queue.put(await temp_queue.get())

    async def process_subtask(self, task_id, detail, order):
        start = datetime.now()
        if order == 1:  # Simulate timeout for second question (order == 1)
            await asyncio.sleep(11)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(self.executor, self.blocking_subtask, detail)
        self.logger.info(f"[Agent] Subtask processing for Q{task_id[-4:]} took {(datetime.now() - start).total_seconds():.2f}s")
        return result

    def blocking_subtask(self, detail):
        import time
        time.sleep(0.1)
        return f"Processed: {detail}"

    def generate_response(self, task_id, index):
        responses = [
            "Can you clarify that?",
            "Please summarize it.",
            "Give me an example.",
            "Repeat the key point."
        ]
        return responses[index % len(responses)]

    async def run(self):
        self.logger.info("[SessionManager] Starting session...")
        start_time = datetime.now()
        timeout = timedelta(minutes=2)

        await self.producer()
        agent_task = asyncio.create_task(self.agent())
        user_task = asyncio.create_task(self.user())

        while datetime.now() - start_time < timeout:
            all_done = (self.question_queue.empty() and 
                        self.interaction_queue.empty() and 
                        all(info["status"] in ["completed", "timeout"] for info in self.status.values()))
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