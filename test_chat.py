"""
test_chat.py — Tests for the text chat mode, recording and device selection.

Covers the fixes for:
  - record_command() never returning the recorded audio
  - _record_fixed() returning only the first chunk
  - mic device selection
  - chat mode routing and slash commands

Run: python test_chat.py
"""

import io
import os
import struct
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
    "edge_tts", "pytesseract",
]:
    sys.modules.setdefault(_m, types.ModuleType(_m))

# openai stub needs the exception classes brain.py imports
_openai = types.ModuleType("openai")
for _exc in ("APIConnectionError", "APIError", "AuthenticationError", "RateLimitError"):
    setattr(_openai, _exc, type(_exc, (Exception,), {}))
_openai.OpenAI = type("OpenAI", (), {"__init__": lambda self, **kw: None})
sys.modules["openai"] = _openai

# webrtcvad stub needs a Vad class
_webrtcvad = types.ModuleType("webrtcvad")
_webrtcvad.Vad = type("Vad", (), {"__init__": lambda self, aggr=2: None,
                                   "is_speech": lambda self, d, r: True})
sys.modules["webrtcvad"] = _webrtcvad

os.environ.setdefault("OPENAI_API_KEY", "test-key")

class _FakeArray:
    """Mimics the numpy array sounddevice returns."""

    def __init__(self, data):
        self._data = data

    def tobytes(self):
        return self._data

    def flatten(self):
        return self._data


results = []


def check(name, fn):
    try:
        ok, detail = fn()
    except Exception as e:
        ok, detail = False, f"{type(e).__name__}: {e}"
    results.append((name, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


print("=" * 62)
print("  JARVIS — Chat mode, recording and device tests")
print("=" * 62)
print()

# ── Recording ───────────────────────────────────────────────────────────
print("Recording")
print("-" * 62)


def record_returns_audio():
    """record_command() must return the captured bytes.

    It used to fall off the end of the function and return None, so the
    voice loop always said "Sorry, I couldn't hear you".
    """
    import mic_manager

    class FakeStream:
        def __init__(self, chunks):
            self.chunks = list(chunks)
            self.started = False
            self.stopped = False

        def start(self):
            self.started = True

        def read(self, n, **kw):
            chunk = self.chunks.pop(0) if self.chunks else b"\x00" * 2048
            return _FakeArray(chunk), False

        def stop(self):
            self.stopped = True

        def close(self):
            pass

    manager = mic_manager.MicManager(None, None)
    manager._sd_open_input = lambda rate, blocksize: FakeStream([b"\x01\x02" * 480])

    audio = manager.record_command(max_duration=0.2, silence_timeout=1.0)
    if audio is None:
        return False, "record_command returned None"
    if not isinstance(audio, bytes):
        return False, f"returned {type(audio).__name__}"
    if len(audio) == 0:
        return False, "returned zero bytes"
    return True, f"returned {len(audio)} bytes"


def record_fixed_returns_full_duration():
    """_record_fixed must capture the whole duration, not just one chunk."""
    import mic_manager

    class FakeStream:
        def __init__(self):
            self.reads = 0

        def read(self, n, **kw):
            self.reads += 1
            return _FakeArray(b"\x00" * n), False

        def stop(self):
            pass

        def close(self):
            pass

    manager = mic_manager.MicManager(None, None)
    created = {}

    def fake_open(rate, blocksize):
        stream = FakeStream()
        created["stream"] = stream
        return stream

    manager._sd_open_input = fake_open
    audio = manager._record_fixed(0.5)
    expected = 16000 * 0.5  # 16 kHz, 16-bit mono
    if len(audio) < expected * 0.9:
        return False, f"got {len(audio)} bytes, expected ~{int(expected)}"
    if created["stream"].reads < 5:
        return False, f"only {created['stream'].reads} reads — returned early"
    return True, f"{len(audio)} bytes over {created['stream'].reads} reads"


def record_handles_no_backend():
    import mic_manager

    original = mic_manager._audio_backend
    mic_manager._audio_backend = None
    try:
        manager = mic_manager.MicManager(None, None)
        try:
            manager.record_command()
        except RuntimeError as e:
            if "No audio backend" in str(e):
                return True, "clear error"
            return False, f"unexpected: {e}"
        return False, "no error raised"
    finally:
        mic_manager._audio_backend = original


check("record_command() returns the captured audio", record_returns_audio)
check("_record_fixed() captures the full duration", record_fixed_returns_full_duration)
check("no backend gives a clear error", record_handles_no_backend)


# ── Device selection ────────────────────────────────────────────────────
print()
print("Microphone device selection")
print("-" * 62)


def device_config_exists():
    import importlib
    import config
    importlib.reload(config)
    if not hasattr(config, "MIC_DEVICE"):
        return False, "config.MIC_DEVICE missing"
    return True, f"MIC_DEVICE = {config.MIC_DEVICE!r}"


def device_resolves_by_name():
    """MIC_DEVICE can be part of a device name."""
    import importlib
    import config
    import mic_manager
    importlib.reload(config)
    importlib.reload(mic_manager)

    config.MIC_DEVICE = "headset"

    def device(name, channels):
        return {"name": name, "max_input_channels": channels,
                "default_samplerate": 48000}

    mic_manager._sd = types.SimpleNamespace(
        query_devices=lambda: [
            device("Headset Microphone", 1),
            device("Speakers", 0),
        ]
    )
    index = mic_manager._resolve_sd_device()
    if index != 0:
        return False, f"expected device 0, got {index}"
    return True, "'headset' matched 'Headset Microphone'"


def device_resolves_by_index():
    import importlib
    import config
    import mic_manager
    importlib.reload(config)
    importlib.reload(mic_manager)

    config.MIC_DEVICE = "3"

    def device(name, channels):
        return {"name": name, "max_input_channels": channels,
                "default_samplerate": 48000}

    mic_manager._sd = types.SimpleNamespace(
        query_devices=lambda: [device(f"mic {i}", 1) for i in range(4)]
    )
    index = mic_manager._resolve_sd_device()
    if index != 3:
        return False, f"expected device 3, got {index}"
    return True, "numeric index honoured"


def device_defaults_to_system():
    import importlib
    import config
    import mic_manager
    importlib.reload(config)
    importlib.reload(mic_manager)

    config.MIC_DEVICE = ""
    index = mic_manager._resolve_sd_device()
    if index is not None:
        return False, f"expected None (system default), got {index}"
    return True, "empty MIC_DEVICE uses the system default"


def device_ignores_output_only_devices():
    """A device with 0 input channels must never be selected."""
    import importlib
    import config
    import mic_manager
    importlib.reload(config)
    importlib.reload(mic_manager)

    config.MIC_DEVICE = "speaker"

    def device(name, channels):
        return {"name": name, "max_input_channels": channels,
                "default_samplerate": 48000}

    mic_manager._sd = types.SimpleNamespace(
        query_devices=lambda: [
            device("Speakers", 0),
            device("USB Mic", 1),
        ]
    )
    index = mic_manager._resolve_sd_device()
    if index is not None:
        return False, f"output-only device selected ({index})"
    return True, "no input device matched — fell back to default"


check("config.MIC_DEVICE exists", device_config_exists)
check("MIC_DEVICE resolves by name", device_resolves_by_name)
check("MIC_DEVICE resolves by index", device_resolves_by_index)
check("empty MIC_DEVICE uses the system default", device_defaults_to_system)
check("output-only devices are never selected", device_ignores_output_only_devices)


# ── Chat routing ────────────────────────────────────────────────────────
print()
print("Chat mode")
print("-" * 62)


def chat_routes_to_skill():
    """Keyword-matched skills must be used before the LLM."""
    from conversation import handle_command

    class FakeMemory:
        def __init__(self):
            self.turns = []

        def add_turn(self, u, r):
            self.turns.append((u, r))

    class FakeBrain:
        def __init__(self):
            self.memory = FakeMemory()
            self.llm_calls = 0

        def process(self, text):
            self.llm_calls += 1
            return "LLM response"

    brain = FakeBrain()
    response, source = handle_command("what time is it", brain)
    if source != "skill:time":
        return False, f"expected skill:time, got {source}"
    if brain.llm_calls:
        return False, "the LLM was called even though a skill matched"
    if not response:
        return False, "empty response"
    return True, f"'{response}' via {source}"


def chat_falls_back_to_llm():
    from conversation import handle_command

    class FakeMemory:
        def add_turn(self, u, r):
            pass

    class FakeBrain:
        def __init__(self):
            self.memory = FakeMemory()
            self.llm_calls = 0

        def process(self, text):
            self.llm_calls += 1
            return "LLM response"

    brain = FakeBrain()
    response, source = handle_command("who won the world cup in 1998", brain)
    if source != "llm":
        return False, f"expected llm, got {source}"
    if brain.llm_calls != 1:
        return False, f"LLM called {brain.llm_calls} times"
    if response != "LLM response":
        return False, f"unexpected response {response!r}"
    return True, "unmatched input goes to the LLM"


def chat_records_skill_turns_in_memory():
    """A skill answer must still be remembered."""
    from conversation import handle_command

    class FakeMemory:
        def __init__(self):
            self.turns = []

        def add_turn(self, u, r):
            self.turns.append((u, r))

    class FakeBrain:
        def __init__(self):
            self.memory = FakeMemory()

        def process(self, text):
            return "LLM"

    brain = FakeBrain()
    handle_command("what time is it", brain)
    if not brain.memory.turns:
        return False, "skill turn was not stored in memory"
    return True, f"{len(brain.memory.turns)} turn(s) stored"


def chat_handles_empty_input():
    from conversation import handle_command

    class FakeBrain:
        memory = None

    response, source = handle_command("   ", FakeBrain())
    if source != "empty":
        return False, f"expected empty, got {source}"
    return True, "blank input is ignored"


def chat_survives_brain_failure():
    """A failing LLM must not crash the chat loop."""
    from conversation import handle_command

    class FakeMemory:
        def add_turn(self, u, r):
            pass

    class FakeBrain:
        memory = FakeMemory()

        def process(self, text):
            raise RuntimeError("network down")

    response, source = handle_command("something unmatched entirely", FakeBrain())
    if source != "error":
        return False, f"expected error, got {source}"
    if "trouble" not in response.lower():
        return False, f"unexpected message: {response}"
    return True, "LLM failure returns a friendly message"


def chat_slash_commands():
    """The slash commands must work without a keyboard."""
    import chat

    replies = []
    instance = chat.Chat.__new__(chat.Chat)
    instance.brain = types.SimpleNamespace(
        model="test",
        memory=types.SimpleNamespace(enabled=True, storage_path="m.json",
                                     get_messages=lambda: [], clear=lambda: None),
    )
    instance.voice = False
    instance.speaker = None

    original_print = __builtins__.print
    try:
        __builtins__.print = lambda *a, **k: replies.append(" ".join(str(x) for x in a))
        for command in ("/help", "/skills", "/memory", "/voice", "/bogus"):
            instance.handle_command_line(command)
    finally:
        __builtins__.print = original_print

    if len(replies) < 5:
        return False, f"only {len(replies)} replies produced"
    if not any("Commands" in r for r in replies):
        return False, "/help produced no command list"
    if not any("Skills" in r for r in replies):
        return False, "/skills listed nothing"
    return True, f"{len(replies)} replies, all commands handled"


check("keyword skills are used before the LLM", chat_routes_to_skill)
check("unmatched input goes to the LLM", chat_falls_back_to_llm)
check("skill answers are stored in memory", chat_records_skill_turns_in_memory)
check("blank input is ignored", chat_handles_empty_input)
check("an LLM failure returns a friendly message", chat_survives_brain_failure)
check("slash commands all work", chat_slash_commands)


# ── Skill reachability ──────────────────────────────────────────────────
print()
print("Skill and tool reachability")
print("-" * 62)


def all_skills_are_reachable():
    """Every skill must be reachable from the registry."""
    from conversation import list_skills

    names = list_skills()
    expected = {"time", "date", "joke", "timer", "weather",
                "document_creator", "document_reader"}
    missing = expected - set(names)
    if missing:
        return False, f"unreachable skills: {sorted(missing)}"
    return True, f"{len(names)} skills reachable"


def document_tools_are_exposed():
    """The LLM must be able to reach the document skills."""
    import inspect
    import re
    import tools

    names = {t["function"]["name"] for t in tools.SKILL_TOOLS}
    for required in ("read_document", "create_document"):
        if required not in names:
            return False, f"{required} missing from SKILL_TOOLS"
    handlers = set(re.findall(r'function_name == "(\w+)"', inspect.getsource(tools.execute_tool)))
    orphans = names - handlers
    if orphans:
        return False, f"schemas without handlers: {sorted(orphans)}"
    return True, f"{len(names)} tools, all with handlers"


check("every skill is reachable", all_skills_are_reachable)
check("document tools are exposed to the LLM", document_tools_are_exposed)


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
