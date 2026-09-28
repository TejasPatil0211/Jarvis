import logging
import re
import threading
import time
from typing import ClassVar

from base import Skill

logger = logging.getLogger(__name__)

class TimerSkill(Skill):
    name = "timer"
    keywords: ClassVar[list[str]] = ["set a timer", "start a timer", "timer for"]

    def handle(self, user_input: str) -> str:
        match = re.search(r"(\d+)\s*(seconds?|secs?|minutes?|mins?)", user_input.lower())
        if not match:
            return "Please specify a duration. Like 5 mins or 2 minutes."
        
        value = int(match.group(1))
        unit = match.group(2)
        if "min" in unit:
            seconds = value * 60 if "min" in unit else value


            threading.Thread(target=self._timer_thread, args=(seconds,), daemon=True
            ).start()
            return f"Timer set for {value} {unit}."

        def _timer_thread(self, seconds):
            time.sleep(seconds)
            logger.info("Timer has ended.")

            try:
                from speaker import Speaker
                Speaker().speak("Timer has ended!")
            except (ImportError, AttributeError, OSError, RuntimeError) as e:
                logger.error(f"Failed to announce timer end: {e}")
