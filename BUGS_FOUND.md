# Bugs Found and Fixed

Every issue below was found by reading the code, then reproducing it with a
failing test. Each fix has a regression test in `test_fixes.py`.

Run `python test_fixes.py` to confirm all 14 checks still pass.

---

## Critical

### 1. All of Layer 4 was silently dead — `config.py` typo

**File:** `config.py:41`
**Symptom:** Every function-calling tool returned `"Tools module missing."`
Web search, app launching, volume control, screenshots, timers and weather
were all non-functional. No error was shown to the user.

**Cause:** The variable was named `SCREEENSHOTS_DIR` (three E's) but
`tools.py:12` imported `SCREENSHOTS_DIR`. The `ImportError` was swallowed by
the `try/except ImportError` in `brain.py`, which replaced the whole tools
module with an empty stub.

```python
# before
SCREEENSHOTS_DIR = os.getenv("SCREENSHOTS_DIR", "./screenshots")

# after
SCREENSHOTS_DIR = os.getenv("SCREENSHOTS_DIR", "./screenshots")
```

**Severity:** Critical — the entire Layer 4 feature set was dead on arrival.

---

### 2. Skill registry never loaded a single skill — `registry.py`

**File:** `registry.py:23`
**Symptom:** `SkillRegistry.discover()` found 0 skills. Time, date, joke,
weather, timer and both document skills were all unavailable. The failure was
logged to `jarvis.log` but never surfaced.

**Cause:** The registry used a relative import
(`importlib.import_module(f".{name}", package=__package__)`) while every other
module used flat absolute imports (`from base import Skill`). Running
`python main.py` leaves `__package__` empty, so every relative import failed.

**Fix:** Try the package-relative import first, fall back to a flat import, and
only scan files ending in `_skill.py` so that `main.py`, `settings.py` and the
test files are never imported as skills.

**Severity:** Critical — no skill worked at all.

---

### 3. The settings panel wiped your `.env` file — `settings.py`

**File:** `settings.py:36`
**Symptom:** Running `python settings.py` and changing any single option
deleted every other line in `.env` — including all three API keys.

**Cause:** The existence check was inverted, and the file was only read when it
did *not* exist.

```python
# before
if not os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
```

**Fix:** Read the file when it exists, start from an empty list when it does
not, and create the file if it is missing.

**Severity:** Critical — silent loss of API credentials.

---

## High

### 4. Memory never persisted to disk — `memory.py`

**File:** `memory.py:67`
**Symptom:** Conversation history worked within a single session but was lost
on every restart. The `TypeError` was caught and logged, so it looked like it
had saved.

**Cause:** `open()` was called with `self` as the file argument.

```python
# before
with open(self, self.storage_path, "w", encoding="utf-8") as f:

# after
with open(self.storage_path, "w", encoding="utf-8") as f:
```

### 5. Memory returned only one turn — `memory.py`

**File:** `memory.py:48`
**Cause:** `return messages` sat inside the `for` loop, so the function always
returned after the first turn. Moved the return outside the loop.

### 6. `get_context()` returned a bound method — `memory.py`

**File:** `memory.py:51`
**Cause:** `return self.get_messages` returned the method object instead of
calling it. Changed to `return self.get_messages()`.

---

## Medium

### 7. "Open app" always failed — `tools.py`

**File:** `tools.py` `_open_app()`
**Cause:** `name = name.strip` and `name = name.lower` assigned the *method
objects* instead of calling them. The subsequent `"." in name` raised
`TypeError: argument of type 'method' is not iterable`.

**Fix:** `name = name.strip()` and `name = name.lower()`, plus a guard for
`None` input.

### 8. Volume control always failed — `tools.py`

**File:** `tools.py` `_set_volume()`
**Cause:** Called `SetMasterVolumeLevelScaler`, which does not exist in pycaw.
The correct method is `SetMasterVolumeLevelScalar`. The resulting
`AttributeError` was not caught by the local `except ImportError`.

**Fix:** Corrected the method name and widened the `except` clause to catch
`AttributeError`, `OSError`, `TypeError` and `ValueError`.

### 9. `tell_joke` was implemented but never exposed — `tools.py`

**File:** `tools.py` `SKILL_TOOLS`
**Symptom:** The joke skill had a working implementation and a handler in
`execute_tool()`, but no entry in `SKILL_TOOLS` — so the LLM could never call
it. Only the keyword-matching path could.

**Fix:** Added the missing schema. `test_fixes.py` now asserts that every
schema has a handler and every handler is exposed.

### 10. Timers ignored the "hours" unit — `tools.py`

**File:** `tools.py` `_set_timer()`
**Cause:** Only `minutes` and `seconds` were handled; `hours` was silently
treated as seconds. A 1-hour timer fired after 1 second.

**Fix:** Added explicit `hours` handling, and the schema enum now includes
`hours`.

### 11. Document skill crashed during discovery — `document_creator_skill.py`

**File:** `document_creator_skill.py` `__init__`
**Symptom:** If the OpenAI client could not be constructed, the exception
escaped `__init__`, the registry logged it, and the skill was dropped from
discovery entirely.

**Fix:** Wrapped client creation in `try/except`, and check for `OpenAI is
None` when the package is not installed.

---

## Low

### 12. Spelling errors in user-facing strings

`"Weather data unavailabel."` → `"Weather data unavailable."` in `tools.py`,
and `"No audio backend availabel."` → `"No audio backend available."` in
`mic_manager.py`.

### 13. Broken TOC anchors in `API_SETUP.md`

Headings containing `(Wake Word)`, `+` and `—` produced anchor slugs that did
not match the table of contents. The headings were simplified so GitHub
generates predictable anchors.

### 14. `requirements.txt` had a duplicate `python-dotenv` entry

Two identical `python-dotenv>=1.0.1` lines. Deduplicated.

### 15. SimpleVAD compared a float against a dict — `simple_vad.py`

**File:** `simple_vad.py:28`
**Symptom:** Every single call to `is_speech()` raised
`TypeError: '>' not supported between instances of 'float' and 'dict'`. The
`except struct.error` clause did not catch it, so the exception propagated into
the recording loop.

**Cause:** The threshold was assigned the whole mapping instead of the value for
the requested aggressiveness level.

```python
# before
self.threshold = self.THRESHOLDS

# after
self.threshold = self.THRESHOLDS.get(aggressiveness, 700)
```

**Severity:** Critical on Python 3.12+ — `webrtcvad` has no wheels there, so
`simple_vad.py` is the only VAD, and it was completely broken. Recording would
crash on every command.

### 16. A failed audio device stopped Jarvis from starting — `speaker.py`

**File:** `speaker.py` `__init__`
**Symptom:** `pygame.mixer.init()` raises `pygame.error` when there is no
audio device, a missing PulseAudio server, or a device already in use. Only
`ImportError` was caught, so the exception escaped the constructor and
`main.py` died before the first wake word.

**Fix:** Catch any exception from the mixer init, log a warning, and continue
without playback. Jarvis still logs what it would have said.

### 17. A missing OpenAI client crashed skill discovery — `document_creator_skill.py`

**File:** `document_creator_skill.py` `__init__`
**Symptom:** If the OpenAI client could not be constructed, the skill raised
during instantiation. The registry caught it and silently dropped the skill.

**Fix:** Wrap client creation in `try/except` and check for `OpenAI is None`.

---

## Found while building the text chat mode

### 18. The microphone never recorded anything — `mic_manager.py`

**File:** `mic_manager.py` `record_command()`
**Symptom:** The wake word was detected, but every single command came back as
*"Sorry, I couldn't hear you."* The mic worked fine — the audio was thrown away.

**Cause:** Neither branch of the recording loop returned the captured frames.
The `sounddevice` branch had no `return` at all, and the `pyaudio` branch's
`return b"".join(frames)` sat **after** a `break`, making it unreachable
dead code. The function therefore fell off the end and returned `None`.

```python
# before
            else:
                ...
                        break
                        return b"".join(frames)   # unreachable

# after
            ...
            audio = b"".join(frames)
            if not audio:
                return self._record_fixed(5.0)
            return audio
```

**Severity:** Critical — the voice loop was completely non-functional.

### 19. `_record_fixed()` captured only the first chunk — `mic_manager.py`

**File:** `mic_manager.py` `_record_fixed()`
**Symptom:** The fallback recorder returned about 64 ms of audio instead of the
requested duration, so Whisper received a fragment.

**Cause:** The `return` was inside the `for` loop, so it returned after the
first iteration. Moved it after the loop.

### 20. No skill could ever match — `base.py`

**File:** `base.py` `__init__`
**Symptom:** Every skill reported zero triggers. "what time is it" fell
straight through to the LLM.

**Cause:** The base class assigned `self.keywords = []` in `__init__`. An
instance attribute shadows the class-level one, so the `keywords` list that
every subclass declares as a `ClassVar` was overwritten with an empty list.

```python
# before
def __init__(self) -> None:
    self.keywords: list[str] = []

# after
def __init__(self) -> None:
    # Only default the trigger list when the subclass genuinely has none.
    if not getattr(self, "keywords", None):
        self.keywords = []
```

**Severity:** Critical — the entire skill system was dead. Combined with bug
22, skills were doubly unreachable.

### 21. A nested tuple in the keyword list — `date_skill.py`

**File:** `date_skill.py` `keywords`
**Symptom:** `matches()` raised
`TypeError: 'in <string>' requires string as left operand, not tuple`.

**Cause:** One entry was written as `("today's date,", "current date")` — a
tuple inside the list. The neighbouring entry also had a stray leading space
(`" what is today"`), so it could never match either.

**Fix:** Flattened to plain strings, and `matches()` now skips any non-string
entry instead of raising.

### 22. The skills were never called from the voice loop — `main.py`

**File:** `main.py`
**Symptom:** `SkillRegistry` was imported nowhere in the running app. Only the
eight LLM function-calling tools were reachable, so the document reader and
document creator — the two skills with no tool schema — were unreachable in
practice.

**Fix:** Both `main.py` and the new `chat.py` now route through
`conversation.handle_command()`, which tries the skill registry first and
falls back to the LLM.

### 23. The document skills had no LLM tool schema — `tools.py`

**File:** `tools.py` `SKILL_TOOLS`
**Fix:** Added `read_document` and `create_document` schemas so the model can
reach the OCR and document-creation skills directly. That brings the tool
count to ten, all with handlers.

---

## Added in the no-signup rewrite

| Change | Why |
|---|---|
| `WAKE_ENGINE` with an openWakeWord backend | Picovoice asks for a corporate email. openWakeWord is fully local, needs no key, and ships a pretrained "hey jarvis" model. |
| `TTS_ENGINE` with an Edge TTS backend | Google Cloud requires a billing account even for the free tier. Edge TTS needs no key. |
| `OCR_ENGINE` with four backends | Same billing problem. OCR.space (no key), OpenRouter vision (free key), Tesseract (local), and Google Vision as an opt-in. |
| `requirements-google.txt` | Google packages are now opt-in instead of required. |
| `validate_required_keys()` warns instead of exiting | Only `OPENAI_API_KEY` is genuinely required. Every other service has a working fallback. |
| `__init__.py` sys.path bootstrap | Makes `python -m jarvis.main` work as well as `python main.py`. |
| `test_engines.py` | 19 tests covering engine selection, fallbacks and the VAD. |

---


## Not bugs — documented behaviour

| Behaviour | Why it is fine |
|---|---|
| `brain.py` catches the `tools` ImportError | Intentional fallback, but it is what made bug #1 invisible. The fallback now logs a warning instead of staying silent. |
| `webrtcvad` is not installed on Python 3.12+ | Expected. `simple_vad.py` is the pure-Python fallback and `mic_manager.py` picks the backend automatically. |
| `pycaw` is skipped on Python 3.14 | Expected. `pywin32` + `comtypes` cover Windows volume control instead. |
| Google Cloud requires a billing account for the free tier | Google policy, not a defect. The setup guide walks through it. |
