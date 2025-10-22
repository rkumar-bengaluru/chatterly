import asyncio
import time
import queue 
import threading 
import os 
from datetime import datetime, timezone

from chatterly.poc.report.notfication_mgr import NotificationMgr
from chatterly.loop.session import SchedulerSessionManager
from chatterly.utils.constants import LOGGER_NAME, LOGGER_DIR, SESSIONS_DIR
from chatterly.utils.load_json import save_json

def run_session_in_thread(session_mgr):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(session_mgr.run())
    loop.close()

def run_notification_in_thread(notification_engine):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(notification_engine.run())
    loop.close()

class Scheduler:

    def create_new_session(self,user_email, interview_session):

        # create meta data for this session for the user.
        interview_name = interview_session["interview_name"].replace(' ', '_')
        role = interview_session["role"].replace(' ', '_')
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        user_session = SESSIONS_DIR.joinpath(interview_name).joinpath(user_email)
        os.makedirs(user_session, exist_ok=True)
        filename = f"{user_session}/{role}_{timestamp}.json"
        # meta data done.
        questions = []
        for question in interview_session["questions"]:
            tmp_question = {
                "id": question["id"],
                "question": question["question"],
                "timeout": question["timeout"],
                "order": question["order"],
                "wav_file": question["wav_file"],
                "weight": question["weight"],
                "user_answer": "",
                "score": 0.0,
                "rationale": "",
                "next_action": ""
            }
            questions.append(tmp_question)
        utc_today = datetime.now(timezone.utc).date()
        active_session = {
            "interview_name": interview_session["interview_name"],
            "role": interview_session["role"],
            "date": utc_today.strftime('%Y-%m-%d'),
            "user_email": user_email,
            "recording": "",
            "questions": questions
        }
        
        save_json(filename, active_session)

        notification_queue = queue.Queue()
        app_shutdown_event = threading.Event()

        session_mgr = SchedulerSessionManager(notification_queue, active_session ,filename)
        session_thread = threading.Thread(target=run_session_in_thread , 
                                               args=(session_mgr,),
                                               name="SessionThread", daemon=True)
        session_thread.start()

        notification_engine = NotificationMgr(app_shutdown_event, notification_queue, active_session)
        notification_engine = threading.Thread(target=run_notification_in_thread , 
                                               args=(notification_engine,),
                                               name="Notification", daemon=True)
        notification_engine.start()