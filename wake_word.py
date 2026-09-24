from mic_manager import MicManager
import logging

logger = logging.getLogger(__name__)

class WakeWordListener:
    def __init__(self, access_key, keyword_path=None):
        self.mic_manager = MicManager(access_key, keyword_path)

    def wait_for_wake_word(self):
        """Block untill wake word detected."""
        self.mic_manager.wait_for_wake_word()

    def stop(self):
        self.mic_manager.close()