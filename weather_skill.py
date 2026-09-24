from .base import Skill
import json
import logging
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

class WeatherSkill(Skill):
    name = "weather"
    keywords = ["weather", "temperature", "forecast", "how's the weather"]

    def handle(self, user_input: str) -> str:
        try:
            request = Request(
                "https://wttr.in?format=j1",
                headers={"User-Agent": "weather-skill"},
            )
            with urlopen(request, timeout=5) as resp:
                data = json.load(resp)
            current = data.get("current_condition",[{}])[0]
            temp_c = current.get("temp_C", "unknown")
            desc = current.get("weatherDesc", [{}])[0].get("value", "unknown")
            return f"The weather is {desc.lower()} with {temp_c} degree Celsius of Temp."
        except Exception as e:
            logger.error(f"Weather skill error: {e}")
            return "Sorry, I couldn't fetch the weather."