import os
import logging
import sys

# Load environment variables from .env file
def load_dotenv(path=".env"):
    """Load simple KEY=VALUE entries without requiring python-dotenv."""
    if not os.path.isfile(path):
        return
    with open(path, encoding="utf-8") as env_file:
        for line in env_file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key.strip(), value)


load_dotenv()

# API keys and credentials
PORCUPINE_ACCESS_KEY = os.getenv("PORCUPINE_ACCESS_KEY")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
PORCUPINE_KEYWORD_PATH = os.getenv("PORCUPINE_KEYWORD_PATH")

# Audio settings
SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_SIZE = 512 # frames per buffer for PyAudio
FORMAT = 16 # bits per sample (pyaudio.paInt16)
RECORD_SECONDS = 5 # duration for command capture

# Porcupine wake word settings
WAKE_WORD = "jarvis"
POCUPINE_MODEL_PATH = None 

#Logging configuration
LOG_FILE = "jarvis.log"
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(module)s | %(message)s"
LOG_LEVEL = logging.INFO

# Gemini AI settings
LLM_MODEL = "gemini-1.5-flash"
SYSTEM_PROMPT = "You are Jarvis, a concise voice assistant. Keep response under 2 sentences."

# Gemini TTS settings
TTS_MODEL = "gemini-1.5-flash"
TTS_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{TTS_MODEL}:generateContent?key={GEMINI_API_KEY}"

# Google Cloud Speech settings
STT_SAMPLE_RATE = SAMPLE_RATE
STT_ENCODING = "LINEAR16"
STT_LANGUAGE_CODE = "en-US"

def validate_required_keys():
    missing = []
    if not PORCUPINE_ACCESS_KEY:
        missing.append("PORCUPINE_ACCESS_KEY")
    if not GOOGLE_APPLICATION_CREDENTIALS:
        missing.append("GOOGLE_APPLICATION_CREDENTIALS")
    if not GEMINI_API_KEY:
        missing.append("GEMINI_API_KEY")
    if missing:
        print("Error: Missing required environment variables")
        for m in missing:
            print(f" - {m}")
        print("\nPlease set them in .env file and refer to README.md for setup help.")
        sys.exit(1)