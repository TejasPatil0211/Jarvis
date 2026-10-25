from datetime import datetime, timezone
from typing import ClassVar

try:  # package context: `python -m jarvis.main`
    from .base import Skill
except ImportError:  # script context: `python main.py`
    from base import Skill


class TimeSkill(Skill):
    name = "time"
    keywords: ClassVar[list[str]] = ["what time", "current time", "time is it", "tell me the time"]

    def handle(self, user_input: str) -> str:
        now = datetime.now(timezone.utc).astimezone().strftime("%I:%M %p")
        return f"It's {now}."
    