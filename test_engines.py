"""
test_engines.py — Tests for the pluggable wake word, TTS and OCR engines.

These cover the "no signup, no credit card" path: every engine must be
selectable without a Picovoice key or a Google billing account.

Run: python test_engines.py
"""

import os
import sys
import types

# Stub third-party deps that are not installed in the sandbox
for _m in [
    "pvporcupine", "pyaudio", "sounddevice", "webrtcvad", "pygame",
    "numpy", "openai", "dotenv", "requests", "docx", "PIL", "PIL.ImageGrab",
    "comtypes", "pycaw", "pycaw.pycaw", "google", "google.cloud",
    "google.cloud.texttospeech", "google.cloud.vision",
    "google.oauth2", "google.oauth2.service_account", "google.auth",
    "google.auth.transport", "google.auth.transport.requests",
    "edge_tts", "openwakeword", "openwakeword.model", "openwakeword.utils",
    "pytesseract",
]:
    sys.modules.setdefault(_m, types.ModuleType(_m))


# Give the pygame stub a working mixer so Speaker() can be constructed
class _FakeMixer:
    def init(self):
        pass

    def get_busy(self):
        return False

    def Sound(self, *a, **kw):
        raise RuntimeError("no audio device in the sandbox")


class _FakePygame:
    mixer = _FakeMixer()

    class time:
        @staticmethod
        def wait(_ms):
            pass


sys.modules["pygame"].mixer = _FakeMixer()
sys.modules["pygame"].time = _FakePygame.time

os.environ.setdefault("OPENAI_API_KEY", "test-key")

results = []


def check(name, fn):
    try:
        ok, detail = fn()
    except Exception as e:
        ok, detail = False, f"{type(e).__name__}: {e}"
    results.append((name, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


print("=" * 62)
print("  JARVIS — Engine selection tests")
print("=" * 62)
print()

# ── Wake word ───────────────────────────────────────────────────────────
print("Wake word engine selection")
print("-" * 62)


def wake_no_key_uses_openwakeword():
    """With no Picovoice key, Jarvis must fall back to openWakeWord
    instead of dying. This is the whole point of the swap."""
    import importlib
    import wake_word
    importlib.reload(wake_word)

    calls = {}

    class FakeModel:
        def __init__(self, **kwargs):
            calls["init"] = kwargs

        def predict(self, frame):
            return {"hey_jarvis": 0.9}

    fake_model_mod = types.ModuleType("openwakeword.model")
    fake_model_mod.Model = FakeModel
    fake_utils = types.ModuleType("openwakeword.utils")
    fake_utils.download_models = lambda **kw: calls.setdefault("download", kw)
    sys.modules["openwakeword.model"] = fake_model_mod
    sys.modules["openwakeword.utils"] = fake_utils
    sys.modules["openwakeword"] = types.ModuleType("openwakeword")

    detector = wake_word.WakeWordDetector(engine="auto", access_key=None)
    if detector.name != "openwakeword":
        return False, f"expected openwakeword, got {detector.name}"
    if detector.frame_length != 1280:
        return False, f"expected 1280-sample frames, got {detector.frame_length}"
    if detector.sample_rate != 16000:
        return False, f"expected 16000 Hz, got {detector.sample_rate}"
    return True, "no key -> openwakeword, 1280 samples @ 16 kHz"


def wake_openwakeword_detects():
    import wake_word
    detector = wake_word.WakeWordDetector(engine="openwakeword", access_key=None)
    frame = b"\x00\x01" * 1280
    if not detector.process(frame):
        return False, "score 0.9 did not trigger"
    return True, "score above threshold triggers"


def wake_openwakeword_respects_threshold():
    import wake_word
    fake_model_mod = types.ModuleType("openwakeword.model")

    class LowModel:
        def __init__(self, **kwargs):
            pass

        def predict(self, frame):
            return {"hey_jarvis": 0.2}

    fake_model_mod.Model = LowModel
    sys.modules["openwakeword.model"] = fake_model_mod

    detector = wake_word.WakeWordDetector(
        engine="openwakeword", access_key=None, threshold=0.5
    )
    if detector.process(b"\x00\x01" * 1280):
        return False, "low score triggered a false positive"
    return True, "score 0.2 below threshold 0.5 stays quiet"


def wake_forced_porcupine_without_key_errors():
    """Forcing porcupine with no key must fail loudly, not silently."""
    import wake_word
    try:
        wake_word.WakeWordDetector(engine="porcupine", access_key=None)
    except wake_word.WakeWordError as e:
        if "AccessKey" in str(e):
            return True, "clear error message"
        return False, f"unexpected message: {e}"
    return False, "no error raised"


check("no Picovoice key -> openWakeWord", wake_no_key_uses_openwakeword)
check("openWakeWord detects a frame above threshold", wake_openwakeword_detects)
check("openWakeWord respects the threshold", wake_openwakeword_respects_threshold)
check("forced porcupine without key raises a clear error", wake_forced_porcupine_without_key_errors)


# ── TTS ─────────────────────────────────────────────────────────────────
print()
print("TTS engine selection")
print("-" * 62)


def tts_defaults_to_edge():
    """Without Google credentials, the edge engine must be chosen so the
    user never needs a billing account."""
    import importlib
    import config
    import speaker
    importlib.reload(config)
    importlib.reload(speaker)

    config.GOOGLE_APPLICATION_CREDENTIALS = None
    config.TTS_ENGINE = "auto"
    s = speaker.Speaker()
    if s.engine != "edge":
        return False, f"expected edge, got {s.engine}"
    return True, "no Google creds -> edge"


def tts_respects_explicit_engine():
    import importlib
    import config
    import speaker
    importlib.reload(config)
    importlib.reload(speaker)

    config.GOOGLE_APPLICATION_CREDENTIALS = None
    config.TTS_ENGINE = "sapi"
    s = speaker.Speaker()
    if s.engine != "sapi":
        return False, f"expected sapi, got {s.engine}"
    return True, "TTS_ENGINE=sapi honoured"


def tts_google_chosen_when_configured():
    import importlib
    import config
    import speaker
    importlib.reload(config)
    importlib.reload(speaker)

    config.TTS_ENGINE = "google"
    config.GOOGLE_APPLICATION_CREDENTIALS = __file__  # any existing file
    s = speaker.Speaker()
    if s.engine != "google":
        return False, f"expected google, got {s.engine}"
    return True, "TTS_ENGINE=google honoured"


def tts_edge_chain_falls_back_to_sapi():
    """If the edge engine fails at runtime, Jarvis must still speak."""
    import importlib
    import config
    import speaker
    importlib.reload(config)
    importlib.reload(speaker)

    config.TTS_ENGINE = "edge"
    s = speaker.Speaker()
    called = {}

    def boom(text):
        raise RuntimeError("network down")

    s._synthesize = boom
    s._speak_sapi = lambda text: called.setdefault("sapi", text)
    s.speak("hello")
    if "sapi" not in called:
        return False, "offline fallback never triggered"
    return True, "edge failure -> offline voice"


check("no Google creds -> edge TTS", tts_defaults_to_edge)
check("TTS_ENGINE=sapi is honoured", tts_respects_explicit_engine)
check("TTS_ENGINE=google is honoured", tts_google_chosen_when_configured)
check("edge failure falls back to the offline voice", tts_edge_chain_falls_back_to_sapi)


# ── OCR ─────────────────────────────────────────────────────────────────
print()
print("OCR engine selection")
print("-" * 62)


def ocr_auto_prefers_free_engines():
    """The auto order must put the no-billing engines first."""
    import importlib
    import config
    import document_reader_skill
    importlib.reload(config)
    importlib.reload(document_reader_skill)

    config.OCR_ENGINE = "auto"
    config.OPENROUTER_API_KEY = None
    config.GOOGLE_APPLICATION_CREDENTIALS = None
    skill = document_reader_skill.DocumentReaderSkill()
    order = skill._engine_order("auto")
    if order[0] != "ocrspace":
        return False, f"expected ocrspace first, got {order}"
    if "google" in order:
        return False, f"google should not be in the order without creds: {order}"
    return True, f"order = {order}"


def ocr_auto_prefers_openrouter_when_keyed():
    import importlib
    import config
    import document_reader_skill
    importlib.reload(config)
    importlib.reload(document_reader_skill)

    config.OCR_ENGINE = "auto"
    config.OPENROUTER_API_KEY = "sk-or-test"
    config.GOOGLE_APPLICATION_CREDENTIALS = None
    skill = document_reader_skill.DocumentReaderSkill()
    order = skill._engine_order("auto")
    if order[0] != "openrouter":
        return False, f"expected openrouter first, got {order}"
    return True, f"order = {order}"


def ocr_explicit_engine_is_respected():
    import importlib
    import config
    import document_reader_skill
    importlib.reload(config)
    importlib.reload(document_reader_skill)

    skill = document_reader_skill.DocumentReaderSkill()
    for engine in ("openrouter", "ocrspace", "google", "tesseract"):
        order = skill._engine_order(engine)
        if order != [engine]:
            return False, f"{engine} -> {order}"
    return True, "all four explicit engines respected"


def ocr_saves_text_next_to_image():
    """The extracted text must be written to disk next to the image."""
    import importlib
    import tempfile
    import config
    import document_reader_skill
    importlib.reload(config)
    importlib.reload(document_reader_skill)

    with tempfile.TemporaryDirectory() as tmp:
        img = os.path.join(tmp, "note.png")
        with open(img, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n")

        skill = document_reader_skill.DocumentReaderSkill()
        skill._extract_text = lambda path: ("hello world", "Test")

        # call the real save path
        out = skill._save_text(img, "hello world")
        if not os.path.exists(out):
            return False, f"no file at {out}"
        with open(out) as f:
            if f.read() != "hello world":
                return False, "wrong content"
    return True, "text saved to note.txt"


def ocr_missing_file_is_handled():
    import importlib
    import config
    import document_reader_skill
    importlib.reload(config)
    importlib.reload(document_reader_skill)

    skill = document_reader_skill.DocumentReaderSkill()
    reply = skill.handle("read this nonexistent-file.png")
    if "couldn't find" not in reply.lower():
        return False, f"unexpected reply: {reply}"
    return True, "missing file handled gracefully"


check("auto order prefers no-billing engines", ocr_auto_prefers_free_engines)
check("auto order prefers openrouter when keyed", ocr_auto_prefers_openrouter_when_keyed)
check("explicit OCR engine is respected", ocr_explicit_engine_is_respected)
check("OCR text is saved next to the image", ocr_saves_text_next_to_image)
check("missing image is handled gracefully", ocr_missing_file_is_handled)


# ── Config validation ───────────────────────────────────────────────────
print()
print("Config validation")
print("-" * 62)


def validation_does_not_require_porcupine():
    """Missing optional keys must warn, not exit."""
    import importlib
    import config
    importlib.reload(config)

    config.OPENAI_API_KEY = "test-key"
    config.PORCUPINE_ACCESS_KEY = None
    config.GOOGLE_APPLICATION_CREDENTIALS = None
    config.WAKE_ENGINE = "auto"
    config.TTS_ENGINE = "auto"
    config.OCR_ENGINE = "auto"

    try:
        config.validate_required_keys()
    except SystemExit as e:
        return False, f"exited with code {e.code} — should only warn"
    return True, "no hard exit for missing optional keys"


def validation_still_requires_openai_key():
    import importlib
    import config
    importlib.reload(config)

    config.OPENAI_API_KEY = None
    try:
        config.validate_required_keys()
    except SystemExit as e:
        if e.code == 1:
            return True, "exits when the LLM key is missing"
        return False, f"wrong exit code {e.code}"
    return False, "did not exit without OPENAI_API_KEY"


check("missing optional keys only warn", validation_does_not_require_porcupine)
check("missing OPENAI_API_KEY still exits", validation_still_requires_openai_key)


# ── SimpleVAD ───────────────────────────────────────────────────────────
print()
print("SimpleVAD (the webrtcvad replacement on Python 3.12+)")
print("-" * 62)


def vad_threshold_is_a_number():
    """The threshold must be a number, not the threshold *mapping*.
    Comparing a float against a dict raises TypeError on every call."""
    import importlib
    import simple_vad
    importlib.reload(simple_vad)

    vad = simple_vad.SimpleVAD(2)
    if not isinstance(vad.threshold, (int, float)):
        return False, f"threshold is {type(vad.threshold).__name__}"
    return True, f"threshold = {vad.threshold}"


def vad_detects_speech():
    import struct
    import simple_vad
    vad = simple_vad.SimpleVAD(2)
    silence = struct.pack("<1000h", *([0] * 1000))
    loud = struct.pack("<1000h", *([3000] * 1000))
    if vad.is_speech(silence):
        return False, "silence detected as speech"
    if not vad.is_speech(loud):
        return False, "loud audio not detected"
    return True, "silence rejected, speech accepted"


def vad_handles_edge_cases():
    import simple_vad
    vad = simple_vad.SimpleVAD(2)
    if vad.is_speech(b""):
        return False, "empty input treated as speech"
    if vad.is_speech(b"\x01"):
        return False, "1-byte input treated as speech"
    if vad.is_speech(b"\x00" * 3):
        return False, "odd-length silence treated as speech"
    return True, "empty, 1-byte and odd-length inputs handled"


def vad_aggressiveness_is_adjustable():
    import simple_vad
    vad = simple_vad.SimpleVAD(2)
    default = vad.threshold
    vad.set_aggressiveness(3)
    if vad.threshold <= default:
        return False, "stricter level did not raise the threshold"
    return True, f"{default} -> {vad.threshold}"


check("threshold is a number, not the mapping", vad_threshold_is_a_number)
check("detects speech and rejects silence", vad_detects_speech)
check("handles empty and odd-length input", vad_handles_edge_cases)
check("aggressiveness is adjustable at runtime", vad_aggressiveness_is_adjustable)


# ── Summary ────────────────────────────────────────────────────────────
print()
print("=" * 62)
passed = sum(1 for _, ok, _ in results if ok)
total = len(results)
if passed == total:
    print(f"  RESULT: {passed}/{total} passed")
    print("=" * 62)
    sys.exit(0)
else:
    print(f"  RESULT: {passed}/{total} passed, {total - passed} FAILED")
    for name, ok, detail in results:
        if not ok:
            print(f"    FAILED: {name} — {detail}")
    print("=" * 62)
    sys.exit(1)
