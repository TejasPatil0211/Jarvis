from typing import List

class Skill:
    name: str = ""
    keywords: List[str] = []

    def matches(self, user_input: str) -> bool:
        text = user_input.lower()
        return any (kw in text for kw in self.keywords)

    def handle(self, user_input: str) -> str:
        raise NotImplementedError
    