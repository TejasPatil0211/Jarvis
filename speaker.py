import requests
import base64
import io
import pygame
import logging
from google.oauth2 import service_account
from google.auth.transport.requests import Request
import config

logger = logging.getLogger(__name__)


class Speaker:
    def __init__(self):
        pygame.mixer.init()
        self.credentials = None
        self._load_credentials()

    def _load_credentials(self):
        try:
            self.credentials = service_account.Credentials.from_service_account_file(
                config.GOOGLE_APPLICATION_CREDENTIALS,
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
        except Exception as e:
            logger.error(f"Failed to load TTS credentials: {e}")
            self.credentials = None

    def _get_access_token(self):
        if self.credentials and self.credentials.valid:
            return self.credentials.token
        if self.credentials:
            self.credentials.refresh(Request())
            return self.credentials.token
        return None

    def speak(self, text):
        if not text:
            return
        try:
            token = self._get_access_token()
            if not token:
                logger.error("No valid access token for TTS")
                return

            url = "https://texttospeech.googleapis.com/v1/text:synthesize"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
            payload = {
                "input": {"text": text},
                "voice": {"languageCode": "en-US", "name": "en-US-Neural2-J"},
                "audioConfig": {"audioEncoding": "MP3"},
            }

            resp = requests.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            audio_content = resp.json().get("audioContent")
            if not audio_content:
                logger.error("No audio content in TTS response")
                return

            audio_bytes = base64.b64decode(audio_content)
            sound = pygame.mixer.Sound(io.BytesIO(audio_bytes))
            sound.play()
            while pygame.mixer.get_busy():
                pygame.time.wait(10)
        except Exception as e:
            logger.error(f"TTS playback error: {e}")
        