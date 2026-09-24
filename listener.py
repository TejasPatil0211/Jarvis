import logging
from google.cloud import speech_v1
from retry_helper import retry_with_backoff

logger = logging.getLogger(__name__)


class listener:
    def __init__(self):
        self.client = speech_v1.SpeechClient()

    @retry_with_backoff
    def transcribe(self, audio_bytes: bytes) -> str:
        """Transcribe audio bytes using Google STT."""
        audio = speech_v1.RecognitionAudio(content=audio_bytes)
        config = speech_v1.RecognitionConfig(
            encoding=speech_v1.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code="en-US"
        )
        response = self.client.recognize(config=config, audio=audio)
        if response.results:
            transcript = response.results[0].alternatives[0].transcript
            logger.info(f"Transcribed: {transcript}")
            return transcript
        else:
            logger.warning("No transcription returned.")
            return ""