"""
test_fixes.py — Regression tests for the 7 bugs fixed in this pass.

Run: python test_fixes.py
"""

import os
import sys
import types
import tempfile

# Stub third-party deps that aren't installed in the sandbox
for _m in [
    "pvporcupine", "pyaudio", "sounddevice", "webrtcvad", "pygame",
    "numpy", "openai", "dotenv", "requests", "docx", "PIL", "PIL.ImageGrab",
    "comtypes", "pycaw", "pycaw.pycaw", "google", "google.cloud",
    "google.cloud.texttospeech", "google.cloud.vision",
    "google.oauth2", "google.oauth2.service_account", "google.auth",
    "google.auth.transport", "google.auth.transport.requests",
]:
    sys.modules.setdefault(_m, types.ModuleType(_m))

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("PORCUPINE_ACCESS_KEY", "test-key")

results = []


def check(name, fn):
    try:
        ok, detail = fn()
    except Exception as e:
        ok, detail = False, f"{type(e).__name__}: {e}"
    results.append((name, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


print("=" * 62)
print("  JARVIS — Regression tests for fixed bugs")
print("=" * 62)
print()

# ── BUG 1: config typo killed all of Layer 4 function calling ──
print("Bug 1 — config.py SCREENSHOTS_DIR typo")
print("-" * 62)


def bug1():
    import config
    if not hasattr(config, "SCREENSHOTS_DIR"):
        return False, "config has no SCREENSHOTS_DIR"
    import tools
    if not tools.SKILL_TOOLS:
        return False, "SKILL_TOOLS is empty — Layer 4 dead"
    if tools.SCREENSHOTS_DIR != config.SCREENSHOTS_DIR:
        return False, "screenshot dir mismatch"
    return True, f"{len(tools.SKILL_TOOLS)} tools registered"


check("config.SCREENSHOTS_DIR exists and tools imports it", bug1)


# ── BUG 2/3/4: memory.py ──
print()
print("Bugs 2-4 — memory.py get_messages / get_context / _save")
print("-" * 62)


def bug2():
    from memory import ConversationMemory
    m = ConversationMemory(storage_path=os.path.join(tempfile.gettempdir(), "jmem_test.json"))
    m.enabled = True
    m.history = [
        {"user_input": "hi", "jarvis_response": "hello"},
        {"user_input": "how are you", "jarvis_response": "good"},
        {"user_input": "bye", "jarvis_response": "see you"},
    ]
    msgs = m.get_messages()
    if len(msgs) != 6:
        return False, f"expected 6 messages (3 turns), got {len(msgs)}"
    if msgs[0]["role"] != "user" or msgs[1]["role"] != "assistant":
        return False, "wrong role order"
    return True, f"returned all {len(msgs)} messages"


def bug3():
    from memory import ConversationMemory
    m = ConversationMemory(storage_path=os.path.join(tempfile.gettempdir(), "jmem_test2.json"))
    m.enabled = True
    m.history = [{"user_input": "hi", "jarvis_response": "hello"}]
    ctx = m.get_context()
    if not isinstance(ctx, list):
        return False, f"get_context returned {type(ctx).__name__}, not list"
    return True, "get_context returns a list"


def bug4():
    from memory import ConversationMemory
    path = os.path.join(tempfile.gettempdir(), "jmem_persist_test.json")
    if os.path.exists(path):
        os.remove(path)
    m = ConversationMemory(storage_path=path)
    m.enabled = True
    m.add_turn("what time is it", "it is 3pm")
    if not os.path.exists(path):
        return False, "memory file was never written"
    import json
    with open(path) as f:
        data = json.load(f)
    if len(data) != 1 or data[0]["user_input"] != "what time is it":
        return False, f"persisted content wrong: {data}"
    os.remove(path)
    return True, "memory persists to disk"


check("get_messages returns ALL turns (was: only 1)", bug2)
check("get_context returns list, not bound method", bug3)
check("_save() writes to storage_path (was: open(self,...))", bug4)


# ── BUG 5: settings.py update_env wiped .env ──
print()
print("Bug 5 — settings.py update_env wiping .env")
print("-" * 62)


def bug5():
    import settings
    cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:
        os.chdir(tmp)
        try:
            with open(".env", "w") as f:
                f.write("OPENAI_API_KEY=gsk_secret123\nPORCUPINE_ACCESS_KEY=abc\n")
            settings.update_env("MEMORY_ENABLED", "False")
            with open(".env") as f:
                content = f.read()
            if "OPENAI_API_KEY=gsk_secret123" not in content:
                return False, "API key was WIPED"
            if "PORCUPINE_ACCESS_KEY=abc" not in content:
                return False, "second key was WIPED"
            if "MEMORY_ENABLED=False" not in content:
                return False, "new key not written"
            return True, "existing keys preserved"
        finally:
            os.chdir(cwd)


check("update_env preserves existing API keys", bug5)


def bug5b():
    """update_env must also work when .env does not exist yet."""
    import settings
    cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:
        os.chdir(tmp)
        try:
            settings.update_env("MEMORY_ENABLED", "True")
            with open(".env") as f:
                content = f.read()
            if "MEMORY_ENABLED=True" not in content:
                return False, "did not create .env"
            return True, "creates .env when missing"
        finally:
            os.chdir(cwd)


check("update_env creates .env when missing", bug5b)


# ── BUG 6: tools.py _open_app missing () ──
print()
print("Bugs 6-7 — tools.py _open_app / _set_volume")
print("-" * 62)


def bug6():
    """_open_app must not raise TypeError from the `name.strip` bug.

    We mock the launcher so the test is deterministic — in a bare sandbox
    Chrome simply isn't installed, which would mask the real regression.
    """
    import tools
    import subprocess as sp

    opened = {}
    orig_popen = sp.Popen
    orig_system = tools.platform.system

    class FakePopen:
        def __init__(self, args, *a, **kw):
            opened["args"] = args

    sp.Popen = FakePopen
    tools.platform.system = lambda: "Linux"
    try:
        result = tools._open_app("chrome")
    finally:
        sp.Popen = orig_popen
        tools.platform.system = orig_system

    if "failed to execute" in result.lower():
        return False, f"execute_tool caught an exception: {result}"
    if "Couldn't open" in result:
        return False, f"still raising internally: {result}"
    if not opened.get("args"):
        return False, "launcher was never invoked"
    return True, f"launched {opened['args'][0]}"


def bug6b():
    import tools
    import subprocess as sp

    opened = {}
    orig_popen = sp.Popen
    orig_system = tools.platform.system

    class FakePopen:
        def __init__(self, args, *a, **kw):
            opened["args"] = args

    sp.Popen = FakePopen
    tools.platform.system = lambda: "Linux"
    try:
        result = tools._open_app("  github.com  ")
    finally:
        sp.Popen = orig_popen
        tools.platform.system = orig_system

    if "failed" in result.lower():
        return False, f"raised internally: {result}"
    if "github.com" not in str(opened.get("args")):
        return False, f"wrong target: {opened.get('args')}"
    return True, f"launched {opened['args'][0]}"


def bug7():
    import tools
    import inspect
    src = inspect.getsource(tools._set_volume)
    if "SetMasterVolumeLevelScaler" in src:
        return False, "wrong pycaw method name still present"
    if "SetMasterVolumeLevelScalar" not in src:
        return False, "correct pycaw method missing"
    return True, "SetMasterVolumeLevelScalar"


check("_open_app('chrome') works (was: name.strip)", bug6)
check("_open_app('github.com') works (was: name.lower)", bug6b)
check("_set_volume uses correct pycaw method name", bug7)


# ── BUG 8: timer unit handling ──
print()
print("Bug 8 — tools.py timer unit handling")
print("-" * 62)


def bug8():
    import tools
    import threading
    captured = {}

    orig_thread = threading.Thread

    class FakeThread:
        def __init__(self, target=None, args=(), daemon=None):
            captured["args"] = args
        def start(self):
            pass

    tools.threading.Thread = FakeThread
    try:
        tools._set_timer(2, "hours")
        if captured["args"][0] != 7200:
            return False, f"2 hours -> {captured['args'][0]}s, expected 7200"
        tools._set_timer(5, "minutes")
        if captured["args"][0] != 300:
            return False, f"5 minutes -> {captured['args'][0]}s, expected 300"
        tools._set_timer(30, "seconds")
        if captured["args"][0] != 30:
            return False, f"30 seconds -> {captured['args'][0]}s, expected 30"
    finally:
        tools.threading.Thread = orig_thread
    return True, "hours/minutes/seconds all correct"


check("set_timer handles hours, minutes, seconds", bug8)


# ── BUG 9: registry never loaded any skills ──
print()
print("Bugs 9-10 — registry discovery + missing tell_joke schema")
print("-" * 62)


def bug9():
    """registry.py used relative imports, so no skill ever loaded when
    running `python main.py` (the documented way to start Jarvis)."""
    import registry
    registry.SkillRegistry._skills = []
    registry.SkillRegistry.discover()
    names = {s.name for s in registry.SkillRegistry._skills}
    expected = {"time", "date", "joke", "timer", "weather",
                "document_creator", "document_reader"}
    missing = expected - names
    if missing:
        return False, f"skills not discovered: {sorted(missing)}"
    return True, f"discovered {len(names)} skills"


def bug9b():
    """The registry must not try to import main.py, settings.py or tests."""
    import registry
    registry.SkillRegistry._skills = []
    registry.SkillRegistry.discover()
    for s in registry.SkillRegistry._skills:
        if s.__class__.__module__.startswith("main") or s.__class__.__module__.startswith("test"):
            return False, f"leaked non-skill module: {s.__class__.__module__}"
    return True, "only *_skill.py modules are scanned"


def bug10():
    """tell_joke had an implementation but was never exposed to the LLM."""
    import tools
    names = {t["function"]["name"] for t in tools.SKILL_TOOLS}
    if "tell_joke" not in names:
        return False, f"tell_joke missing from SKILL_TOOLS (has {sorted(names)})"
    return True, f"{len(names)} tool schemas exposed"


def bug10b():
    """Every exposed tool must have a handler in execute_tool."""
    import re
    import tools
    import inspect
    schemas = {t["function"]["name"] for t in tools.SKILL_TOOLS}
    handlers = set(re.findall(r'function_name == "(\w+)"', inspect.getsource(tools.execute_tool)))
    orphans = schemas - handlers
    if orphans:
        return False, f"no handler for: {sorted(orphans)}"
    return True, "every schema has a handler"


check("registry discovers all 7 skills", bug9)
check("registry only scans *_skill.py files", bug9b)
check("tell_joke is exposed as a tool schema", bug10)
check("every tool schema has an execute_tool handler", bug10b)


# ── Summary ──
print()
print("=" * 62)
passed = sum(1 for _, ok, _ in results if ok)
total = len(results)
if passed == total:
    print(f"  RESULT: {passed}/{total} passed — all bugs fixed")
    print("=" * 62)
    sys.exit(0)
else:
    print(f"  RESULT: {passed}/{total} passed, {total - passed} FAILED")
    for name, ok, detail in results:
        if not ok:
            print(f"    FAILED: {name} — {detail}")
    print("=" * 62)
    sys.exit(1)
