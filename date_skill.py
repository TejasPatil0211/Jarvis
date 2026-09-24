from .base import Skill
from datetime import datetime

class DateSkill(Skill):
    name = "date"
    keywords = [" what is today", "today's date," "current date", "what date"]

    def handle(self, user_input: str) -> str:
        today = datetime.now().strftime("%B %d, %Y")
        return f"Today is (today)."