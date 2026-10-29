from typing import ClassVar


class Skill:
    """Base class for every skill.

    Subclasses declare their triggers as a class-level `keywords` list:

        class TimeSkill(Skill):
            name = "time"
            keywords: ClassVar[list[str]] = ["what time", "time is it"]

    Do not assign `self.keywords` here. An instance attribute would shadow
    the class-level one with an empty list, and no skill would ever match.
    """

    name: str = ""
    keywords: ClassVar[list[str]] = []

    def __init__(self) -> None:
        # Only default the trigger list when the subclass genuinely has
        # none. Subclasses that set keywords in their own __init__ are
        # unaffected either way.
        if not getattr(self, "keywords", None):
            self.keywords = []

    def matches(self, user_input: str) -> bool:
        text = user_input.lower()
        for keyword in self.keywords:
            # Skip anything that is not a plain string — a nested tuple in a
            # keyword list would otherwise raise TypeError here.
            if not isinstance(keyword, str):
                continue
            needle = keyword.lower().strip()
            if needle and needle in text:
                return True
        return False

    def handle(self, user_input: str) -> str:
        raise NotImplementedError
