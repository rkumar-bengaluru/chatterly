import asyncio
import json
from collections import deque
from typing import Optional
from chatterly.utils.logger import setup_daily_logger
from chatterly.utils.constants import LOGGER_NAME, LOGGER_DIR
from chatterly.utils.load_json import load_json_from_file

class QuestionQueue:
    def __init__(self, json_data: dict):
        sorted_questions = sorted(json_data.get("questions", []), key=lambda q: q.get("order", 0))
        self.question_queue = deque(sorted_questions)
        self.logger = setup_daily_logger(name=LOGGER_NAME, log_dir=LOGGER_DIR)

    async def getNext(self) -> Optional[dict]:
        self.logger.info("next question...")
        return self.question_queue.popleft() if self.question_queue else None



# Example usage
if __name__ == "__main__":
    file_path = "questions.json"  # Replace with your actual file path
    data = load_json_from_file(file_path)
    q_queue = QuestionQueue(data)

    async def run():
        while True:
            question = await q_queue.getNext()
            if question is None:
                print("No more questions.")
                break
            print("Next Question:", question["question"])

    asyncio.run(run())
