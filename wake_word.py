"""
wake_word.py — Unified, pluggable wake word detection.

Two backends:

  porcupine     Picovoice. Needs an AccessKey. The signup form asks for a
                 corporate email, so plenty of people cannot get one.

  openwakeword  Fully local ONNX models. No API key, no signup, no billing,
                 no phone-home. Ships a pretrained "hey jarvis" model that
                 works out of the box. Apache-2.0 code, and the bundled
                 models are CC BY-NC-SA 4.0 (fine for personal use).

Pick one with the WAKE_ENGINE environment variable:

  WAKE_ENGINE=auto          porcupine if a key is set, otherwise openwakeword
  WAKE_ENGINE=openwakeword  force openWakeWord
  WAKE_ENGINE=porcupine     force Porcupine

Both backends expose the same interface:

    detector = WakeWordDetector()
    detector.frame_length   # samples per frame
    detector.sample_rate    # Hz
    detector.process(raw)   # raw int16 PCM bytes -> True when activated
    detector.close()
"""

import importlib
import logging
import struct

logger = logging.getLogger(__name__)

# openWakeWord works on 80 ms frames of 16 kHz mono audio.
OWW_FRAME_SAMPLES = 1280
OWW_SAMPLE_RATE = 16000


class WakeWordError(RuntimeError):
    """Raised when no wake word backend can be initialised."""


class PorcupineBackend:
    """Picovoice Porcupine. Requires a valid AccessKey."""

    name = "porcupine"

    def __init__(self, access_key=None, keyword_path=None, keyword="jarvis"):
        if not access_key:
            raise WakeWordError(
                "Porcupine needs an AccessKey. Get one at "
                "https://console.picovoice.ai/ or use openWakeWord instead "
                "(set WAKE_ENGINE=openwakeword)."
            )
        pvporcupine = importlib.import_module("pvporcupine")
        if keyword_path:
            self._handle = pvporcupine.create(
                access_key=access_key, keyword_path=[keyword_path]
            )
        else:
            self._handle = pvporcupine.create(access_key=access_key, keyword=[keyword])
        self.frame_length = self._handle.frame_length
        self.sample_rate = self._handle.sample_rate

    def process(self, raw: bytes) -> bool:
        needed = self.frame_length * 2
        if len(raw) < needed:
            return False
        samples = struct.unpack_from(f"h{self.frame_length}", raw[:needed])
        return self._handle.process(samples) >= 0

    def close(self):
        try:
            self._handle.delete()
        except Exception:  # pragma: no cover - best effort cleanup
            pass


class OpenWakeWordBackend:
    """openWakeWord. Local ONNX inference, no credentials of any kind."""

    name = "openwakeword"

    def __init__(self, model="hey_jarvis", threshold=0.5, model_path=None):
        importlib.import_module("openwakeword")
        oww_model = importlib.import_module("openwakeword.model")
        oww_utils = importlib.import_module("openwakeword.utils")

        models = [model_path] if model_path else [model]

        # The pip wheel does not bundle the models. They are fetched once
        # from GitHub Releases and then cached on disk forever.
        if not model_path:
            self._download(oww_utils, model)

        # Prefer ONNX: tflite-runtime has no wheels for Python 3.12+.
        self._model = oww_model.Model(
            wakeword_models=models, inference_framework="onnx"
        )
        self.threshold = threshold
        self.frame_length = OWW_FRAME_SAMPLES
        self.sample_rate = OWW_SAMPLE_RATE
        self._buffer = bytearray()
        logger.info(
            f"openWakeWord ready (model={model}, threshold={threshold})."
        )

    @staticmethod
    def _download(utils, model: str) -> None:
        """Fetch the model. The kwarg name changed between releases."""
        for kwargs in ({"model_names": [model]}, {"models": [model]}):
            try:
                utils.download_models(**kwargs)
                return
            except TypeError:
                continue
            except Exception as e:  # network failure, offline, etc.
                logger.warning(f"Could not download wake word model '{model}': {e}")
                return
        logger.warning(
            "Could not download wake word model. If you are offline, fetch it "
            "manually from https://github.com/dscripka/openWakeWord/releases"
        )

    def process(self, raw: bytes) -> bool:
        self._buffer.extend(raw)
        needed = self.frame_length * 2
        if len(self._buffer) < needed:
            return False
        frame = bytes(self._buffer[:needed])
        del self._buffer[:needed]

        try:
            scores = self._model.predict(frame)
        except Exception as e:
            logger.error(f"openWakeWord prediction failed: {e}")
            return False

        for score in scores.values():
            if score >= self.threshold:
                logger.info(f"Wake word score {score:.2f} >= {self.threshold}")
                return True
        return False

    def close(self):
        self._buffer.clear()


def _create_backend(
    engine="auto",
    access_key=None,
    keyword_path=None,
    model="hey_jarvis",
    threshold=0.5,
    model_path=None,
):
    """Build the requested backend, falling back gracefully."""
    engine = (engine or "auto").strip().lower()

    if engine == "openwakeword":
        return OpenWakeWordBackend(model=model, threshold=threshold, model_path=model_path)

    if engine == "porcupine":
        return PorcupineBackend(access_key=access_key, keyword_path=keyword_path)

    # auto — prefer Porcupine when it is fully configured, else openWakeWord
    if access_key:
        try:
            backend = PorcupineBackend(access_key=access_key, keyword_path=keyword_path)
            logger.info("Wake word engine: porcupine")
            return backend
        except Exception as e:
            logger.warning(
                f"Porcupine unavailable ({e}). Switching to openWakeWord."
            )

    try:
        backend = OpenWakeWordBackend(model=model, threshold=threshold, model_path=model_path)
        logger.info("Wake word engine: openwakeword")
        return backend
    except ImportError:
        raise WakeWordError(
            "No wake word backend available. Install one with:\n"
            "  pip install openwakeword onnxruntime    (no signup needed)\n"
            "  pip install pvporcupine                   (needs an AccessKey)"
        )


class WakeWordDetector:
    """Backend-agnostic wake word detector."""

    def __init__(
        self,
        engine="auto",
        access_key=None,
        keyword_path=None,
        model="hey_jarvis",
        threshold=0.5,
        model_path=None,
    ):
        self._backend = _create_backend(
            engine=engine,
            access_key=access_key,
            keyword_path=keyword_path,
            model=model,
            threshold=threshold,
            model_path=model_path,
        )
        self.name = self._backend.name

    @property
    def frame_length(self) -> int:
        return self._backend.frame_length

    @property
    def sample_rate(self) -> int:
        return self._backend.sample_rate

    def process(self, raw: bytes) -> bool:
        return self._backend.process(raw)

    def close(self):
        self._backend.close()
