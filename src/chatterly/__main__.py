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
from chatterly.utils.constants import LOGGER_NAME, LOGGER_DIR
from chatterly.utils.logger import setup_daily_logger

import soundfile as sf
import numpy as np

import asyncio
from chatterly.poc.edgetts.session import SessionManager


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
                        choices=["run", "agent"])
    
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
    
    logger.info("Main thread waiting for shutdown...")

    try:
        while True:
            time.sleep(1)  # Idle loop
    except KeyboardInterrupt:
        logger.error("Shutdown signal received. Exiting...")

if __name__ == "__main__":
    main()