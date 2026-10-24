import io
import logging
import wave

from config import GROQ_STT_MODEL, OPENAI_API_KEY, OPENAI_BASE_URL

try:
    from openai import OpenAI  # type: ignore[import-not-found]
except ImportError as exc:  # pragma: no cover - handled at runtime
    raise RuntimeError(
        "The 'openai' package is not installed. Install it with 'pip install openai'."
    ) from exc

logger = logging.getLogger(__name__)
MAX_UPLOAD_BYTES = 25 * 1024 * 1024


class Listener:
    def __init__(self):
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not set in .env")

        self.client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
        self.stt_model = GROQ_STT_MODEL
        logger.info(f"Listener initialized with Groq Whisper ({self.stt_model})")

    def transcribe(self, audio_bytes: bytes) -> str:
        """Transcribe raw 16 kHz mono PCM bytes using Groq Whisper."""
        if not audio_bytes:
            return ""
        if len(audio_bytes) > MAX_UPLOAD_BYTES:
            logger.error(f"Audio too large: {len(audio_bytes)} bytes (>25MB)")
            return ""

        try:
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, "wb") as wf:
                wf.setnchannels(1)  # mono
                wf.setsampwidth(2)  # 16-bit PCM
                wf.setframerate(16000)  # 16 kHz
                wf.writeframes(audio_bytes)
            wav_buffer.seek(0)
            wav_buffer.name = "audio.wav"  # Set a name for the file-like object

            response = self.client.audio.transcriptions.create(
                model=self.stt_model,
                file=wav_buffer,
                language="en",
            )
            text = response.text.strip()
            logger.info(f"Transcribed: {text}")
            return text

        except (OSError, TypeError, ValueError, wave.Error) as e:
            logger.error(f"Error during transcription: {e}")
            return ""