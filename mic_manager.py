import importlib
import logging
import struct

logger = logging.getLogger(__name__)

_audio_backend : str | None = None
_backend_label = "none"

try:
    _sd = importlib.import_module("sounddevice")
    _np = importlib.import_module("numpy")
    _audio_backend = "sounddevice" 
    _backend_label = f"sounddevice {getattr(_sd, '__version__', '?')}"
except ImportError:
    try:
        _pyaudio = importlib.import_module("pyaudio")
        _audio_backend = "pyaudio"
        _backend_label = f"pyaudio {getattr(_pyaudio, '__version__', '?')}"
    except ImportError:
        logger.error(
            "No audio backend availabel. Install 'sounddevice' (Python 3.14+)"
            "or 'pyaudio' (older Python versions)."
        )

_vad_backend: str | None = None

try:
    _webrtcvad = importlib.import_module("webrtcvad")
    _vad_backend  = "webrtcvad"
except ImportError:
    try:
        from simple_vad import SimpleVAD as _SimpleVAD
        _vad_backend = "simple"
    except ImportError:
        logger.warning(
            "No VAD backend. Install webrtcvad (Python <3.12) or add 'simple_vad.py' to the project root. Recording will use fixed duration."
        )
logger.info(f"Audio backend: {_backend_label} | VAD backend: {_vad_backend}")

def _make_vad():
    """Instantiate the active VAD with aggressiveness=2."""
    if _vad_backend == "webrtcvad":
        return _webrtcvad.Vad(2)
    if _vad_backend == "simple":
        return _SimpleVAD(aggressiveness=2)
    return None

def _vad_is_speech(vad, chunk_bytes: bytes, rate: int) -> bool:
    """Uniform VAD call across backends."""
    if vad is None:
        return True
    if _vad_backend == "webrtcvad":
        return vad.is_speech(chunk_bytes, rate)
    return vad.is_speech(chunk_bytes)

class MicManager:
    def __init__(self, access_key: str, keyword_path: str | None = None):
        self.access_key = access_key
        self.keyword_path = keyword_path

    def _sd_open_input(self, rate: int, blocksize: int):
        """Open a 16 kHz mono int16 input stream via sounddevice."""
        stream = _sd.InputStream(
            samplerate=rate,
            channels=1,
            dtype="int16",
            blocksize=blocksize,
        )
        stream.start()
        return stream

    @staticmethod
    def _sd_read_bytes(stream, n_frames: int) -> bytes:
        """Read n_frames samples -> raw int16 little-endian bytes."""
        data, _overflowed = stream.read(n_frames)
        return data.tobytes()

    @staticmethod
    def _sd_read_tuple(stream, n_frames: int):
        """Read n_frames samples -> tuple of ints (for Porcupine)."""
        data, _overflowed = stream.read(n_frames)
        return tuple(int(x) for x in data.flatten())
    
    def _pa_open_input(self, rate: int, frames_per_buffer: int):
        pa = _pyaudio.PyAudio()
        stream = pa.open(
            format=_pyaudio.paInt16,
            channels=1,
            rate=rate,
            input=True,
            frames_per_buffer=frames_per_buffer,
        )
        return pa, stream

    def wait_for_wake_word(self) -> None:
        """Block until Porcupine detects the wake word, then return."""
        if _audio_backend is None:
            raise RuntimeError("No audio backend - cannot run wake word.")
        
        pvporcupine = importlib.import_module("pvporcupine")

        porcupine = None
        stream = None
        pa = None
        try:
            if self.keyword_path:
                porcupine = pvporcupine.create(
                    access_key=self.access_key,
                    keyword_path=[self.keyword_path],
                )
            else:
                porcupine = pvporcupine.create(
                    access_key=self.access_key,
                    keyword=["jarvis"],
                )
            frame_len = porcupine.frame_length
            rate = porcupine.sample_rate

            logger.info("Listening for wake word...")

            if _audio_backend == "sounddevice":
                stream = self._sd_open_input(rate=rate, blocksize=frame_len)
                while True:
                    pcm_tuple = self._sd_read_tuple(stream, frame_len)
                    if porcupine.process(pcm_tuple) >= 0:
                        logger.info("Wake word detected!")
                        break
            else:
                pa, stream = self._pa_open_input(rate=rate, frames_per_buffer=frame_len)
                while True:
                    raw = stream.read(frame_len, exception_on_overflow=False)
                    pcm_tuple = struct.unpack_from("h" * frame_len, raw)
                    if porcupine.process(pcm_tuple) >= 0:
                        logger.info("Wake word detected!")
                        break
        
        except (OSError, RuntimeError, ValueError) as e:
            logger.error(f"Wake word detection error: {e}")
        finally:
            if stream is not None:
                try:
                    if _audio_backend == "sounddevice":
                        stream.stop()
                        stream.close()
                    else:
                        stream.stop_stream()
                        stream.close()
                except (OSError, RuntimeError) as exc:
                    logger.warning("Error while closing audio stream: %s", exc)
                if pa is not None:
                    pa.terminate()
                if porcupine is not None:
                    porcupine.delete() 

    def record_command(self, max_duration: float = 5.0, silence_timeout: float = 1.0,) -> bytes:
        """Record up to max_duration seconds, cutting early after silence_timeout seconds of silence. Returns 16 kHz mono int16 bytes."""
        if _audio_backend is None:
            raise RuntimeError("No audio backend - cannot record.")
        
        rate = 16000
        frame_duration_ms = 30
        frame_samples = int(rate * frame_duration_ms / 1000)
        frame_bytes_len = frame_samples * 2

        vad = _make_vad()
        silence_limit = int(silence_timeout / (frame_duration_ms / 1000.0))
        max_frames = int(max_duration / (frame_duration_ms / 1000))

        stream = None
        pa = None
        frames: list[bytes] = []
        silent_count = 0

        try: 
            logger.info("Recording command...")

            if _audio_backend == "sounddevice":
                stream = self._sd_open_input(rate=rate, blocksize=frame_samples)
                for _ in range(max_frames):
                    data, _ov = stream.read(frame_samples)
                    chunk = data.tobytes()
                    frames.append(chunk)
                    if _vad_is_speech(vad, chunk, rate):
                        silent_count = 0
                    else:
                        silent_count += 1
                        if silent_count >= silence_limit:
                            logger.info(f"Silence detected - stopped at {len(frames)} frames.")
                            break
                        
            else:
                pa, stream = self._pa_open_input(rate=rate, frames_per_buffer=frame_bytes_len)
                for _ in range(max_frames):
                    chunk = stream.read(frame_bytes_len, exception_on_overflow=False)
                    frames.append(chunk)
                    if _vad_is_speech(vad, chunk, rate):
                        silent_count = 0
                    else:
                        silent_count += 1
                        if silent_count >= silence_limit:
                            logger.info(f"Silence detected - stopped at {len(frames)} frames.")
                            break
                        return b"".join(frames)

        except (OSError, RuntimeError, ValueError) as e:
            logger.error(f"Recording error: {e}")
            logger.warning("Falling back to fixed-duration recording.")
            return self._record_fixed(5.0)
        finally:
            if stream is not None:
                try:
                    if _audio_backend == "sounddevice":
                        stream.stop()
                        stream.close()
                    else:
                        stream.stop_stream()
                        stream.close()
                except (OSError, RuntimeError, AttributeError) as e:
                    logger.warning("Error closing audio stream: %s", e)
            if pa is not None:
                pa.terminate()
    
    def _record_fixed(self, duration: float) -> bytes:
        """Record exactly `duration` seconds - used when VAD fails."""
        rate = 16000
        total_frames = int(rate * duration)

        if _audio_backend == "sounddevice":
            stream = self._sd_open_input(rate=rate, blocksize=1024)
            try:
                chunks = []
                remaining = total_frames
                while remaining > 0:
                    n = min(1024, remaining)
                    data, _ov = stream.read(n)
                    chunks.append(data.tobytes())
                    remaining -= n
                return b"".join(chunks)
            finally:
                stream.stop()
                stream.close()

        chunk = 1024
        pa, stream = self._pa_open_input(rate=rate, frames_per_buffer=chunk)
        try:
            frames = []
            for _ in range(int(rate / chunk * duration)):
                frames.append(stream.read(chunk, exception_on_overflow=False))
                return b"".join(frames)
        finally:
            stream.stop_stream()
            stream.close()
            pa.terminate()

    def close(self):
        """No-op for souddevice; pyaudio cleanup is handles per-stream."""
        logger.debug("MicManager.close() - nothing to clean up.")


