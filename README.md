# Jarvis

A personal voice assistant in Python. Wake word → listen → think → act → speak.
Runs on low-end hardware, powered by free cloud APIs, with a modular skill system and function calling.

> Say **"jarvis"** and it listens.

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Setup](#setup)
- [Usage](#usage)
- [Settings](#settings)
- [Adding a Skill](#adding-a-skill)
- [Performance](#performance)
- [Cost](#cost)
- [Troubleshooting](#troubleshooting)
- [Bug Fixes](#bug-fixes)
- [License](#license)

---

## Features

### Core Voice Loop

| Stage | Engine | Account needed? | Runs On |
|---|---|---|---|
| Wake word | openWakeWord ("hey jarvis") | **None** | Local |
| Recording + VAD | PyAudio / sounddevice | None | Local |
| Speech-to-text | Groq Whisper | Free key | Cloud |
| Reasoning | Groq (`openai/gpt-oss-120b`) | Free key | Cloud |
| Text-to-speech | Edge TTS | **None** | Cloud |
| OCR | OCR.space / OpenRouter / Tesseract | **None** | Cloud or local |

Only one account is required: Groq. No credit card anywhere, no corporate email,
no Google Cloud billing account. Everything CPU-heavy is in the cloud, so the
local footprint stays under 250 MB RAM.

Every engine is swappable. Set `WAKE_ENGINE`, `TTS_ENGINE` or `OCR_ENGINE` in
`.env` and pick from the alternatives — including Picovoice Porcupine and
Google Cloud TTS if you ever want them.

### Skills

Skills live as plain `.py` files in the project root. `registry.py` auto-discovers them at startup — no registration needed.

| Skill | Trigger | What it does |
|---|---|---|
| Time | "what time is it" | Current time |
| Date | "what's today's date" | Current date and weekday |
| Joke | "tell me a joke" | Random joke |
| Weather | "what's the weather" | Live weather via wttr.in |
| Timer | "set a timer for 5 minutes" | Countdown with a spoken alert |
| Document Reader | "read this document" | OCR for handwritten notes (Google Vision) |
| Document Creator | "create a document about X" | Generates a `.docx` file |

### Function Calling (Layer 4)

Seven tools are exposed to the LLM as OpenAI-style function schemas. The model picks the right one on its own.

| Tool | Example request |
|---|---|
| `get_current_time` | "what time is it" |
| `get_weather` | "weather in Tokyo" |
| `tell_joke` | "tell me a joke" |
| `set_timer` | "remind me in 10 minutes" |
| `web_search` | "search for the latest Python release" |
| `open_application` | "open Chrome" |
| `set_volume` | "set volume to 30" |
| `take_screenshot` | "take a screenshot" |

Web search uses DuckDuckGo — no API key required.

### Memory and Settings

- Toggleable conversation memory (last N turns, persisted to `jarvis_memory.json`)
- CLI settings panel for memory, paths, and feature flags
- Clean logging to both console and `jarvis.log`

---

## Architecture

```text
┌─────────────────────────────────────────────────────┐
│                Jarvis (local Python)                │
│                                                     │
│   openWakeWord ─► wake word detection (local)      │
│   mic_manager ──► record + VAD (shared mic handle)  │
│   registry ─────► skill auto-discovery              │
│   memory ───────► conversation history (JSON)       │
│   tools ────────► function-calling router           │
│   settings ─────► CLI config panel                  │
└─────────────────────────────────────────────────────┘
          │                │                │
     ┌────▼─────┐    ┌─────▼─────┐    ┌─────▼──────┐
     │   Groq   │    │   Groq    │    │  Edge TTS │
     │ Whisper  │    │  gpt-oss  │    │  (no key) │
     │  (STT)   │    │  (LLM)    │    │           │
     └──────────┘    └───────────┘    └────────────┘
        audio          reply              speech
```

**The loop:**

1. `mic_manager.wait_for_wake_word()` blocks until openWakeWord hears "hey jarvis"
2. `record_command()` captures audio and stops on silence (VAD)
3. `listener.transcribe()` sends audio to Groq Whisper
4. `brain.process()` sends the text to the LLM along with memory and tool schemas
5. If the model returns tool calls, `tools.execute_tool()` runs them and the result feeds back
6. `speaker.speak()` renders the reply through Edge TTS

---

## Project Structure

```text
jarvis/
├── main.py                     # Entry point — voice loop
├── chat.py                     # Text mode — talk to Jarvis with no mic
├── conversation.py             # Shared routing (skill first, then LLM)
├── config.py                   # Env vars, constants, key validation
│
├── mic_manager.py              # Shared audio handle, wake word, VAD recording
├── wake_word.py                # Wake word (openWakeWord / Porcupine)
├── listener.py                 # Speech-to-text via Groq Whisper
├── brain.py                    # LLM calls, memory, function-calling loop
├── speaker.py                  # Text-to-speech (Edge / Google / SAPI)
│
├── registry.py                 # Skill auto-discovery and dispatch
├── base.py                     # Skill base class
├── time_skill.py               # Time
├── date_skill.py               # Date
├── joke_skill.py               # Jokes
├── weather_skill.py            # Weather via wttr.in
├── timer_skill.py              # Timers
├── document_reader_skill.py    # OCR (OCR.space / OpenRouter / Tesseract)
├── document_creator_skill.py   # .docx generation
│
├── tools.py                    # Function schemas + tool implementations
├── memory.py                   # Conversation memory
├── settings.py                 # CLI settings panel
├── retry_helper.py             # Retry with exponential backoff
├── simple_vad.py               # Pure-Python VAD (webrtcvad fallback)
│
├── test_compat.py              # Dependency checker
├── test_smoke.py               # Import and startup smoke test
├── test_chat.py                # Chat mode, recording and device tests
├── test_engines.py             # Engine selection tests
├── test_fixes.py               # Regression tests for fixed bugs
│
├── requirements.txt            # Core dependencies (no signup needed)
├── requirements-google.txt     # Optional Google Cloud add-ons
├── .env.keys                   # Template — copy to .env and fill in
├── .gitignore
├── README.md
├── API_SETUP.md                # Detailed API key walkthrough
└── LICENSE                     # MIT
```

Runtime output directories (`documents/`, `scans/`, `screenshots/`) are created on demand.

---

## Setup

### Prerequisites

- **Python 3.10 or newer** (3.12, 3.13, and 3.14 supported)
- Microphone and speakers
- Internet connection — STT, LLM, TTS, and OCR are all cloud services

### Install

```bash
git clone https://github.com/TejasPatil0211/Jarvis.git
cd Jarvis

python -m venv venv
```

Activate it:

```bash
# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

Then install dependencies:

```bash
pip install -r requirements.txt
```

That is one command on Windows and macOS. `requirements.txt` uses environment
markers, so pip picks the right build for your platform automatically:

| Package | Python 3.11–3.13 | Python 3.14+ |
|---|---|---|
| Microphone | `pyaudio` | `sounddevice` |
| VAD | `webrtcvad` | `simple_vad.py` (bundled) |
| Inference | `onnxruntime>=1.16` | `onnxruntime>=1.24` (cp314 wheels) |

> **Linux + Python 3.12+ only:** `tflite-runtime` has no wheels past cp311 and
> openWakeWord pulls it in on Linux, so the resolve fails. Use the two-step
> install instead:
> ```bash
> pip install onnxruntime scipy scikit-learn tqdm requests
> pip install --no-deps openwakeword
> ```

`requirements.txt` uses environment markers, so pip picks the right audio backend for your Python version automatically:

- Python **< 3.14** → `pyaudio`
- Python **>= 3.14** → `sounddevice` (no C compilation needed)
- Python **< 3.12** → `webrtcvad`
- Python **>= 3.12** → `simple_vad.py` (bundled, pure Python)

Verify the install:

```bash
python test_compat.py
```

### Configure

```bash
cp .env.keys .env
```

Edit `.env` and paste in your Groq key. **That is the only account you need** —
the wake word, the speech engine, and OCR all work without a signup or a
credit card.

Full walkthrough is in **[API_SETUP.md](API_SETUP.md)**.

```env
# LLM and STT — https://console.groq.com/keys (free, no credit card)
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.groq.com/openai/v1
OPENAI_MODEL=openai/gpt-oss-120b
GROQ_STT_MODEL=whisper-large-v3-turbo

# Wake word — no account needed
WAKE_ENGINE=openwakeword
WAKEWORD_MODEL=hey_jarvis
WAKEWORD_THRESHOLD=0.5

# Text to speech — no account needed
TTS_ENGINE=edge
TTS_VOICE_EDGE=en-US-GuyNeural

# OCR — no account needed (public demo key)
OCR_ENGINE=ocrspace
```

### Optional: swap in other engines

Every engine is selectable from `.env`:

| Variable | Options |
|---|---|
| `WAKE_ENGINE` | `openwakeword` (no key), `porcupine` (needs AccessKey) |
| `TTS_ENGINE` | `edge` (no key), `google` (needs billing), `sapi` (offline) |
| `OCR_ENGINE` | `ocrspace` (no key), `openrouter` (free key), `tesseract` (local), `google` (needs billing) |

`auto` picks the best option that needs the least setup.

### Run

```bash
python main.py
```

Jarvis logs `Jarvis is ready. Say 'Jarvis' to activate.` and waits for the wake word.

Running as a package also works, if you prefer:

```bash
cd ..          # one level above the project folder
python -m jarvis.main
```

### Verify the install

```bash
python test_compat.py     # dependency and API key check
python test_smoke.py      # imports, tool registration, skills, memory
python test_fixes.py      # regression tests for the 14 fixed bugs
```

`test_smoke.py --online` additionally makes one live LLM call to confirm your key works.

---

## Usage

```text
You:    "jarvis, what's the capital of Japan"
Jarvis: "Tokyo."

You:    "jarvis, what time is it"
Jarvis: "It's 3:42 PM."

You:    "jarvis, what's the weather in Tokyo"
Jarvis: "Weather in Tokyo: partly cloudy, 22C."

You:    "jarvis, search for the latest Python release"
Jarvis: "Here's what I found: Python 3.14 was released in October 2025..."

You:    "jarvis, open Chrome"
Jarvis: "Opening chrome."

You:    "jarvis, set volume to 30"
Jarvis: "Volume set to 30%."

You:    "jarvis, take a screenshot"
Jarvis: "Screenshot saved."

You:    "jarvis, create a document about my project notes"
Jarvis: "Done. Saved 'Project Notes' to the documents folder."

You:    "jarvis, what's my name"
Jarvis: "You told me your name was earlier."      # only with memory enabled
```

### Text mode — no microphone needed

If the mic is not cooperating, or you just want to type:

```bash
python chat.py                # talk to Jarvis in the terminal
python chat.py --no-voice     # print replies only
python chat.py --no-memory    # start with a clean slate
```

```
You> what time is it
Jarvis> It's 10:45 AM.

You> tell me a joke
Jarvis> What do you call a bear with no teeth? A gummy bear.

You> who won the world cup in 1998
Jarvis> France beat Brazil 3-0 in the final.

You> /skills
  Skills:
    - date
    - document_creator
    ...

You> /memory        # show the conversation history
You> /clear        # wipe it
You> /voice off    # stop speaking replies
You> /quit
```

Same brain, same skills, same function calling, same memory. The only thing
missing is the microphone.

### Choosing a microphone

If Jarvis hears you but the wrong device is being used — common with
headsets — point it at the right one:

```bash
python mic_manager.py --list-devices    # show every input device
python mic_manager.py --test-mic        # record 3 seconds and report
```

Then set the device in `.env`:

```env
MIC_DEVICE=2            # by index
MIC_DEVICE=headset      # or by name fragment
```

### OCR workflow

1. Drop a photo of your handwritten notes into `scans/`
2. Say *"jarvis, read the document"*
3. The image is transcribed by the configured OCR engine, the text is saved next to the image as a `.txt`, and Jarvis reads back a summary

---

## Settings

```bash
python settings.py
```

```text
+--------------------------------------+
|         JARVIS SETTINGS PANEL        |
+--------------------------------------+
|  1. Toggle conversation memory       |
|  2. Set memory max turns             |
|  3. View current memory              |
|  4. Clear memory                     |
|  5. Set documents output directory   |
|  6. Set scans/OCR directory          |
|  7. Show current settings            |
|  0. Exit                             |
+--------------------------------------+
```

Changes are written to `.env`. Restart Jarvis to apply them.

---

## Adding a Skill

Drop a new file in the project root. `registry.py` picks it up automatically at startup.

The filename **must end with `_skill.py`** — `registry.py` only scans files matching that pattern, so that `main.py`, `settings.py` and the test files are never imported as skills.

```python
# my_cool_skill.py
from typing import ClassVar

try:  # package context: `python -m jarvis.main`
    from .base import Skill
except ImportError:  # script context: `python main.py`
    from base import Skill


class MyCoolSkill(Skill):
    name = "my_cool"

    def __init__(self):
        self.keywords: ClassVar[list[str]] = ["trigger phrase", "another phrase"]

    def handle(self, user_input: str) -> str:
        return "Short spoken response — keep it under two sentences."
```

Restart Jarvis. That's it.

To make the skill callable through the LLM instead of keyword matching, add a schema to `SKILL_TOOLS` in `tools.py` and a handler in `execute_tool()`. Every schema must have a matching handler — `test_fixes.py` checks for orphaned schemas.

---

## Performance

| Component | RAM |
|---|---|
| Python runtime and libraries | ~180 MB |
| openWakeWord model (ONNX) | ~20 MB |
| Audio buffers | ~20 MB |
| **Jarvis overhead** | **~230 MB** |
| OS plus Jarvis | ~600 MB (minimal Linux) |

STT, LLM, TTS, and OCR all run remotely, so they add nothing to local memory.

**Runtime for a typical command:** 0.8 – 2.0 s (wake word detection is instant and local).

---

## Cost

| Service | Account | Free tier | Cost |
|---|---|---|---|
| Groq (LLM + STT) | Google sign-in | ~14,000 requests/day | $0 |
| openWakeWord (wake word) | **none** | Unlimited | $0 |
| Edge TTS (speech) | **none** | Unlimited | $0 |
| OCR.space (OCR) | **none** | 25,000 requests/month | $0 |
| wttr.in (weather) | none | Unlimited | $0 |
| DuckDuckGo (search) | none | Unlimited | $0 |
| **Total** | | | **$0** |

One free account, no credit card, no corporate email. If you ever want the
Google Cloud or Picovoice options, those are free tiers too — they just need
a billing account and an AccessKey respectively.

A typical response is ~80 characters, so the free TTS tier covers roughly 50,000 responses per month.

---

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `ModuleNotFoundError: No module named 'google'` | Run `pip install -r requirements.txt` |
| `ModuleNotFoundError: No module named 'distutils.msvccompiler'` | Use Python 3.11, or install MSVC Build Tools |
| `ImportError: cannot import name 'SCREENSHOTS_DIR'` | Stale `config.py` — pull the latest, or check for a typo in the variable name |
| Wake word never triggers | Check the default input device, then verify with `python -c "import pyaudio; p=pyaudio.PyAudio(); print(p.get_device_count())"` |
| "Device unavailable" error | Another app holds the mic — close Discord, Zoom, or the browser |
| `429 RESOURCE_EXHAUSTED` from Groq | Rate limit — retries happen automatically, wait a few seconds |
| Google TTS 401 or 403 | Service account is missing the TTS or Vision role |
| `DefaultCredentialsError` | `GOOGLE_APPLICATION_CREDENTIALS` points at a file that isn't there |
| Jarvis forgets previous turns | Memory may be off — check `python settings.py` |
| Skill never triggers | The `keywords` list must match what you actually say |
| No text transcribed | Check `jarvis.log` — you should see `Recording command...` then `Transcribed: ...` |

---

## Bug Fixes

Fourteen defects were found by reading the code and reproducing each one with a failing test. The full write-up is in [BUGS_FOUND.md](BUGS_FOUND.md).

The three that mattered most:

| Bug | Impact |
|---|---|
| `config.py` variable typo | Silently disabled **every** Layer 4 tool — web search, volume, screenshots, timers |
| `registry.py` import mismatch | **No skill loaded at all** — time, date, joke, weather, timer, documents |
| `settings.py` inverted check | The settings panel **wiped your `.env`**, deleting all API keys |

Plus four memory bugs (history never persisted, only one turn returned), two broken tool implementations (`open_application`, `set_volume`), a `tell_joke` tool that existed but was never exposed to the LLM, and timers that ignored the "hours" unit.

`test_fixes.py` covers all of them:

```bash
python test_fixes.py
# RESULT: 14/14 passed — all bugs fixed
```

---

## License

MIT. See [LICENSE](LICENSE).

---

## Credits

- [openWakeWord](https://github.com/dscripka/openWakeWord) — local wake word engine
- [Groq](https://groq.com/) — LLM and Whisper inference
- [edge-tts](https://github.com/rany2/edge-tts) — speech synthesis
- [OCR.space](https://ocr.space/) — OCR
- [Picovoice](https://picovoice.ai/) — Porcupine, optional wake word engine
- [Google Cloud](https://cloud.google.com/) — optional TTS and Vision OCR
- [wttr.in](https://wttr.in/) — Weather data
- [DuckDuckGo](https://duckduckgo.com/) — Web search
- The Python community
