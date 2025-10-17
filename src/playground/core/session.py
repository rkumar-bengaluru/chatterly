import asyncio
import threading
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
import uuid
from logger import setup_daily_logger
from agent import Agent 
from user import User

from state import InteractionState
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
        self.agent = Agent(self)
        self.user = User(self)

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

    async def clear_interaction_queue(self, task_id):
        temp_queue = asyncio.Queue()
        while not self.interaction_queue.empty():
            message_type, msg_task_id, data = await self.interaction_queue.get()
            if msg_task_id != task_id:
                await temp_queue.put((message_type, msg_task_id, data))
            self.interaction_queue.task_done()
        while not temp_queue.empty():
            await self.interaction_queue.put(await temp_queue.get())

    async def run(self):
        self.logger.info("[SessionManager] Starting session...")
        start_time = datetime.now()
        timeout = timedelta(minutes=2)

        await self.producer()
        agent_task = asyncio.create_task(self.agent.run())
        user_task = asyncio.create_task(self.user.run())

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