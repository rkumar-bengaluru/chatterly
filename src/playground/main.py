import asyncio
import threading
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
import uuid

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

    async def producer(self):
        questions = [
            "What is Python?",
            "Explain asyncio.",
            "What is a coroutine?",
            "How does threading differ from asyncio?",
            "What is the GIL in Python?"
        ]
        for i, q in enumerate(questions):
            task_id = str(uuid.uuid4())
            await self.question_queue.put((task_id, q))
            self.status[task_id] = {"question": q, "status": "pending", "subtasks": 0}
            self.state[task_id] = InteractionState.WAITING_QUESTION
        print("[Producer] All questions loaded into queue.")

    async def user(self):
        while not self.shutdown_event.is_set():
            try:
                message_type, task_id, data = await asyncio.wait_for(self.interaction_queue.get(), timeout=5.0)
            except asyncio.TimeoutError:
                continue

            async with self.interaction_lock:
                if task_id != self.active_task_id:
                    print(f"[User] Ignoring message for Q{task_id[-4:]}: Not active task")
                    self.interaction_queue.task_done()
                    continue

                if message_type == "question" and self.state.get(task_id) == InteractionState.WAITING_QUESTION:
                    print(f"[User] Received question Q{task_id[-4:]}: {data}")
                    self.state[task_id] = InteractionState.WAITING_SUBTASK_1
                    print(f"[User] State for Q{task_id[-4:]}: {self.state[task_id]}")
                    await asyncio.sleep(0.1)
                    response1 = self.generate_response(task_id, 0)
                    print(f"[User] Subtask 1 for Q{task_id[-4:]}: {response1}")
                    await self.interaction_queue.put(("subtask_1", task_id, response1))
                    self.status[task_id]["subtasks"] = 1
                elif message_type == "subtask_1_response" and self.state.get(task_id) == InteractionState.WAITING_SUBTASK_1:
                    print(f"[User] Received agent response for Q{task_id[-4:]}: {data}")
                    self.state[task_id] = InteractionState.WAITING_SUBTASK_2
                    print(f"[User] State for Q{task_id[-4:]}: {self.state[task_id]}")
                    await asyncio.sleep(0.1)
                    response2 = self.generate_response(task_id, 1)
                    print(f"[User] Subtask 2 for Q{task_id[-4:]}: {response2}")
                    await self.interaction_queue.put(("subtask_2", task_id, response2))
                    self.status[task_id]["subtasks"] = 2
                elif message_type == "subtask_2_response" and self.state.get(task_id) == InteractionState.WAITING_SUBTASK_2:
                    print(f"[User] Received agent response for Q{task_id[-4:]}: {data}")
                    self.state[task_id] = InteractionState.COMPLETED
                    print(f"[User] State for Q{task_id[-4:]}: {self.state[task_id]}")
                else:
                    print(f"[User] Ignoring unexpected message: {message_type} for Q{task_id[-4:]}")

                self.interaction_queue.task_done()

    async def agent(self):
        while not self.shutdown_event.is_set():
            if self.active_task_id is None:
                try:
                    task_id, question = await asyncio.wait_for(self.question_queue.get(), timeout=5.0)
                    self.active_task_id = task_id
                    async with self.interaction_lock:
                        print(f"\n[Agent] Asking user Q{task_id[-4:]}: {question}")
                        await self.interaction_queue.put(("question", task_id, question))
                    self.question_queue.task_done()
                except asyncio.TimeoutError:
                    await asyncio.sleep(0.5)
                    continue

            try:
                message_type, task_id, data = await asyncio.wait_for(self.interaction_queue.get(), timeout=5.0)
            except asyncio.TimeoutError:
                continue

            async with self.interaction_lock:
                if task_id != self.active_task_id:
                    print(f"[Agent] Ignoring message for Q{task_id[-4:]}: Not active task")
                    self.interaction_queue.task_done()
                    continue

                if message_type == "subtask_1" and self.state.get(task_id) == InteractionState.WAITING_SUBTASK_1:
                    try:
                        result = await asyncio.wait_for(self.process_subtask(task_id, data), timeout=10.0)
                        print(f"[Agent] Subtask 1 result for Q{task_id[-4:]}: {result}")
                        await self.interaction_queue.put(("subtask_1_response", task_id, result))
                    except asyncio.TimeoutError:
                        print(f"[Agent] Subtask 1 for Q{task_id[-4:]} timed out.")
                        self.state[task_id] = InteractionState.TIMED_OUT
                        self.status[task_id]["status"] = "timeout"
                        self.active_task_id = None
                elif message_type == "subtask_2" and self.state.get(task_id) == InteractionState.WAITING_SUBTASK_2:
                    try:
                        result = await asyncio.wait_for(self.process_subtask(task_id, data), timeout=10.0)
                        print(f"[Agent] Subtask 2 result for Q{task_id[-4:]}: {result}")
                        await self.interaction_queue.put(("subtask_2_response", task_id, result))
                        self.status[task_id]["status"] = "completed"
                        self.active_task_id = None
                    except asyncio.TimeoutError:
                        print(f"[Agent] Subtask 2 for Q{task_id[-4:]} timed out.")
                        self.state[task_id] = InteractionState.TIMED_OUT
                        self.status[task_id]["status"] = "timeout"
                        self.active_task_id = None
                else:
                    print(f"[Agent] Ignoring message: {message_type} for Q{task_id[-4:]}")

                self.interaction_queue.task_done()

    async def process_subtask(self, task_id, detail):
        if task_id.startswith("2"):  # Simulate timeout for second question
            await asyncio.sleep(11)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self.blocking_subtask, detail)

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
        print("[SessionManager] Starting session...")
        start_time = datetime.now()
        timeout = timedelta(minutes=2)  # Changed to 2 minutes

        await self.producer()
        agent_task = asyncio.create_task(self.agent())
        user_task = asyncio.create_task(self.user())

        while datetime.now() - start_time < timeout:
            # Check if all questions are answered
            all_done = (self.question_queue.empty() and 
                        self.interaction_queue.empty() and 
                        all(info["status"] in ["completed", "timeout"] for info in self.status.values()))
            if all_done:
                print("[SessionManager] All questions answered. Terminating early.")
                break
            await asyncio.sleep(0.5)

        print("[SessionManager] Shutting down...")
        self.shutdown_event.set()
        agent_task.cancel()
        user_task.cancel()
        try:
            await agent_task
        except asyncio.CancelledError:
            print("[SessionManager] Agent task cancelled.")
        try:
            await user_task
        except asyncio.CancelledError:
            print("[SessionManager] User task cancelled.")
        self.executor.shutdown(wait=True)
        print("[SessionManager] Final status summary:")
        for task_id, info in sorted(self.status.items(), key=lambda x: x[0]):
            print(f"  Q{task_id[-4:]}: {info['status']} ({info['question']}) with {info['subtasks']} subtasks")

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