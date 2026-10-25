# API Setup Guide

Everything needed to get Jarvis running. Every service below has a **free tier that needs no credit card**, and the wake word and speech engines need **no account at all**.

**Time:** ~10 minutes
**Cost:** $0

---

## Table of Contents

- [The fast path](#the-fast-path-no-signup-no-credit-card)
- [What changed and why](#what-changed-and-why)
- [1. Groq — required](#1-groq-required)
- [2. Wake word — openWakeWord](#2-wake-word--openwakeword-no-signup)
- [3. Text to speech — Edge TTS](#3-text-to-speech--edge-tts-no-signup)
- [4. OCR — pick one](#4-ocr--pick-one)
- [Optional: Google Cloud](#optional-google-cloud)
- [Optional: Picovoice](#optional-picovoice)
- [Complete .env template](#complete-env-template)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)

---

## The fast path (no signup, no credit card)

If you want the shortest possible setup:

| # | Service | Account needed? | Credit card? |
|---|---|---|---|
| 1 | [Groq](https://console.groq.com/keys) — LLM + STT | Google/GitHub sign-in | No |
| 2 | [openWakeWord](https://github.com/dscripka/openWakeWord) — wake word | **None** | No |
| 3 | [Edge TTS](https://pypi.org/project/edge-tts/) — speech | **None** | No |
| 4 | [OCR.space](https://ocr.space/ocrapi) — OCR | **None** (public demo key) | No |

That is the whole setup. One signup, for Groq, which never asks for a card.

```bash
git clone https://github.com/TejasPatil0211/Jarvis.git
cd Jarvis
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # macOS / Linux

# openwakeword needs --no-deps on Python 3.12+ (tflite has no wheels there)
pip install --no-deps openwakeword
pip install onnxruntime
pip install -r requirements.txt

cp .env.keys .env              # then paste your Groq key in
python main.py
```

That is it. No Picovoice, no Google Cloud, no billing account.

---

## What changed and why

| Need | Was | Now | Why |
|---|---|---|---|
| Wake word | Picovoice Porcupine | **openWakeWord** | Picovoice signup asks for a corporate email. openWakeWord is fully local, needs no key, and ships a pretrained "hey jarvis" model. |
| Speech | Google Cloud TTS | **Edge TTS** | Google requires a billing account on the project even to use the free tier. Edge TTS needs no key and sounds like a real person. |
| OCR | Google Cloud Vision | **OCR.space / OpenRouter / Tesseract** | Same billing problem. Three alternatives, pick by how much accuracy you need. |
| LLM + STT | Groq | **Groq** (unchanged) | Already the best free option. |

Everything is pluggable. Set the engine you want in `.env` and nothing else changes.

---

## 1. Groq (required)

Groq powers both the LLM and speech recognition. It is the only account you need.

### Setup

1. Go to **https://console.groq.com/keys**
2. Sign up with Google or GitHub
3. Click **Create API Key**
4. Name it `jarvis` and confirm
5. Copy the key — it starts with `gsk_`

### Add to `.env`

```env
OPENAI_API_KEY=gsk_your_actual_key_here
OPENAI_BASE_URL=https://api.groq.com/openai/v1
OPENAI_MODEL=openai/gpt-oss-120b
GROQ_STT_MODEL=whisper-large-v3-turbo
```

### Verify

```bash
python -c "from openai import OpenAI; import os; from dotenv import load_dotenv; load_dotenv(); c=OpenAI(api_key=os.getenv('OPENAI_API_KEY'), base_url=os.getenv('OPENAI_BASE_URL')); r=c.chat.completions.create(model=os.getenv('OPENAI_MODEL'), messages=[{'role':'user','content':'Say OK'}]); print(r.choices[0].message.content)"
```

Expected: `OK`

### List the models on your account

```bash
python -c "from openai import OpenAI; import os; from dotenv import load_dotenv; load_dotenv(); c=OpenAI(api_key=os.getenv('OPENAI_API_KEY'), base_url=os.getenv('OPENAI_BASE_URL')); [print(m.id) for m in c.models.list().data]"
```

If `openai/gpt-oss-120b` is not listed, pick one that is and update `OPENAI_MODEL`.

### Model options

| Model | Speed | Quality | Best for |
|---|---|---|---|
| `openai/gpt-oss-120b` | Fast | Great | Default — smart and quick |
| `llama-3.3-70b-versatile` | Medium | Great | Complex reasoning |
| `llama-3.1-8b-instant` | Very fast | Good | Simple commands, quick chat |
| `mixtral-8x7b-32768` | Fast | Good | Balanced alternative |

### Free tier

- ~14,000 requests/day
- ~30 requests/minute
- No credit card required
- ~200ms response time

---

## 2. Wake word — openWakeWord (no signup)

### What it does

Listens for "hey jarvis" in the background. Runs entirely on your CPU with ONNX inference — no API calls, no latency, no cost, no account.

### Install

```bash
# Python 3.12+ — install without dependencies first
pip install --no-deps openwakeword
pip install onnxruntime
```

> **Why `--no-deps`?** openWakeWord declares `tflite-runtime` as a dependency, and tflite has no wheels for Python 3.12 or newer. Installing without dependencies and adding `onnxruntime` yourself avoids a failed resolve. openWakeWord falls back to ONNX automatically when tflite is absent.

On Python 3.11 and older you can just run `pip install openwakeword`.

### Download the model (one time)

The models are not bundled with the wheel. They are fetched once and cached forever:

```bash
python -c "import openwakeword; openwakeword.utils.download_models()"
```

Or let Jarvis do it on first launch — it handles the download automatically.

### Configure

```env
WAKE_ENGINE=openwakeword
WAKEWORD_MODEL=hey_jarvis
WAKEWORD_THRESHOLD=0.5
```

`hey_jarvis` is the default and works out of the box. Other bundled models: `alexa`, `hey_mycroft`, `hey_rhasspy`, plus phrase models for `timers` and `weather`.

### Tuning

`WAKEWORD_THRESHOLD` controls sensitivity:

| Value | Behaviour |
|---|---|
| 0.3 | Triggers more easily, more false positives |
| 0.5 | Default, balanced |
| 0.7 | Fewer false positives, may miss you sometimes |

If Jarvis triggers when you are not talking to it, raise it to 0.6 or 0.7.

### Free tier

There is no account, no key, and no limit. The code is Apache-2.0. The bundled models are CC BY-NC-SA 4.0, which covers personal and non-commercial use.

---

## 3. Text to speech — Edge TTS (no signup)

### What it does

Converts Jarvis's reply into natural speech using the same neural voices Microsoft Edge uses. No account, no API key, no billing. It does need an internet connection.

### Install

```bash
pip install edge-tts
```

### Configure

```env
TTS_ENGINE=edge
TTS_VOICE_EDGE=en-US-GuyNeural
```

### Voice options

| Voice | Gender | Notes |
|---|---|---|
| `en-US-GuyNeural` | Male | Default — closest to the old Neural2-J voice |
| `en-US-AriaNeural` | Female | Warm and natural |
| `en-US-JennyNeural` | Female | Crisp, good for short replies |
| `en-GB-SoniaNeural` | Female | British accent |
| `en-IN-RaveenaNeural` | Female | Indian English accent |

To hear them all:

```bash
edge-tts --list-voices
```

### If Edge TTS is blocked

Some networks block the Edge endpoint. Fall back to the Windows built-in voice — fully offline, no account, robotic but functional:

```env
TTS_ENGINE=sapi
```

On Linux and macOS, install `espeak` and Jarvis will use that instead.

---

## 4. OCR — pick one

OCR has the most options because handwriting accuracy varies a lot between them.

### Option A — OCR.space (no signup, free, good on handwriting)

25,000 requests per month, no credit card, and Engine 3 handles handwriting well.

```bash
pip install requests
```

```env
OCR_ENGINE=ocrspace
```

With no key set, Jarvis uses OCR.space's public demo key. For real use, get a free key at **https://ocr.space/ocrapi** and set:

```env
OCRSPACE_API_KEY=your_free_key
```

### Option B — OpenRouter vision (best on handwriting, free models)

A free vision model reads the image and transcribes it. It uses the same OpenAI SDK you already have for Groq.

1. Go to **https://openrouter.ai/keys**
2. Sign in with Google
3. Create a key
4. Set it in `.env`:

```env
OCR_ENGINE=openrouter
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_VISION_MODEL=google/gemini-2.0-flash-exp:free
```

The `:free` suffix means the model is free. Other free options: `qwen/qwen2.5-vl-7b-instruct:free`, `google/gemini-2.5-flash-lite:free`.

### Option C — Tesseract (fully local, free, weak on handwriting)

Good for printed text, receipts, and scanned PDFs. No account, no internet.

```bash
pip install pytesseract
```

You also need the Tesseract binary:

- **Windows:** download the installer from **https://github.com/UB-Mannheim/tesseract/wiki**
- **Debian/Ubuntu:** `sudo apt install tesseract-ocr`
- **macOS:** `brew install tesseract`

```env
OCR_ENGINE=tesseract
```

If Tesseract is not on your PATH, set `TESSERACT_CMD` in `.env` to the full path of `tesseract.exe`.

### What to expect from each

| Engine | Printed text | Handwriting | Setup |
|---|---|---|---|
| OCR.space | Very good | Good | None |
| OpenRouter vision | Excellent | Excellent | Free key |
| Tesseract | Good | Poor | Binary install |
| Google Vision | Excellent | Very good | Billing account |

### How to use it

1. Drop an image into `scans/`
2. Say *"jarvis, read the document"*
3. Jarvis transcribes it, saves a `.txt` next to the image, and reads a summary back

---

## Optional: Google Cloud

Only if you want Google's specific TTS voices or Vision OCR quality. It requires a billing account on the project, even to stay within the free tier.

1. Create a project at **https://console.cloud.google.com/**
2. Link a billing account at **https://console.cloud.google.com/billing**
3. Enable **Cloud Text-to-Speech API** and **Cloud Vision API** at **https://console.cloud.google.com/apis/library**
4. Create a service account with the **Cloud TTS User** and **Cloud Vision User** roles
5. Create a JSON key and save it as `gcp-credentials.json` in the project folder
6. Install the extra packages:

```bash
pip install -r requirements-google.txt
```

7. Configure:

```env
TTS_ENGINE=google
GOOGLE_APPLICATION_CREDENTIALS=./gcp-credentials.json
OCR_ENGINE=google
```

---

## Optional: Picovoice

Only if you already have an AccessKey. Their signup asks for a corporate email, which is why openWakeWord is the default.

```bash
pip install pvporcupine
```

```env
WAKE_ENGINE=porcupine
PORCUPINE_ACCESS_KEY=your_access_key
```

With a key set and `WAKE_ENGINE=auto`, Jarvis uses Porcupine automatically.

---

## Complete `.env` template

```env
# ─── LLM + speech to text (REQUIRED) ───────────────────────────────────
# Free key: https://console.groq.com/keys  — no credit card
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.groq.com/openai/v1
OPENAI_MODEL=openai/gpt-oss-120b
GROQ_STT_MODEL=whisper-large-v3-turbo

# ─── Wake word ──────────────────────────────────────────────────────────
# auto | openwakeword | porcupine
WAKE_ENGINE=auto
WAKEWORD_MODEL=hey_jarvis
WAKEWORD_THRESHOLD=0.5
# PORCUPINE_ACCESS_KEY=
# PORCUPINE_KEYWORD_PATH=./jarvis_wake.ppn

# ─── Text to speech ─────────────────────────────────────────────────────
# auto | edge | google | sapi
TTS_ENGINE=auto
TTS_VOICE_EDGE=en-US-GuyNeural
# GOOGLE_APPLICATION_CREDENTIALS=./gcp-credentials.json
# TTS_VOICE_NAME=en-US-Standard-A

# ─── OCR ────────────────────────────────────────────────────────────────
# auto | openrouter | ocrspace | tesseract | google
OCR_ENGINE=auto
# OPENROUTER_API_KEY=
# OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
# OPENROUTER_VISION_MODEL=google/gemini-2.0-flash-exp:free
# OCRSPACE_API_KEY=

# ─── Feature flags ──────────────────────────────────────────────────────
MEMORY_ENABLED=True
MEMORY_MAX_TURNS=10
DOCS_OUTPUT_DIR=./documents
OCR_TEMP_DIR=./scans
SCREENSHOTS_DIR=./screenshots
```

---

## Verification

```bash
python test_compat.py     # dependencies and .env
python test_smoke.py      # imports, tools, skills, memory
python test_engines.py    # engine selection
python test_fixes.py      # regression tests
```

`test_compat.py` prints which engine each subsystem will use:

```
--- API configuration ---
  required:
    [OK]   OPENAI_API_KEY               Groq LLM + STT (gsk_ab12...)

  optional (each has a free fallback):
    [WARN] PORCUPINE_ACCESS_KEY         not set — openWakeWord used if unset
    [WARN] GOOGLE_APPLICATION_CREDENTIALS not set — Edge TTS used if unset

  engine selection:
    WAKE_ENGINE                        openwakeword
    TTS_ENGINE                         edge
    OCR_ENGINE                         ocrspace
```

---

## Troubleshooting

### "PORCUPINE_ACCESS_KEY not set"

That is a warning, not an error. openWakeWord is being used instead. If you want to force Porcupine, set `WAKE_ENGINE=porcupine` and add the key.

### openWakeWord will not install

```
error: Could not find a version that satisfies the requirement tflite-runtime
```

Expected on Python 3.12+. Use:

```bash
pip install --no-deps openwakeword
pip install onnxruntime
```

### openWakeWord triggers on background noise

Raise the threshold:

```env
WAKEWORD_THRESHOLD=0.7
```

### openWakeWord never triggers

- Lower the threshold to 0.3
- Check the model downloaded: `python -c "import openwakeword; openwakeword.utils.download_models()"`
- Speak clearly — the model expects "hey jarvis", not just "jarvis"

### Edge TTS returns no audio

- Check internet connectivity
- Try `TTS_ENGINE=sapi` for the offline Windows voice
- Try a different voice from `edge-tts --list-voices`

### OCR returns empty text

- Check the image is not too dark or too blurry
- Try `OCR_ENGINE=openrouter` — it is the most forgiving on handwriting
- For Tesseract, make sure the Tesseract binary is installed and on PATH

### "No audio device" or playback fails

pygame could not open an audio device. Jarvis still works and logs what it would have said. Check your default output device in the OS sound settings.

### `429` from Groq

You hit 30 requests/minute or the daily cap. Wait a few seconds — Jarvis retries automatically.

---

## Quick links

| Resource | URL |
|---|---|
| Groq Console | https://console.groq.com/keys |
| openWakeWord | https://github.com/dscripka/openWakeWord |
| openWakeWord models | https://openwakeword.com/ |
| edge-tts | https://pypi.org/project/edge-tts/ |
| Edge voice list | `edge-tts --list-voices` |
| OCR.space | https://ocr.space/ocrapi |
| OpenRouter | https://openrouter.ai/keys |
| Tesseract (Windows) | https://github.com/UB-Mannheim/tesseract/wiki |
| Picovoice (optional) | https://console.picovoice.ai/ |
| Google Cloud (optional) | https://console.cloud.google.com/ |

---

Setup complete. Run `python main.py` and say "hey jarvis".
