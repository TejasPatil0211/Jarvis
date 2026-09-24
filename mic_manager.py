import importlib
import struct
import time
import logging
try:
    webrtcvad = importlib.import_module("webrtcvad")
except ImportError:
    webrtcvad = None
from typing import Optional

try:
    pyaudio = importlib.import_module("pyaudio")
except ImportError:
    pyaudio = None

logger = logging.getLogger(__name__)

try:
    pvporcupine = importlib.import_module("pvporcupine")
except ImportError:
    pvporcupine = None

class MicManager:
    def __init__(self, access_key: str, keyword_path: Optional[str] = None):
        self.access_key = access_key
        self.keyword_path = keyword_path
        self._pa = None

    def _open_stream(self, rate=16000, channels=1, input=True, frames_per_buffer=1024):
        if pyaudio is None:
            raise ImportError(
                "pyaudio is required for microphone access; "
                "install it with 'pip install pyaudio'."
            )
        if self._pa is None:
            self._pa = pyaudio.PyAudio()
        return self._pa.open(
            format=pyaudio.paInt16,
            channels=channels,
            rate=rate,
            input=input,
            frames_per_buffer=frames_per_buffer
        )

    def wait_for_wake_word(self) -> None:
        """Block until the wake word is detected, then return."""
        if pvporcupine is None:
            raise ImportError(
                "pvporcupine is required for wake-word detection; "
                "install it with 'pip install pvporcupine'."
            )
        porcupine = None
        stream = None
        try:
            if self.keyword_path:
                porcupine = pvporcupine.create(
                    access_key=self.access_key,
                    keyword_paths=[self.keyword_path]
                )
            else:
                porcupine = pvporcupine.create(
                    access_key=self.access_key,
                    keywords=["jarvis"]
                )

            stream = self._open_stream(
                rate=porcupine.sample_rate,
                frames_per_buffer=porcupine.frame_length
            )
            logger.info("Listening for wake word...")
            while True:
                pcm = stream.read(porcupine.frame_length, exception_on_overflow=False)
                pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)
                if porcupine.process(pcm) >= 0:
                    logger.info("Wake word detected!")
                    break
        except Exception as e:
            logger.error(f"Wake word detection error: {e}")
        finally:
            if stream:
                stream.stop_stream()
                stream.close()
            if porcupine:
                porcupine.delete()

    def record_command(self, max_duration=5.0, silence_timeout=1.0) -> bytes:
        """Record upto max_duration seconds, but stop early if silence_timeout seconds of silence (VAD) are detected.
        Returns raw 16kHz mono PCM audio data as bytes."""
        if webrtcvad is None:
            raise ImportError(
                "webrtcvad is required for silence detection; "
                "install it with 'pip install webrtcvad'."
            )
        vad = webrtcvad.Vad(2)
        rate = 16000
        frame_duration = 30 # in ms
        frame_bytes = int(rate * frame_duration / 1000) * 2

        stream = None
        frames = []
        silent_chunks = 0
        silence_limit = int(silence_timeout / (frame_duration / 1000.0))
        max_chunks = int(max_duration / (frame_duration / 1000.0))

        try:
            stream = self._open_stream(rate=rate, frames_per_buffer=frame_bytes)
            logger.info("Recording command...")
            for _ in range(max_chunks):
                data = stream.read(frame_bytes, exception_on_overflow=False)
                frames.append(data)

                if len(data) == frame_bytes:
                    is_speech = vad.is_speech(data, rate)
                    if not is_speech:
                        silent_chunks += 1
                        if silent_chunks >= silence_limit:
                            logger.info(f"Silence detected, stopping recording early at {len(frames)} frame.")
                            break
                        else:
                            silent_chunks = 0

        except Exception as e:
            logger.error(f"Recording error: {e}")
            logger.warning("Falling back to recorded audio.")
            return self._record_fixed(5.0)
        finally:
            if stream:
                stream.stop_stream()
                stream.close()

        return b''.join(frames)

    def _record_fixed(self, duration: float) -> bytes:
        """Fallback: record exactly duration seconds."""
        rate = 16000
        chunk = 1024
        stream = self._open_stream(rate=rate, frames_per_buffer=chunk)
        frames = []
        for _ in range(0, int(rate / chunk * duration)):
            data = stream.read(chunk, exception_on_overflow=False)
            frames.append(data)
        stream.stop_stream()
        stream.close()
        return b''.join(frames)

    def close(self):
        if self._pa:
            self._pa.terminate()