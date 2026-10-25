"""
speaker.py — Text to speech with pluggable engines.

Engines (set TTS_ENGINE in .env):

  auto    google if credentials are present, otherwise edge, otherwise sapi
  google  Google Cloud TTS. Best quality. Requires a billing account.
  edge    Microsoft Edge TTS via edge-tts. No API key, no signup, no billing,
          and it sounds like a real person. Requires internet.
  sapi   Windows built-in speech engine via PowerShell. Fully offline, robotic,
          and works with zero setup. Linux/macOS fall back to espeak.

Every engine returns raw MP3 bytes so playback is identical across engines.
"""

import asyncio
import base64
import importlib
import io
import json
import logging
import os
import platform
import subprocess
from urllib.error import HTTPError, URLError
from urllib.request import Request as UrlRequest
from urllib.request import urlopen

import config
from retry_helper import retry_with_backoff

logger = logging.getLogger(__name__)


class Speaker:
    def __init__(self):
        self._pygame = None
        self._init_playback()

        self.credentials = None
        self.engine = self._select_engine()
        if self.engine == "google":
            self._load_credentials()
        logger.info(f"TTS engine: {self.engine}")

    def _init_playback(self):
        """Set up audio playback.

        A failure here must not stop Jarvis — it can still log what it
        would have said. This happens on machines with no audio device,
        a missing PulseAudio server, or a device already in use.
        """
        try:
            self._pygame = importlib.import_module("pygame")
            self._pygame.mixer.init()
        except ImportError:
            logger.warning("pygame is not installed; audio playback is unavailable")
        except Exception as e:
            logger.warning(f"Could not initialise audio playback: {e}")
            self._pygame = None

    # ── engine selection ────────────────────────────────────────────────
    def _select_engine(self) -> str:
        requested = (config.TTS_ENGINE or "auto").strip().lower()

        if requested == "google":
            return "google"
        if requested == "edge":
            return "edge"
        if requested == "sapi":
            return "sapi"

        # auto — prefer the key-free option when Google is not configured
        if config.GOOGLE_APPLICATION_CREDENTIALS and self._google_usable():
            return "google"
        if self._edge_usable():
            return "edge"
        return "sapi"

    @staticmethod
    def _edge_usable() -> bool:
        try:
            importlib.import_module("edge_tts")
            return True
        except ImportError:
            return False

    def _google_usable(self) -> bool:
        path = config.GOOGLE_APPLICATION_CREDENTIALS
        return bool(path) and os.path.exists(path)

    # ── Google Cloud TTS ────────────────────────────────────────────────
    def _load_credentials(self):
        try:
            service_account = importlib.import_module("google.oauth2.service_account")
            self.credentials = service_account.Credentials.from_service_account_file(
                config.GOOGLE_APPLICATION_CREDENTIALS,
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
        except (ImportError, AttributeError, FileNotFoundError, OSError, TypeError, ValueError) as e:
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
            raise ValueError("No valid access token for TTS")
        url = "https://texttospeech.googleapis.com/v1/text:synthesize"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        payload = {
            "input": {"text": text},
            "voice": {
                "languageCode": "en-US",
                "name": config.TTS_VOICE_NAME or "en-US-Standard-A",
            },
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
            raise ValueError("No audio content in TTS response")
        return base64.b64decode(audio_content)

    # ── Edge TTS (no key required) ─────────────────────────────────────
    def _get_edge_audio(self, text: str) -> bytes:
        edge_tts = importlib.import_module("edge_tts")
        voice = config.TTS_VOICE_EDGE or "en-US-GuyNeural"

        async def _collect() -> bytes:
            communicate = edge_tts.Communicate(text, voice)
            buffer = bytearray()
            async for chunk in communicate.stream():
                if chunk.get("type") == "audio":
                    buffer.extend(chunk["data"])
            return bytes(buffer)

        try:
            audio = asyncio.run(_collect())
        except RuntimeError:
            # An event loop is already running in this thread.
            loop = asyncio.new_event_loop()
            try:
                audio = loop.run_until_complete(_collect())
            finally:
                loop.close()
        except Exception as e:
            raise RuntimeError(f"Edge TTS failed: {e}") from e

        if not audio:
            raise ValueError("Edge TTS returned no audio")
        return audio

    # ── playback ────────────────────────────────────────────────────────
    def speak(self, text):
        if not text:
            return
        last = None
        for engine in self._engine_chain():
            try:
                audio_bytes = self._synthesize(engine, text)
                self._play(audio_bytes)
                logger.info(f"TTS played via {engine}.")
                return
            except (RuntimeError, ValueError, OSError, TypeError, AttributeError) as e:
                logger.warning(f"{engine} TTS failed: {e}")
                last = e
        logger.warning(f"All cloud TTS engines failed: {last}. Using offline voice.")
        self._speak_sapi(text)

    def _engine_chain(self):
        """Cloud engines to try, in order, for this call."""
        if self.engine == "google":
            return ["google", "edge"]
        if self.engine == "edge":
            return ["edge"]
        return []

    def _synthesize(self, engine: str, text: str) -> bytes:
        if engine == "google":
            return self._get_tts_audio(text)
        if engine == "edge":
            return self._get_edge_audio(text)
        raise RuntimeError(f"Unknown engine {engine}")

    def _play(self, audio_bytes: bytes):
        if self._pygame is None:
            raise RuntimeError("pygame is not installed")
        sound = self._pygame.mixer.Sound(io.BytesIO(audio_bytes))
        sound.play()
        while self._pygame.mixer.get_busy():
            self._pygame.time.wait(10)

    # ── offline fallbacks ───────────────────────────────────────────────
    def _speak_sapi(self, text: str):
        """Windows SAPI via PowerShell, or espeak on Linux/macOS."""
        if platform.system() == "Windows":
            if self._speak_sapi_windows(text):
                return
        self._speak_espeak(text)

    def _speak_sapi_windows(self, text: str) -> bool:
        try:
            escaped = text.replace("'", "''")
            script = (
                "Add-Type -AssemblyName System.Speech; "
                "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                f"$s.Speak('{escaped}')"
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", script],
                check=True,
                timeout=30,
                capture_output=True,
            )
            logger.info("TTS played via Windows SAPI")
            return True
        except (FileNotFoundError, subprocess.SubprocessError, OSError, TimeoutError) as e:
            logger.warning(f"SAPI fallback failed: {e}")
            return False

    def _speak_espeak(self, text):
        """Fallback TTS using espeak."""
        try:
            cmd = ["espeak", "-v", "en-us", "+m3", "-s", "160", text]
            subprocess.run(cmd, check=True, timeout=10)
            logger.info("TTS played via espeak")
        except (FileNotFoundError, subprocess.SubprocessError, OSError, TimeoutError, ValueError) as e:
            logger.error(f"espeak fallback also failed: {e}")
