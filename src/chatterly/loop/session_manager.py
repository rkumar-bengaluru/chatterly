import asyncio
import threading
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
import uuid
from chatterly.utils.logger import setup_daily_logger
from chatterly.utils.log_exec_time import LogExecutionTime
from chatterly.utils.constants import LOGGER_NAME, LOGGER_DIR
from chatterly.loop.question_queue import QuestionQueue
from chatterly.utils.load_json import load_json_from_file

from chatterly.loop.agent import ChatterlyAgent 
from chatterly.loop.state import AgentUserInteractionState
from chatterly.loop.user import User 
from chatterly.loop.context import TaskContext

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

        file_path = "./data/go_questions.json"  # Replace with your actual file path
        data = load_json_from_file(file_path)
        self.q_queue = QuestionQueue(data)

    def info(self):
        self.logger.info(f"session manager started with agent & timeout={self.session_timeout}")

    async def producer(self):
        question = await self.q_queue.getNext()
        if question is None:
            return None
        task_id = question["id"]
        task = TaskContext(question.get("task"), 
                           question.get("timeout"), 
                           question.get("order"),
                           AgentUserInteractionState.WAITING_FOR_AGENT)
        await self.question_queue.put((task_id, task))
        self.status[task_id] = {
            "question": question.get("task"),
            "status": AgentUserInteractionState.WAITING_FOR_AGENT,
            "answer": None,
            "timeout": question.get("timeout"),
            "order": question.get("order")
        }
            
        self.state[task_id] = AgentUserInteractionState.WAITING_FOR_AGENT
        return task_id
        
        # questions = [
        #     {"id": str(uuid.uuid4()), "question": "How does threading differ from asyncio?", "timeout": 10, "order": 0},
        # ]
        # for q in questions:
        #     task_id = q["id"]
        #     task = TaskContext(q["question"], q["timeout"], q["order"],AgentUserInteractionState.WAITING_FOR_AGENT)
        #     await self.question_queue.put((task_id, task))
        #     self.status[task_id] = {
        #         "question": q["question"],
        #         "status": AgentUserInteractionState.WAITING_FOR_AGENT,
        #         "answer": None,
        #         "timeout": q["timeout"],
        #         "order": q["order"]
        #     }
            
        #     self.state[task_id] = AgentUserInteractionState.WAITING_FOR_AGENT
        # self.logger.info("[Producer] All questions loaded into queue.")

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
        task_id = await self.producer()

        while datetime.now() - start_time < timeout:
            all_done = (self.question_queue.empty() and 
                        self.interaction_queue.empty() and 
                        len(self.q_queue.question_queue) == 0 and
                        all(info["status"] in [AgentUserInteractionState.COMPLETED, AgentUserInteractionState.TIMED_OUT] for info in self.status.values()))
            print((datetime.now() - start_time), timeout, all_done,self.interaction_queue.empty())
            
            if all_done:
                self.logger.info("[SessionManager] All questions answered. Terminating early.")
                break

            if self.state[task_id] == AgentUserInteractionState.COMPLETED:
                self.logger.info("current task is done, let's find next if any")
                task_id = await self.producer()

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
            self.logger.info(f"  Q{task_id[-4:]}: {info['status']} ({info['question']}) with {info['answer']} subtasks")

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