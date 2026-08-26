import google.generativeai as genai 
import logging
from config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_SYSTEM_PROMPT

logger = logging.getLogger(_name_)

class Brain:
    def _init_(self):
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            self.model = genai.GenerativeModel(
                model_name=GEMINI_MODEL,
                system_instruction=GEMINI_SYSTEM_PROMPT
            )
            logger.info("Brain initialised with Gemini API")
        except Exception as e:
            logger.error(f"Failed to initialize brain: {e}")
            self.model = None

    def get_response(self, user_input):
        """Get response from Gemini for user input"""
        if not self.model:
            logger.error("Brain not initialised")
            return "Sorry, I'm having trouble connecting right now."

        if not user_input or not user_input.strip():
            logger.warning("Empty user input")
            return "Sorry, I didn't catch that."

        try:
            logger.info(f"Sending to brain: {user_input}")
            response = self.model.generate_content(user_input)

            if response and response.text:
                result = response.text.strip()
                logger.info(f"Brain response: {result}")
                return result
            else:
                logger.warning("Empty response from Gemini")
                return "Sorry, I didn't catch that."

            except Exception as e:
                logger.error(f"Error getting response from brain: {e}")
                return "Sorry, I didn't catch that."

