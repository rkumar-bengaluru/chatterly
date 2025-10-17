
import logging
from logging.handlers import TimedRotatingFileHandler
import os
import datetime
import sys 

def setup_daily_logger(
    name: str = "app",
    log_dir: str = "logs",
    log_level: int = logging.INFO,
    log_format: str = "%(asctime)s - %(name)s - %(threadName)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
) -> logging.Logger:
    """
    Set up a daily rotating logger with a single console and file handler.
    This should be called once at the application entry point.
    
    Args:
        name: Root logger name (default: 'app')
        log_dir: Directory to store log files (default: 'logs')
        log_level: Logging level (default: logging.INFO)
        log_format: Log message format (includes filename and line number)
    
    Returns:
        Configured logger instance
    """
    # Get the logger (use named logger to avoid root logger conflicts)
    logger = logging.getLogger(name)
    if logger.hasHandlers():
        logging.debug(f"Logger {name} already configured, returning existing instance")
        return logger
    
    # Disable propagation to prevent root logger handling
    logger.propagate = False
    logger.setLevel(log_level)

    # Clear any existing handlers (in case of partial configuration)
    logger.handlers.clear()

    # Create logs directory if it doesn't exist
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Create daily rotating file handler
    current_date = datetime.date.today()
    formatted_date = current_date.strftime("%Y-%m-%d")
    log_file = os.path.join(log_dir, f"{name}_{formatted_date}.log")
    file_handler = TimedRotatingFileHandler(
        log_file,
        when="midnight",  # Rotate at midnight
        interval=1,       # Rotate every 1 day
        backupCount=30,    # Keep logs for 30 days
        encoding="utf-8"
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(logging.Formatter(log_format))

    # Determine if console logging should be enabled
    is_dev = not getattr(sys, "frozen", False)

    # Create console handler
    if is_dev:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(logging.Formatter(log_format))
        logger.addHandler(console_handler)
    

    # Add handlers to logger
    logger.addHandler(file_handler)

    logging.debug(f"Logger {name} configured with file handler ({log_file}) and console handler")
    return logger