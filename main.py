import logging
import sys
import time
from queue import Queue, Empty
import signal

from config import PORCUPINE_ACCESS_KEY, GEMINI_API_KEY
from wake_word import WakeWordListener
from listener import Listener
from speaker import Speaker

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("jarvis.log")
    ]
)
logger = logging.getLogger(_name_)

task_queue = Queue()
listener = Listener()
brain = Brain(GEMINI_API_KEY) if GEMINI_API_KEY else None
speaker = Speaker()
wake_listener = None

def wake_callback():
    """Callback when wake word is detected - enqueue a task."""
    task_queue.put("wake")

def process_wake():
    """Capture, think, speak."""
    logger.info("Processing wake...")
    transcript = listener.capture_command()
    if not transcript:
        speaker.speak("Sorry, I didn't catch that.")
        return
    if brain:
        reply = brain.get_response(transcript)
    else:
        reply = "Brain not initialized."
    speaker.speak(reply)

def main():
    global wake_listener

    if not PORCUPINE_ACCESS_KEY:
        logger.error("PORCUPINE_ACCESS_KEY not set in .env")
        sys.exit(1)
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY not set in .env")
        sys.exit(1)

    wake_listener = WakeWordListener(PORCUPINE_ACCESS_KEY, wake_callback)
    wake_listener.start()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("Jarvis is ready. Say 'Jarvis' to activate.")
    while True:
        try:
            item = task_queue.get(timeout=0.1)
            if item == "wake":
                process_wake()
        except Empty:
            continue
        except Exception as e:
            logger.error(f"Loop error: {e}")

if _name_ == "_main_":
    main()
