# Jarvis 🎙️

A personal voice assistant built in Python.                 
Runs on low-end hardware,                 
powered by free cloud APIs,                 
with a modular skill system and function calling.

Say "jarvis" → it listens → it thinks → it acts → it answers.

# ✨ Features:

Core Voice Loop

🎙️ Wake word detection — Porcupine listens locally for "jarvis" (or a custom .ppn file)

👂 Speech recognition — Groq Whisper (fast, free, generous limits)

🧠 LLM brain — Groq openai/gpt-oss-120b with function calling

🔊 Text-to-speech — Google Cloud TTS with local espeak fallback

🔇 Voice activity detection — stops recording when you stop talking

# Skills

Modular,                 
auto-discovered skills in skills/.                
Add one file, restart, done.

Skill	                 Trigger	                Does

Time	                 "what time is it"	        Current time

Date	                 "what's today's date"	        Current date + day

Joke	                 "tell me a joke"	        Random joke

Weather	                 "what's the weather"	        Live weather via wttr.in

Timer	                 "set a timer for 5 minutes"	Countdown + spoken alert

Document Reader	          "read this document"	        OCR for handwritten notes (Google Vision)

Document Creator	  "create a document about X"	Generates a .docx file

# System Control (Layer 4)

🌐 Web search — DuckDuckGo, no API key needed

🚀 Open apps — "open Chrome", "open github.com"

🔊 Set volume — "set volume to 30"

📸 Screenshots — "take a screenshot"

# Memory & Config

💬 Toggleable conversation memory — remembers your last 10 turns

⚙️ CLI settings panel — python settings.py to toggle memory, change paths

📄 Document handling — read handwritten notes, create Word documents

🧩 Function calling — the LLM auto-picks the right skill for ambiguous requests

🏗️ Architecture

text


┌──────────────────────────────────────────────────────┐
│                 Jarvis (local Python)                 │
│                                                      │
│  Porcupine ──→ wake word (LOCAL, ~30MB)              │
│  mic_manager ──→ record + VAD (LOCAL)                │
│  skills/ ──→ time, weather, timer, docs (LOCAL)      │
│  memory.py ──→ conversation history (LOCAL JSON)     │
│  settings.py ──→ config panel (LOCAL)                │
│  tools.py ──→ function calling router (LOCAL)        │
└──────────────────────────────────────────────────────┘
        ↓              ↓                ↓
    ┌────────┐    ┌──────────┐    ┌────────────┐
    │  Groq  │    │   Groq   │    │   Google   │
    │Whisper │    │gpt-oss   │    │ Cloud TTS  │
    │ (STT)  │    │  (LLM)   │    │  (+Vision) │
    └────────┘    └──────────┘    └────────────┘
    "yo jarvis"   "what time?"     "it's 3:42 pm"
      → text       → response        → audio
Everything CPU-heavy runs in the cloud. Local footprint stays under ~400MB RAM.

📁 Project Structure


jarvis/

├── main.py                       # Entry point — runs the main loop                

├── config.py                     # Env vars, constants, key validation

├── mic_manager.py                # Shared PyAudio resource, VAD recording

├── wake_word.py                  # Porcupine wake word listener

├── listener.py                   # STT via Groq Whisper (25MB guard)

├── brain.py                      # LLM via Groq + function calling

├── speaker.py                    # TTS via Google Cloud + espeak fallback

├── tools.py                      # Function calling schemas + executor

├── memory.py                     # Toggleable conversation memory

├── settings.py                   # CLI settings panel

├── retry_helper.py               # Retry with exponential backoff

├── simple_vad.py                 # Pure-Python VAD (webrtcvad alternative)

│

├── skills/                       # Auto-discovered skill system

│   ├── __init__.py

│   ├── base.py                   # Skill base class

│   ├── registry.py               # Auto-discovery + dispatch

│   ├── time_skill.py

│   ├── date_skill.py

│   ├── joke_skill.py

│   ├── weather_skill.py

│   ├── timer_skill.py

│   ├── document_reader_skill.py  # OCR via Google Vision

│   └── document_creator_skill.py # .docx generation

│

├── tests/                        # Pytest suites

│   ├── test_skills.py

│   └── test_layer4.py

│

├── documents/                    # Generated docs land here

├── scans/                        # Drop handwritten images here for OCR

├── screenshots/                  # Captured screenshots land here

│

├── .env                          # API keys (gitignored)

├── .env.example                  # Template

├── requirements.txt              # Pinned deps

├── README.md                     # This file

├── CHANGELOG.md                  # Version history

├── LICENSE                       # MIT

└── BUGS_FOUND.md                 # Known issues (if any)


🚀 Setup
1. Prerequisites
Python 3.10+ (tested on 3.12, 3.13, 3.14)                
A microphone and speakers                
Internet connection (STT, LLM, TTS all cloud-based)                

2. Install

bash                
git clone https://github.com/TejasPatil0211/Jarvis.git
cd Jarvis
Create virtual environment

python -m venv venv

Activate it

1. Windows:

venv\Scripts\activate

2. macOS/Linux:

source venv/bin/activate

Install dependencies

pip install -r requirements.txt

Windows note: If pyaudio fails to install, you need PortAudio:

 Download from https://www.portaudio.com/ downloads/archives/ 
 OR use the sounddevice fallback (see API_SETUP_GUIDE.md)


Verify everything installed:

bash


python test_compat.py
3. Configure API keys
bash


cp .env.example .env
Then edit .env with your keys. See API_SETUP_GUIDE.md for detailed walkthrough.

env


# Wake word
PORCUPINE_ACCESS_KEY=your_picovoice_key
# LLM + STT (Groq)
OPENAI_API_KEY=gsk_your_groq_key
OPENAI_BASE_URL=https://api.groq.com/openai/v1
OPENAI_MODEL=openai/gpt-oss-120b
GROQ_STT_MODEL=whisper-large-v3-turbo
# TTS + OCR (Google Cloud)
GOOGLE_APPLICATION_CREDENTIALS=./gcp-credentials.json
4. Run
bash


python main.py
Say "jarvis" to wake it, then speak your command.

🎯 Usage Examples
bash


# Simple Q&A
You:    "jarvis, what's the capital of Japan"
Jarvis: "Tokyo."
# Skills (auto-selected via function calling)
You:    "jarvis, what time is it"
Jarvis: "It's 3:42 PM."
# Live data
You:    "jarvis, what's the weather in Tokyo"
Jarvis: "Weather in Tokyo: partly cloudy, 22°C."
# Web search
You:    "jarvis, search for the latest Python releases"
Jarvis: "Here's what I found: Python 3.14 released October 2025..."
# System control
You:    "jarvis, open Chrome"
You:    "jarvis, set volume to 30"
You:    "jarvis, take a screenshot"
# Documents
You:    "jarvis, create a document about my project notes"
Jarvis: "Done. Created 'Project Notes' in your documents folder."
# Memory
You:    "jarvis, what's my name"
Jarvis: "You told me your name was earlier..."  ← if memory is on
⚙️ Settings
bash


python settings.py
text


╔══════════════════════════════════════╗
║         JARVIS SETTINGS PANEL        ║
╠══════════════════════════════════════╣
║  1. Toggle conversation memory       ║
║  2. Set memory max turns             ║
║  3. View current memory              ║
║  4. Clear memory                     ║
║  5. Set documents output directory   ║
║  6. Set scans/OCR directory          ║
║  7. Show current settings            ║
║  0. Exit                             ║
╚══════════════════════════════════════╝
Changes persist to .env. Restart Jarvis to apply.

🛠️ Adding a Skill
Drop a new file in skills/:

python


# skills/my_skill.py
from .base import Skill
class MySkill(Skill):
    name = "my_skill"
    keywords = ["trigger phrase", "another phrase"]
    def handle(self, user_input: str) -> str:
        return "Response spoken by Jarvis (keep under 2 sentences)"
Restart Jarvis — auto-discovery picks it up.

For function calling support, also add a schema to tools.py → SKILL_TOOLS and a handler in execute_tool().

💾 Memory Budget
Component	RAM
Python runtime + all libs	~180 MB
Porcupine wake word	~30 MB
Audio buffers	~20 MB
Memory + skills data	< 10 MB
Total Jarvis overhead	~240 MB
OS + Jarvis	~600 MB (on minimal Linux)
Heavy compute (STT, LLM, TTS, OCR) all happen in the cloud → 0 MB local.

💰 Cost
Service	Free Tier	Typical Monthly Use
Groq (LLM + STT)	~14,000 req/day	$0
Porcupine (wake word)	Unlimited (personal)	$0
Google Cloud TTS	4M characters/mo	$0
Google Cloud Vision	1,000 images/mo	$0
wttr.in (weather)	Unlimited	$0
DuckDuckGo (search)	Unlimited	$0
Total		$0
Realistic daily use (~100 commands) stays well within every free tier.

🐛 Troubleshooting
Problem	Fix
ModuleNotFoundError: No module named 'google'	pip install -r requirements.txt
ModuleNotFoundError: No module named 'distutils.msvccompiler'	Use Python 3.11, or install MSVC Build Tools
Wake word never triggers	Check mic is the default input device; test pyaudio device count
"Device unavailable" error	Another app is using the mic. Close Discord/browser
429 RESOURCE_EXHAUSTED from Groq	Rate limit — wait a few seconds, it retries automatically
Google TTS 401/403	Service account needs TTS and Vision roles
No text transcribed	Check GOOGLE_APPLICATION_CREDENTIALS path is correct
Jarvis doesn't remember	Memory might be off — check python settings.py
Skill not triggering	Check keywords list matches what you actually say
See API_SETUP_GUIDE.md for API-specific issues.

📜 License
MIT — see LICENSE.

Use it, fork it, ship it. Just keep the credit.

🙏 Credits
Picovoice
 — Porcupine wake word engine
Groq
 — LLM + Whisper inference
Google Cloud
 — Text-to-Speech + Vision OCR
wttr.in
 — Free weather data
DuckDuckGo
 — Web search
The Python community — for all the libraries that make this possible
📊 Project Status
Layer	Status	Added
Layer 1	✅	Core voice loop, skills foundation, VAD, retries
Layer 2	✅	Skill system, mic conflict fix, TTS fallback, backoff
Layer 3	✅	Groq migration, memory, OCR, doc creation, settings
Layer 4	✅	Function calling, web search, system control
Status: Feature complete. Shipped.
