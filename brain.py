import json
import logging

from config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL
from memory import ConversationMemory
from openai import (
    APIConnectionError,
    APIError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)

try:
    from tools import SKILL_TOOLS, execute_tool
except ImportError as e:
    # Do NOT stay silent here — a broken tools import silently disables every
    # Layer 4 function (web search, volume, screenshots, timers, weather).
    logger.error(
        "tools module could not be imported (%s) — all function calling is "
        "disabled. Check config.py and tools.py.", e
    )
    SKILL_TOOLS = []
    def execute_tool(name, args): return "Tools module missing."

logger = logging.getLogger(__name__)

class Brain:
    def __init__(self):
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not set in .env")
        self.client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
        self.model = OPENAI_MODEL
        self.memory = ConversationMemory()
        self.system_prompt = (
            "You are Jarvis, a concise voice assistant."
            "Keep responses under 2 sentences."
            "When a user's request matches a tool, call the tool."
            "If no tool fits the request, answer directly."
        )
        logger.info(f"Brain initialised with {self.model} (Function Calling active)")

    def process(self, user_input: str) -> str:
        response = self.get_response(user_input)
        self.memory.add_turn(user_input, response)
        return response

    def get_response(self, user_input: str) -> str:
        try:
            messages = [{"role": "system", "content": self.system_prompt}]
            messages.extend(self.memory.get_messages())
            messages.append({"role": "user", "content": user_input})

            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 300,
            }
            if SKILL_TOOLS:
                kwargs["tools"] = SKILL_TOOLS
                kwargs["tool_choice"] = "auto"

            response = self.client.chat.completions.create(**kwargs)
            message = response.choices[0].message

            if getattr(message, "tool_calls", None):
                for tc in message.tool_calls:
                    fn_name = tc.function.name
                    try:
                        fn_args =  json.loads(tc.function.arguments or "{}")
                    except json.JSONDecodeError:
                        fn_args = {}

                    logger.info(f"executing tool: {fn_name}({fn_args})")
                    result = execute_tool(fn_name, fn_args)

                    messages.append({
                        "role": "assistant",
                        "content": message.content or "",
                        "tool_calls": [{
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": fn_name, "arguments": tc.function.arguments}
                        }]
                    })

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": str(result)
                    })
                
                final = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=300,
                )
                return final.choices[0].message.content.strip()

            return message.content.strip() or "I'm not sure how to respond."

        except (APIConnectionError, APIError, AuthenticationError, RateLimitError, ValueError, TypeError) as e:
            logger.error(f"OpenAI API error: {e}")
            if "429" in str(e): return "Rate limit hit. Wait for a moment."
            if "401" in str(e): return "API key invalid."
            return "Sorry, I had trouble thinking just now."