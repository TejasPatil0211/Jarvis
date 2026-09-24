import logging
import sys
import signal
import time
from config import (
    PORCUPINE_ACCESS_KEY,
    PORCUPINE_KEYWORD_PATH,
    GEMINI_API_KEY,
    validate_required_keys,
)
from mic_manager import MicManager
from listener import Listener
from brain import Brain
from speaker import Speaker


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("jarvis.log")
    ]
)
logger = logging.getLogger(__name__)

running = True

def signal_handler(sig, frame):
    global running
    logger.info("Shutting down...")
    running = False
    sys.exit(0)

def main():
    global running
    validate_required_keys()

    mic_manager = MicManager(PORCUPINE_ACCESS_KEY, PORCUPINE_KEYWORD_PATH)
    listener = Listener()
    brain = Brain(GEMINI_API_KEY)
    speaker = Speaker()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("Jarvis is ready. Say 'Jarvis' to activate.")
    while running:
        try:
            mic_manager.wait_for_wake_word()
            if not running:
                break
            audio = mic_manager.record_command()
            if not audio:
                speaker.speak("Sorry, I couldn't hear you.")
                continue
            text = listener.transcribe(audio)
            if not text:
                speaker.speak("Sorry, I didn't catch that.")
                continue
            response = brain.process(text)
            speaker.speak(response)
        except Exception as e:
            logger.error(f"Loop error: {e}")
            speaker.speak("An error occured. Please try again.")

    mic_manager.close()

if __name__ == "_main_":
    main()
