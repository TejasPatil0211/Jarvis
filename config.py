import logging
import os
import sys

try:
    from dotenv import load_dotenv  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - optional dependency for local .env files
    def load_dotenv(*args, **kwargs):
        return False

load_dotenv()

# API keys and credentials
PORCUPINE_ACCESS_KEY = os.getenv("PORCUPINE_ACCESS_KEY")
PORCUPINE_KEYWORD_PATH = os.getenv("PORCUPINE_KEYWORD_PATH")

# Groq (LLM + STT)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.groq.com/openai/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "openai/gpt-oss-120b")
GROQ_STT_MODEL = os.getenv("GROQ_STT_MODEL", "whisper-large-v3-turbo")

# Google Cloud TTS 
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
TTS_VOICE_NAME = os.getenv("TTS_VOICE_NAME", "en-US-Standard-A")

# Audio settings
SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_SIZE = 512 # frames per buffer for PyAudio
FORMAT = 16 # bits per sample (pyaudio.paInt16)
RECORD_SECONDS = 5 # duration for command capture

# Feature Flags(settings.py)
MEMORY_ENABLED = os.getenv("MEMORY_ENABLED", "True").lower() in ("true", "1", "yes")
MEMORY_MAX_TURNS = int(os.getenv("MEMORY_MAX_TURNS", "10"))
DOCS_OUTPUT_DIR = os.getenv("DOCS_OUTPUT_DIR", "./documents")
OCR_TEMP_DIR = os.getenv("OCR_TEMP_DIR", "./scans")

# Layer 4 System Control
SCREEENSHOTS_DIR = os.getenv("SCREENSHOTS_DIR", "./screenshots")

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(module)s | %(message)s",
    handlers=[
        logging.FileHandler("jarvis.log"),
        logging.StreamHandler(),        
    ],
    )
logger = logging.getLogger(__name__)

def validate_required_keys():
    """Validate required API keys at startup."""
    missing = []
    if not PORCUPINE_ACCESS_KEY:
        missing.append("PORCUPINE_ACCESS_KEY")
    if not OPENAI_API_KEY:
        missing.append("OPENAI_API_KEY")
    if not GOOGLE_APPLICATION_CREDENTIALS:
        missing.append("GOOGLE_APPLICATION_CREDENTIALS")
    
    if missing:
        print("ERROR: Missing required environment variables:")
        for m in missing:
            print(f" - {m} not set in .env")
        print("\nGet them at:")
        print(" Porcupine: https://console.picovoice.ai/")
        print(" Groq: https://console.groq.com/keys")
        print(" Google: https://console.cloud.google.com/")
        sys.exit(1)