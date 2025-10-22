import logging
import edge_tts
import asyncio 
import sounddevice as sd 
from pydub import AudioSegment
import numpy as np
import io
import os 
import time 
from datetime import datetime, timedelta
import queue 
from chatterly.utils.logger import setup_daily_logger
from chatterly.utils.constants import LOGGER_NAME, LOGGER_DIR
from chatterly.poc.report.report import InterviewReport
import pdb 
from chatterly.eval.singleton import get_gemini_evaluator, get_openai_evaluator, get_antropic_evaluator, get_llama_evaluator
from chatterly.utils.load_json import save_json
from chatterly.poc.report.report import InterviewReport

class NotificationMgr:

    def __init__(self,app_shutdown_event, notification_queue, active_session):
        self.logger = setup_daily_logger(name=LOGGER_NAME, log_dir=LOGGER_DIR)
        self.app_shutdown_event = app_shutdown_event
        self.notification_queue = notification_queue
        self.active_session = active_session 
        self.report = InterviewReport()

    
    # get the score for each question
    async def get_question_score(self, task_id, file_name, question, answer):
        model = "gemini-2.0-flash"
        evaluator = await get_gemini_evaluator()
        response = await evaluator.evaluate(question=question, answer=answer)
        model = model.replace(".","_")
        directory = os.path.dirname(file_name)
        print(directory)
        file_path = os.path.join(directory, f"{model}_{task_id[-4:]}output.json")
        save_json(file_path=file_path, settings=response)
        return response
        

    def run(self):
        while not self.app_shutdown_event.is_set():
            try:
                file_name, active_session = self.notification_queue.get(timeout=0.5)
                self.logger.info(f"session finished for {active_session['interview_name']}")
                print(active_session)
                for question in active_session["questions"]:
                    task_id = question["id"]
                    agent_question = question["question"]
                    user_answer = question["user_answer"]
                    status = question["status"]
                    agent_question = question["question"]
                    loop = asyncio.get_event_loop()
                    result = loop.run_until_complete(self.get_question_score(task_id, file_name, agent_question, user_answer))
                    question["score"] = result["score"]
                    question["rationale"] = result["rationale"]
                    question["next_action"] = result["next_action"]

                    self.logger.info(f"  Q{task_id[-4:]}: {status} ({agent_question}) with answer->{user_answer}")
                # save json
                save_json(file_name, active_session)
                # generate the report.
                self.report.send_email_report(active_session)
            except queue.Empty:
                time.sleep(0.5)
                continue
