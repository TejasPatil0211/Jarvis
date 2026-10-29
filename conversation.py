"""
conversation.py — Shared command routing.

Both the voice loop (main.py) and the text chat (chat.py) send a user
utterance through `handle_command`, so they behave identically.

Routing order:
  1. Keyword-matched skill (time, weather, jokes, timers, documents)
  2. The LLM, with function-calling tools available
"""

import logging

from registry import SkillRegistry

logger = logging.getLogger(__name__)


def handle_command(text: str, brain, use_skills: bool = True) -> tuple[str, str]:
    """
    Route one utterance.

    Returns:
        (response_text, source) where source is "skill:<name>", "llm" or "empty".
    """
    text = (text or "").strip()
    if not text:
        return "", "empty"

    if use_skills:
        try:
            skill = SkillRegistry.find_skill(text)
        except Exception as e:
            logger.warning(f"Skill lookup failed: {e}")
            skill = None

        if skill is not None:
            try:
                response = skill.handle(text)
            except Exception as e:
                logger.error(f"Skill '{skill.name}' failed: {e}")
                response = None
            if response and response.strip():
                response = response.strip()
                # Keep memory consistent with the LLM path.
                try:
                    brain.memory.add_turn(text, response)
                except Exception:
                    pass
                return response, f"skill:{skill.name}"

    try:
        response = brain.process(text)
    except Exception as e:
        logger.error(f"Brain failed: {e}")
        return "Sorry, I had trouble thinking just now.", "error"

    return response, "llm"


def list_skills() -> list[str]:
    """Names of every registered skill, for the /skills command."""
    try:
        SkillRegistry.discover()
    except Exception as e:
        logger.warning(f"Could not load skills: {e}")
        return []
    return sorted(s.name for s in SkillRegistry._skills)
