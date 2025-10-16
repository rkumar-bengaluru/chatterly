import time
import functools
import asyncio 
import logging 

from chatterly.utils.constants import LOGGER_NAME

class LogExecutionTime:
    def __init__(self, label=None):
        self.logger = logging.getLogger(LOGGER_NAME)
        self.label = label or "Execution"

    def __call__(self, func):
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                start = time.perf_counter()
                result = await func(*args, **kwargs)
                elapsed = time.perf_counter() - start
                self.logger.info(f"⏱️ {self.label} took {elapsed:.2f} seconds.")
                return result
        else:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start = time.perf_counter()
                result = func(*args, **kwargs)
                elapsed = time.perf_counter() - start
                self.logger.info(f"⏱️ {self.label} took {elapsed:.2f} seconds.")
                return result
        return wrapper
