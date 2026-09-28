import logging

import google.generativeai as genai  # type: ignore[import-not-found]
from config import GEMINI_MODEL

logger = logging.getLogger(__name__)

try:
    from registry import SkillRegistry
except ImportError as e:
    logger.error(f"Could not load SkillRegistry: {e}")
    SkillRegistry = None

try:
    from memory import ConversationMemory  # type: ignore[import-not-found]
except ImportError:
    ConverstionMemory = None

class Brain:
    def __init__(self, api_key):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(GEMINI_MODEL,
            system_instruction=(
            "You are Jarvis, a concise voice assistant." 
            "Keep responses under 2 sentences."),
        )
        self.memory = ConversationMemory() if ConverstionMemory else None

    def process(self, user_input: str) -> str:
        skill_response = None
        if SkillRegistry is not None:
            skill_response = SkillRegistry.execute(user_input)
        if skill_response is not None:
              logger.info(f"Skill handled: {skill_response}")
              if self.memory:
                  self.memory.add_turn(user_input, skill_response)
              return skill_response
         
        response = self.get_response(user_input)
        if self.memory:
             self.memory.add_turn(user_input, response)
             return response


    def get_response(self, text: str) -> str:
        context_str=""
        if self.memory:
            context = self.memory.get_context()
            if context:
                context_str = "\n".join(
                    f"User: {t['user']}\nAssistant: {t['jarvis']}"
                    for t in context[-5:]
                ) + "\n\n"

                prompt = f"{context_str}User: {text}" if context_str else text
                response = self.model.generate_content(prompt)
                reply = response.text.strip()
                logger.info(f"Gemini reply: {reply}")
                return reply

