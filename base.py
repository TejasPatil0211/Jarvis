

class Skill:
    name: str = ""

    def __init__(self) -> None:
        self.keywords: list[str] = []

    def matches(self, user_input: str) -> bool:
        text = user_input.lower()
        return any(kw in text for kw in self.keywords)

    def handle(self, user_input: str) -> str:
        raise NotImplementedError
    