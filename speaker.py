import base64
import io
import json
import subprocess
from urllib.error import HTTPError, URLError
from urllib.request import Request as UrlRequest, urlopen
import logging
import importlib
import config
from retry_helper import retry_with_backoff

logger = logging.getLogger(__name__)


class Speaker:
    def __init__(self):
        self._pygame = None
        try:
            self._pygame = importlib.import_module("pygame")
            self._pygame.mixer.init()
        except ImportError:
            logger.warning("pygame is not installed; audio playback is unavailable")
        self.credentials = None
        self._load_credentials()

    def _load_credentials(self):
        try:
            service_account = importlib.import_module("google.oauth2.service_account")
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
            requests_auth = importlib.import_module("google.auth.transport.requests")
            self.credentials.refresh(requests_auth.Request())
            return self.credentials.token
        return None
    @retry_with_backoff
    def _get_tts_audio(self, text: str) -> bytes:
        token = self._get_access_token()
        if not token:
            raise Exception("No valid access token for TTS")
        url = "https://texttospeech.googleapis.com/v1/text:synthesize"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "input": {"text": text},
            "voice": {"languageCode": "en-US", "name": "en-US-Neural2-J"},
            "audioConfig": {"audioEncoding": "MP3"},
        }
        request = UrlRequest(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urlopen(request, timeout=10) as response:
                response_data = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError) as e:
            raise RuntimeError(f"TTS request failed: {e}") from e

        audio_content = response_data.get("audioContent")
        if not audio_content:
            raise Exception("No audio content in TTS response")
        return base64.b64decode(audio_content)
    
    def speak(self, text):
        if not text:
            return
        try:
            audio_bytes = self._get_tts_audio(text)
            if self._pygame is None:
                raise RuntimeError("pygame is not installed")
            sound = self._pygame.mixer.Sound(io.BytesIO(audio_bytes))
            sound.play()
            while self._pygame.mixer.get_busy():
                self._pygame.time.wait(10)
            logger.info("TTS played via Google.")
        except Exception as e:
            logger.warning(f"Google TTS failed: {e}. Falling back to espeak.")
            self._speak_espeak(text)

    def _speak_espeak(self, text):
        """Fallback TTS using espeak."""
        try:
            cmd = ["espeak", "-v", "en-us", "+m3", "-s", "160", text]
            subprocess.run(cmd, check=True, timeout=10)
            logger.info("TTS played via espeak")
        except Exception as e:
            logger.error(f"espeak fallback also failed: {e}")
        