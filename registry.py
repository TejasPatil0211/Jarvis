import os
import importlib
import inspect
from typing import Optional, Type, List
from .base import Skill
import logging

logger = logging.getLogger(__name__)

class SkillRegistry:
    _skills: List[Skill] = []

    @classmethod
    def discover(cls):
        if cls._skills:
            return
        skills_dir = os.path.dirname(__file__)
        for filename in os.listdir(skills_dir):
            if filename.endswith(".py") and filename not in ["__init__.py", "base.py", "registry.py"]:
                module_name = f".{filename[:-3]}"
                try:
                    module = importlib.import_module(module_name, package=__package__)
                    for name, obj in inspect.getmembers(module):
                        if inspect.isclass(obj) and issubclass(obj, Skill) and obj is not Skill:
                            skill = obj()
                            cls._skills.append(skill)
                            logger.info(f"Registered skill: {skill.name}")
                except Exception as e:
                    logger.error(f"Failed to load skill {module_name}: {e}")

    @classmethod
    def find_skill(cls, user_input: str) -> Optional[Skill]:
        cls.discover()
        for skill in cls._skills:
            if skill.matches(user_input):
                return skill
        return None

    @classmethod
    def execute(cls, user_input: str) -> Optional[str]:
        skill = cls.find_skill(user_input)
        if skill:
            try:
                return skill.handle(user_input)
            except Exception as e:
                logger.error(f"Error executing skill {skill.name} error: {e}")
                return "Sorry, I encountered an issue while processing your request."
        return None