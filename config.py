import logging
import os
import sys

try:
    from dotenv import load_dotenv  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - optional dependency for local .env files
    def load_dotenv(*args, **kwargs):
        return False

load_dotenv()

# ─── Wake word ────────────────────────────────────────────────────────────
# Engine: auto | porcupine | openwakeword
#   porcupine    — Picovoice. Needs an AccessKey; signup asks for a corporate
#                  email, so many people cannot get one.
#   openwakeword — Fully local ONNX models. No key, no signup, no billing.
#                  Ships a pretrained "hey jarvis" model.
PORCUPINE_ACCESS_KEY = os.getenv("PORCUPINE_ACCESS_KEY")
PORCUPINE_KEYWORD_PATH = os.getenv("PORCUPINE_KEYWORD_PATH")
WAKE_ENGINE = os.getenv("WAKE_ENGINE", "auto").strip().lower()
WAKEWORD_MODEL = os.getenv("WAKEWORD_MODEL", "hey_jarvis")
WAKEWORD_THRESHOLD = float(os.getenv("WAKEWORD_THRESHOLD", "0.5"))

# ─── Groq (LLM + STT) ─────────────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.groq.com/openai/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "openai/gpt-oss-120b")
GROQ_STT_MODEL = os.getenv("GROQ_STT_MODEL", "whisper-large-v3-turbo")

# ─── Text to speech ──────────────────────────────────────────────────────
# Engine: auto | google | edge | sapi
#   google — Google Cloud TTS. Best quality, but needs a billing account.
#   edge   — Microsoft Edge TTS via edge-tts. No key, no signup, no billing.
#   sapi   — Windows built-in speech engine. Offline, robotic, zero setup.
TTS_ENGINE = os.getenv("TTS_ENGINE", "auto").strip().lower()
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
TTS_VOICE_NAME = os.getenv("TTS_VOICE_NAME", "en-US-Standard-A")
TTS_VOICE_EDGE = os.getenv("TTS_VOICE_EDGE", "en-US-GuyNeural")

# ─── OCR ──────────────────────────────────────────────────────────────────
# Engine: auto | openrouter | ocrspace | google | tesseract
#   openrouter — free vision LLM via OpenRouter. Needs a free account.
#   ocrspace   — free OCR API, 25k requests/month, no credit card.
#   google     — Google Cloud Vision. Needs a billing account.
#   tesseract  — fully local. Free, no key, but weak on handwriting.
OCR_ENGINE = os.getenv("OCR_ENGINE", "auto").strip().lower()
OCRSPACE_API_KEY = os.getenv("OCRSPACE_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_VISION_MODEL = os.getenv(
    "OPENROUTER_VISION_MODEL", "google/gemini-2.0-flash-exp:free"
)

# Audio settings
SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_SIZE = 512 # frames per buffer for PyAudio
FORMAT = 16 # bits per sample (pyaudio.paInt16)
RECORD_SECONDS = 5 # duration for command capture

# Microphone selection. Empty = system default. Set to a device index ("2")
# or part of a device name ("headset", "usb mic") to pick a specific input.
# List the options with: python mic_manager.py --list-devices
MIC_DEVICE = os.getenv("MIC_DEVICE", "").strip()

# Feature Flags(settings.py)
MEMORY_ENABLED = os.getenv("MEMORY_ENABLED", "True").lower() in ("true", "1", "yes")
MEMORY_MAX_TURNS = int(os.getenv("MEMORY_MAX_TURNS", "10"))
DOCS_OUTPUT_DIR = os.getenv("DOCS_OUTPUT_DIR", "./documents")
OCR_TEMP_DIR = os.getenv("OCR_TEMP_DIR", "./scans")

# Layer 4 System Control
SCREENSHOTS_DIR = os.getenv("SCREENSHOTS_DIR", "./screenshots")

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
    """Validate the environment at startup.

    Only OPENAI_API_KEY is genuinely required — the LLM cannot work without it.
    Everything else has a working fallback, so a missing key produces a
    warning and a suggestion, not a hard exit.
    """
    missing = []
    warnings = []

    if not OPENAI_API_KEY:
        missing.append("OPENAI_API_KEY")

    # ── Optional, but warn so the user knows what they are losing ──
    if WAKE_ENGINE in ("auto", "porcupine") and not PORCUPINE_ACCESS_KEY:
        if WAKE_ENGINE == "porcupine":
            missing.append("PORCUPINE_ACCESS_KEY")
        else:
            warnings.append(
                "PORCUPINE_ACCESS_KEY not set — falling back to openWakeWord "
                "(no key needed, 'hey jarvis' model)."
            )

    if TTS_ENGINE in ("auto", "google") and not GOOGLE_APPLICATION_CREDENTIALS:
        if TTS_ENGINE == "google":
            warnings.append(
                "GOOGLE_APPLICATION_CREDENTIALS not set — Google TTS disabled. "
                "Set TTS_ENGINE=edge to use the key-free Edge voice."
            )
        else:
            warnings.append(
                "GOOGLE_APPLICATION_CREDENTIALS not set — using the key-free "
                "Edge TTS voice instead."
            )

    if OCR_ENGINE in ("auto", "openrouter") and not OPENROUTER_API_KEY:
        if OCR_ENGINE == "openrouter":
            warnings.append(
                "OPENROUTER_API_KEY not set — free vision OCR unavailable."
            )

    for w in warnings:
        logger.warning(w)

    if missing:
        print("ERROR: Missing required environment variables:")
        for m in missing:
            print(f" - {m} not set in .env")
        print("\nGet them at:")
        print(" Groq:      https://console.groq.com/keys")
        if "PORCUPINE_ACCESS_KEY" in missing:
            print(" Porcupine: https://console.picovoice.ai/")
            print("            (or set WAKE_ENGINE=openwakeword for no signup)")
        print("\nEverything else has a free, no-signup fallback.")
        sys.exit(1)