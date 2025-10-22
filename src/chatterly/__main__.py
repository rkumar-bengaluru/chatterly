# src/my_cool_project/__main__.py
import argparse
from datetime import datetime, timedelta
import sys 
import os 
import time
import asyncio
import numpy as np
import sounddevice as sd
import threading 

from chatterly.cl.commgr import CommunicationLoopMgr
from pathlib import Path
from chatterly.audio.audio import AudioChunk
from chatterly.utils.constants import LOGGER_NAME, LOGGER_DIR, SESSIONS_DIR
from chatterly.utils.logger import setup_daily_logger
from chatterly.utils.load_json import load_json_from_file

import soundfile as sf
import numpy as np
import json 
import asyncio
# from chatterly.poc.edgetts.session import SessionManager
from chatterly.loop.session_manager import SessionManager

async def run_evaluator():
    from chatterly.eval.singleton import get_gemini_evaluator, get_openai_evaluator, get_antropic_evaluator, get_llama_evaluator
        
    model = "gemini-2.0-flash"
    evaluator = await get_gemini_evaluator()
    question = "how Go's goroutines and channels facilitate concurrent programming"
    answer = "Go uses buffered and unbuffered channels to hand over data between go routines, a producer go routine sends data to the channel and consumer consumes it, if the consumer is not ready then the producer waits, which allows the go scheduler to context switch between other waiting go routines to support concurrency?"
    response = await evaluator.evaluate(question=question, answer=answer)

    # Specify the filename
    model = model.replace(".","_")
    filename = f"data/{model}_output.json"

    # Open the file in write mode and use json.dump() to write the data
    try:
         with open(filename, 'w', encoding='utf-8') as f:
            json.dump(response, f, ensure_ascii=False, indent=4)
            print(f"Data successfully written to {filename}")
    except IOError as e:
        print(f"Error writing to file {filename}: {e}")

def run_session_in_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(SessionManager().run())
    loop.close()

async def communication_loop():
    agent_text = "Hello my name is Rupak and I am your agent. Let me know how I can help you today."
    # await generate_agent_audio(agent_text)

    queue = CommunicationLoopMgr()
    await queue.add_new_loop(agent_text)
    await queue.process()

# Wrapper to run the async loop in a thread
def run_async_loop():
    asyncio.run(communication_loop())

def main():
    """Main entry point for the command-line application."""
    parser = argparse.ArgumentParser(
        prog="chatterly",
        description="chatterly CLI.",
    )
    parser.add_argument("command", 
                        help="you need to provide either run",
                        choices=["run", "agent", "llm", "xttsv2","curate","playai","email","session"])
    
    # ---- manual split for read_email ----
    args = parser.parse_args()
   
    logger = setup_daily_logger(name=LOGGER_NAME, log_dir=LOGGER_DIR)
    # Access the 'command' argument and execute the corresponding function
    if args.command == "run":
        # Start child thread
        t = threading.Thread(target=run_async_loop, name="CommLoopThread", daemon=True)
        t.start()
    elif args.command == "agent":
        session_thread = threading.Thread(target=run_session_in_thread , name="SessionThread", daemon=True)
        session_thread.start()
    elif args.command == "llm":
        asyncio.run(run_evaluator())
    elif args.command == "xttsv2":
        from chatterly.poc.xttsv2.gen_voice import generate_speech_xttsv2
        output_path = "./samples/output.wav"
        text = "Hello Rupak, The candidate demonstrates a good understanding of how goroutines and channels facilitate concurrent programming in Go"
        reference_audio = "./recording_1760540826.wav"

        path = generate_speech_xttsv2(text, reference_audio,output_path=output_path)
        logger.info(f"generated file in {path}")
    elif args.command == "playai":
        from chatterly.poc.groq.groq import generate_playai_tts
        output_path = "./samples/output.wav"
        text = "Hello Rupak, The candidate demonstrates a good understanding of how goroutines and channels facilitate concurrent programming in Go"
        reference_audio = "./recording_1760540826.wav"

        path = generate_playai_tts(text, output_path=output_path)
        logger.info(f"generated file in {path}")
    elif args.command == "curate":
        from chatterly.poc.curation.curate_session import QApplication,InterviewApp
        app = QApplication(sys.argv)
        window = InterviewApp()
        window.show()
        sys.exit(app.exec())
        logger.info(f"generated file in {path}")
    elif args.command == "email":
        from chatterly.poc.report.report import InterviewReport
        # load data
        data = load_json_from_file("./data/consolidate.json")
        ir = InterviewReport()
        ir.send_email_report(data)
    elif args.command == "session":
        from chatterly.loop.scheduler import Scheduler
        # load data
        data = load_json_from_file(f"{SESSIONS_DIR}/Python_Interview/Python_Interview_20251022072043.json")
        sch = Scheduler()
        sch.create_new_session("rupak.kumar.ambasta02@gmail.com", data)

    logger.info("Main thread waiting for shutdown...")

    try:
        while True:
            time.sleep(1)  # Idle loop
    except KeyboardInterrupt:
        logger.error("Shutdown signal received. Exiting...")

if __name__ == "__main__":
    main()