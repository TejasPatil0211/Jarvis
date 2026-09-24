import time
import logging
from functools import wraps

logger = logging.getLogger(__name__)

def retry_with_backoff(func, max_retries=3, base_delay=1.0):
    @wraps(func)
    def wrapper(*args, **kwargs):
        last_exception = None
        for attempt in range(max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Retry {attempt + 1}/{max_retries} for {func.__name__} in {delay:.1f}s: {e}")
                    time.sleep(delay)
                else: 
                    logger.error(f"Max retries failed for {func.__name__}: {e}")

            return "Sorry, I had trouble reaching the service. Please try again later."
        return wrapper
            