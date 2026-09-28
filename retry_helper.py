import logging
import time
from functools import wraps

logger = logging.getLogger(__name__)


def retry_with_backoff(func=None, *, max_retries=3, base_delay=1.0):
    """Retry decorator with exponential backoff.

    Works both as @retry_with_backoff and retry_with_backoff().
    """

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries + 1):
                try:
                    return f(*args, **kwargs)
                except (ConnectionError, TimeoutError) as e:
                    if attempt < max_retries:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(
                            "Retry %s/%s for %s in %.1fs: %s",
                            attempt + 1,
                            max_retries,
                            f.__name__,
                            delay,
                            e,
                        )
                        time.sleep(delay)
                        continue

                    logger.error("Max retries failed for %s: %s", f.__name__, e)

            return (
                "Sorry, I had trouble reaching the service."
                "Please try again later."
            )

        return wrapper

    if func is not None:
        return decorator(func)
    return decorator
