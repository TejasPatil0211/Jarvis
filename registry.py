import importlib
import inspect
import logging
import os
from typing import ClassVar

try:  # package context: `python -m jarvis.main`
    from .base import Skill
except ImportError:  # script context: `python main.py`
    from base import Skill

logger = logging.getLogger(__name__)

# Only files ending in `_skill.py` are treated as skills. Without this the
# registry tries to import main.py, settings.py and the test files too.
SKILL_SUFFIX = "_skill.py"


def _import_skill_module(filename: str):
    """Import a skill module whether we are running as a package or a script."""
    mod_name = filename[: -len(".py")]
    package = __package__ or ""
    if package:
        try:
            return importlib.import_module(f".{mod_name}", package=package)
        except ImportError:
            pass
    return importlib.import_module(mod_name)


class SkillRegistry:
    _skills: ClassVar[list[Skill]] = []

    @classmethod
    def discover(cls):
        if cls._skills:
            return
        skills_dir = os.path.dirname(os.path.abspath(__file__))
        for filename in sorted(os.listdir(skills_dir)):
            if not filename.endswith(SKILL_SUFFIX):
                continue
            module_name = filename[: -len(".py")]
            try:
                module = _import_skill_module(filename)
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, Skill) and obj is not Skill and obj.__module__ == module.__name__:
                        skill = obj()
                        cls._skills.append(skill)
                        logger.info(f"Registered skill: {skill.name}")
            except (ImportError, AttributeError, TypeError) as e:
                logger.error(f"Failed to load skill {module_name}: {e}")
        logger.info(f"Discovered {len(cls._skills)} skill(s).")

    @classmethod
    def find_skill(cls, user_input: str) -> Skill | None:
        cls.discover()
        for skill in cls._skills:
            if skill.matches(user_input):
                return skill
        return None

    @classmethod
    def execute(cls, user_input: str) -> str | None:
        skill = cls.find_skill(user_input)
        if skill:
            try:
                return skill.handle(user_input)
            except (AttributeError, RuntimeError, TypeError) as e:
                logger.error(f"Error executing skill {skill.name} error: {e}")
                return "Sorry, I encountered an issue while processing your request."
        return None