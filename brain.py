import google.generativeai as genai
import logging


logger = logging.getLogger(__name__)


class Brain:
    def __init__(self, api_key):
            genai.configure(api_key=GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-1.5-flash',
                system_instruction="You are Jarvis, a concise voice assistant. Keep responses under 2 sentences."
            )

    def get_response(self, text):
        try:
            response = self.model.generate_content(text)
            reply = response.text.strip()
            logger.info(f"Gemini reply: {reply}")
            return reply
        except Exception as e:
             logger.error(f"Gemini API error: {e}")
             return "Sorry, I didn't catch that."
