import platform 
import pathlib
import os

PUBLISHER = "NeuroProxy"
PRODUCT_NAME = "Chatterly"
VERSION = "0.0.1"

system = platform.system()
if system == "Windows":
    program_base = pathlib.Path(os.environ["PROGRAMDATA"])
    data_base = pathlib.Path(os.environ["APPDATA"])
elif system == "Darwin":
    program_base = pathlib.Path("/Library/Application Support")
else:  # Linux
    program_base = pathlib.Path("/opt")

APP_BASE_DIR = data_base.joinpath(PUBLISHER, PRODUCT_NAME)



APPLICATION_NAME = "chatterly"
LOGGER_NAME = APPLICATION_NAME.lower()
LOGGER_DIR = APP_BASE_DIR.joinpath("logs")

SESSIONS_DIR = APP_BASE_DIR.joinpath("sessions")
os.makedirs(SESSIONS_DIR, exist_ok=True)