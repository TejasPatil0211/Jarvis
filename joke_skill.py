import random
from typing import ClassVar

from base import Skill


class JokeSkill(Skill):
    name = "joke"
    keywords: ClassVar[list[str]] = ["tell me a joke", "make me laugh", "crack a joke"]

    def handle(self, user_input: str) -> str:
        jokes = [
            "Why don’t scientists trust atoms? Because they make up everything.",
            "I told my wife she was drawing her eyebrows too high. She looked surprised.",
            "What do you call a fake noodle? An impasta.",
            "Why did the scarecrow win an award? He was outstanding in his field.",
            "I’m reading a book on anti-gravity. It’s impossible to put down.",
            "What do you call a bear with no teeth? A gummy bear.",
            "Why don’t skeletons fight each other? They don’t have the guts."
            
        ]
        return random.choice(jokes)