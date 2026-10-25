import json
import logging
import os
from datetime import datetime, timezone

from config import MEMORY_ENABLED, MEMORY_MAX_TURNS

logger = logging.getLogger(__name__)

class ConversationMemory:
    def __init__(self, storage_path="./jarvis_memory.json"):
        self.storage_path = storage_path
        self.enabled = MEMORY_ENABLED
        self.history = []
        self._load()

    def _load(self):
        if not self.enabled or not os.path.exists(self.storage_path):
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                self.history = json.load(f)
            logger.info(f"Loaded {len(self.history)} memory entries.")
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load memory: {e}")
            self.history = []

    def add_turn(self, user_input: str, jarvis_response: str):
        if not self.enabled:
            return
        timestamp = datetime.now(timezone.utc).isoformat()
        self.history.append({
            "timestamp": timestamp,
            "user_input": user_input,
            "jarvis_response": jarvis_response
        })
        if len(self.history) > MEMORY_MAX_TURNS:
            self.history = self.history[-MEMORY_MAX_TURNS:]
        self._save()

    def get_messages(self) -> list:
        if not self.enabled:
            return []
        messages = []
        for turn in self.history:
            messages.append({"role": "user", "content": turn.get("user_input", turn.get("user", ""))})
            messages.append({"role": "assistant", "content": turn.get("jarvis_response", turn.get("jarvis",""))})
        return messages

    def get_context(self) -> list:
        return self.get_messages()

    def clear(self):
        self.history = []
        if os.path.exists(self.storage_path):
            os.remove(self.storage_path)
            logger.info("Memory cleared")

    def toggle(self) -> bool:
        self.enabled = not self.enabled
        if not self.enabled:
            self.clear()
        return self.enabled

    def _save(self):
        try:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(self.history, f, indent=2)
        except (OSError, TypeError, ValueError) as e:
            logger.error(f"Failed to save memory: {e}")

        