import importlib
import logging
from retry_helper import retry_with_backoff
try:
    SkillRegistry = importlib.import_module(
        ".skills.registry", package=__package__
    ).SkillRegistry
except ImportError:
    # Support running brain.py directly as well as importing it as a package.
    SkillRegistry = importlib.import_module("skills.registry").SkillRegistry


logger = logging.getLogger(__name__)


try:
    genai = importlib.import_module("google.generativeai")
except ImportError as exc:
    genai = None
    _genai_import_error = exc


class Brain:
    def __init__(self, api_key):
        if genai is None:
            raise ImportError(
                "The google-generativeai package is required to use Brain."
            ) from _genai_import_error
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            "gemini-1.5-flash",
            system_instruction="You are Jarvis, a concise voice assistant. Keep responses under 2 sentences.",
        )
    def process(self, user_input: str) -> str:
         skill_response = SkillRegistry.execute(user_input)
         if skill_response is not None:
              logger.info(f"Skill handled: {skill_response}")
              return skill_response
         return self.get_response(user_input)


    def get_response(self, text):
        try:
            response = self.model.generate_content(text)
            reply = response.text.strip()
            logger.info(f"Gemini reply: {reply}")
            return reply
        except Exception as e:
             logger.error(f"Gemini API error: {e}")
             return "Sorry, I didn't catch that."
