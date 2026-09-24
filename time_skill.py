from .base import Skill
from datetime import datetime

class TimeSkill(Skill):
    name = "time"
    keywords = ["what time", "current time", "time is it", "tell me the time"]

    def handle(self, user_input: str) -> str:
        now = datetime.now().strftime("%I:%M %p")
        return f"It's {now}."
    