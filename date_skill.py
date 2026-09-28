from datetime import datetime, timezone
from typing import ClassVar

from base import Skill


class DateSkill(Skill):
    name = "date"
    keywords: ClassVar[list[str | tuple[str, str]]] = [
        " what is today",
        ("today's date,", "current date"),
        "what date",
    ]

    def handle(self, user_input: str) -> str:
        today = datetime.now(tz=timezone.utc).strftime("%B %d, %Y")
        return f"Today is {today}."