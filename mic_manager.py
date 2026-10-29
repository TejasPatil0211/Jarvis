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
            "No audio backend available. Install 'sounddevice' (Python 3.14+)"
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

def _resolve_sd_device():
    """Resolve the MIC_DEVICE setting to a sounddevice device id.

    MIC_DEVICE can be a device index ("2") or part of a device name
    ("headset", "usb mic"). Empty means "use the system default".
    """
    import config

    spec = (config.MIC_DEVICE or "").strip()
    if not spec:
        return None

    try:
        return int(spec)
    except ValueError:
        pass

    try:
        devices = _sd.query_devices()
    except Exception as e:
        logger.warning(f"Could not query audio devices: {e}")
        return None

    matches = []
    for index, device in enumerate(devices):
        if device.get("max_input_channels", 0) < 1:
            continue
        name = str(device.get("name", ""))
        if spec.lower() in name.lower():
            matches.append((index, name))

    if not matches:
        logger.warning(
            f"No input device matching '{spec}'. Using the system default. "
            "Run 'python mic_manager.py --list-devices' to see the options."
        )
        return None
    if len(matches) > 1:
        logger.warning(
            f"'{spec}' matches {len(matches)} devices, using the first: "
            f"{matches[0][1]}"
        )
    index, name = matches[0]
    logger.info(f"Using input device [{index}] {name}")
    return index


def _resolve_pa_device(pa):
    """Resolve MIC_DEVICE to a PyAudio input device index."""
    import config

    spec = (config.MIC_DEVICE or "").strip()
    if not spec:
        return None

    try:
        index = int(spec)
        if index < pa.get_device_count():
            return index
        logger.warning(f"Input device {index} does not exist. Using default.")
        return None
    except ValueError:
        pass

    for index in range(pa.get_device_count()):
        info = pa.get_device_info_by_index(index)
        if info.get("maxInputChannels", 0) < 1:
            continue
        if spec.lower() in str(info.get("name", "")).lower():
            logger.info(f"Using input device [{index}] {info.get('name')}")
            return index

    logger.warning(
        f"No input device matching '{spec}'. Using the system default. "
        "Run 'python mic_manager.py --list-devices' to see the options."
    )
    return None


def list_devices() -> None:
    """Print every audio input device so the user can pick one."""
    print("=" * 62)
    print("  AUDIO INPUT DEVICES")
    print("=" * 62)

    if _audio_backend == "sounddevice":
        try:
            devices = _sd.query_devices()
        except Exception as e:
            print(f"  Could not query devices: {e}")
            return
        for index, device in enumerate(devices):
            channels = device.get("max_input_channels", 0)
            if channels < 1:
                continue
            default = " (system default)" if device.get("default_samplerate") else ""
            print(f"  [{index}] {device.get('name')}  "
                  f"channels={channels} rate={int(device.get('default_samplerate', 0))}{default}")
    elif _audio_backend == "pyaudio":
        pa = _pyaudio.PyAudio()
        try:
            for index in range(pa.get_device_count()):
                info = pa.get_device_info_by_index(index)
                if info.get("maxInputChannels", 0) < 1:
                    continue
                print(f"  [{index}] {info.get('name')}  "
                      f"channels={info.get('maxInputChannels')} "
                      f"rate={int(info.get('defaultSampleRate', 0))}")
        finally:
            pa.terminate()
    else:
        print("  No audio backend installed. Run: pip install -r requirements.txt")
        return

    print()
    print("  Set MIC_DEVICE in .env to a number or part of a name:")
    print("      MIC_DEVICE=2")
    print("      MIC_DEVICE=headset")


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
            device=_resolve_sd_device(),
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
            input_device_index=_resolve_pa_device(pa),
        )
        return pa, stream

    def wait_for_wake_word(self) -> None:
        """Block until the wake word is detected, then return.

        Uses the pluggable detector in wake_word.py (Porcupine or openWakeWord).
        """
        if _audio_backend is None:
            raise RuntimeError("No audio backend - cannot run wake word.")

        import config
        from wake_word import WakeWordDetector

        detector = WakeWordDetector(
            engine=config.WAKE_ENGINE,
            access_key=self.access_key,
            keyword_path=self.keyword_path,
            model=config.WAKEWORD_MODEL,
            threshold=config.WAKEWORD_THRESHOLD,
        )
        frame_len = detector.frame_length
        rate = detector.sample_rate

        stream = None
        pa = None
        try:
            logger.info(
                f"Listening for wake word (engine={detector.name}, "
                f"frame={frame_len}, rate={rate})..."
            )

            if _audio_backend == "sounddevice":
                stream = self._sd_open_input(rate=rate, blocksize=frame_len)
                while True:
                    raw = self._sd_read_bytes(stream, frame_len)
                    if detector.process(raw):
                        logger.info("Wake word detected!")
                        break
            else:
                pa, stream = self._pa_open_input(rate=rate, frames_per_buffer=frame_len)
                while True:
                    raw = stream.read(frame_len, exception_on_overflow=False)
                    if detector.process(raw):
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
            detector.close()

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

            # Both branches fall through to here. Returning the frames is
            # essential — without it this function yields None and the caller
            # reports "I couldn't hear you" even though the mic worked.
            audio = b"".join(frames)
            if not audio:
                logger.warning("Recorded zero bytes - falling back to fixed duration.")
                return self._record_fixed(5.0)
            return audio

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
            # Must return after the loop — returning inside it would capture
            # only the first 64 ms instead of the full duration.
            return b"".join(frames)
        finally:
            stream.stop_stream()
            stream.close()
            pa.terminate()

    def close(self):
        """No-op for souddevice; pyaudio cleanup is handles per-stream."""
        logger.debug("MicManager.close() - nothing to clean up.")




if __name__ == "__main__":
    import sys

    if "--list-devices" in sys.argv or "-l" in sys.argv:
        list_devices()
    elif "--test-mic" in sys.argv:
        import config

        print(f"Backend: {_backend_label} | VAD: {_vad_backend}")
        print(f"MIC_DEVICE: {config.MIC_DEVICE or '(system default)'}")
        manager = MicManager(None, None)
        print("Recording 3 seconds — speak now...")
        audio = manager.record_command(max_duration=3.0, silence_timeout=1.0)
        if audio:
            print(f"OK — captured {len(audio)} bytes "
                  f"({len(audio) / 32000:.1f}s of audio)")
            print("If the byte count is tiny, your mic is capturing silence.")
        else:
            print("FAILED — no audio captured. Check MIC_DEVICE.")
    else:
        print("Usage:")
        print("  python mic_manager.py --list-devices   show input devices")
        print("  python mic_manager.py --test-mic       record 3 seconds and report")
