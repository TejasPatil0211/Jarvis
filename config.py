import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API keys and credentials
PORCUPINE_ACCESS_KEY = os.getenv("PORCUPINE_ACCESS_KEY")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

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