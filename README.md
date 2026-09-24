Jarvis 🎙️
A personal voice assistant built in Python, designed to run on low-end hardware (2GB RAM, Celeron CPU). All the heavy lifting (LLM, STT, TTS, vision/OCR) is offloaded to cloud APIs so the local footprint stays tiny.

✨ Features
Core (Layer 1)

🎙️ Wake word detection — Porcupine listens for "jarvis" (or a custom .ppn file)
👂 Speech-to-text — Google Cloud Speech-to-Text after wake word fires
🧠 LLM brain — Gemini Flash (latest available: gemini-3.8-flash or gemini-2.5-flash)
🔊 Text-to-speech — Google Cloud TTS with local espeak fallback
🪶 Low memory — ~250–400MB RAM total

Skills & Resilience (Layer 2)

🛠️ Skill system — modular, auto-discovered skills (skills/ directory)
🔁 Retry with backoff — flaky network? Jarvis tries 3 times before giving up
⏱️ Voice activity detection — stops recording when you stop talking (via webrtcvad)
🎤 Shared mic pattern — fixed the mic-conflict crash from Layer 1

Documents & Memory (Layer 3)

📄 Document reader — OCR for handwritten notes via Gemini Vision (drop image in scans/, say "read the document")
📝 Document creator — generates .docx files from voice requests ("create a document about X")
💬 Toggleable memory — remembers your last 10 turns of conversation, turn it off via settings
⚙️ Settings panel — CLI menu (python settings.py) for toggling memory, changing paths, etc.

Built-in Skills

🕐 Time — "What time is it?"
📅 Date — "What's today's date?"
😂 Joke — "Tell me a joke"
🌤️ Weather — "What's the weather?" (uses wttr.in, no API key needed)
⏲️ Timer — "Set a timer for 5 minutes"
📄 Document Reader — "Read this document"
📝 Document Creator — "Create a document about [topic]"


🏗️ Stack
Component   Provider                            Why
Wake word   Picovoice                           PorcupineRuns forever, ~30MB RAM, no AVX2 needed
STT         Google Cloud Speech-to-Text         Fast, accurate, generous free tier
LLM         Gemini Flash (latest)               Cheap, fast, supports vision for OCR
TTS         Google Cloud TTS + espeak fallback  Great voice, fails gracefully
Audio       I/OPyAudio + PygameStandard,        works everywhere

🚀 Setup
1. Clone and enter the project
bashgit clone https://github.com/YOUR_USERNAME/jarvis.git
cd jarvis
2. Install Python dependencies
bashpip install -r requirements.txt
PyAudio needs system libraries (one-time):

Linux: sudo apt-get install python3-pyaudio portaudio19-dev
macOS: brew install portaudio
Windows: pip install pyaudio==0.2.13 (usually works out of the box)

espeak (TTS fallback):

Linux: sudo apt-get install espeak
macOS: brew install espeak
Windows: Download from http://espeak.sourceforge.net/

3. Set up API keys
bashcp .env.example .env
Then edit .env with your actual keys (see API Keys below).
4. Run Jarvis
bashpython main.py
Say "jarvis" to wake it, then speak your command.

🔑 API Keys
You need accounts on three services. All have free tiers that comfortably cover personal use.
1. Picovoice Porcupine (Wake Word)

Sign up: https://console.picovoice.ai/
Free tier: 3 wake words, unlimited use on personal devices
Copy your access key → PORCUPINE_ACCESS_KEY in .env
(Optional) Custom wake word: Train at console.picovoice.ai, download the .ppn file, set PORCUPINE_KEYWORD_PATH in .env

2. Google Cloud (STT + TTS)

Go to: https://console.cloud.google.com/
Create a new project (or use existing)
Enable Cloud Speech-to-Text API and Cloud Text-to-Speech API
Create a service account:

IAM & Admin → Service Accounts → Create Service Account
Grant roles: Cloud Speech-to-Text User + Cloud Text-to-Speech User
Create & download JSON key

Set GOOGLE_APPLICATION_CREDENTIALS to the absolute path of the JSON file

3. Google Gemini (LLM + Vision)

Get API key: https://aistudio.google.com/app/apikey
Free tier is generous (15 RPM, 1500 requests/day)
Set GEMINI_API_KEY in .env
Set GEMINI_MODEL (try gemini-3.8-flash; fall back to gemini-2.5-flash if not available)


⚙️ Settings Panel
Run the interactive CLI to configure Jarvis without editing files:
bashpython settings.py
You'll get a clean menu with options to:
Option                          What it does    
1. Toggle conversation memory   Turn the 10-turn context on/off
2. Set memory max turns         How many back-and-forth to remember (1–50)
3. View current memory          See what's been stored
4. Clear memory                 Wipe the conversation history
5. Set documents output dir     Where generated docs land
6. Set scans/OCR directory      Where Jarvis looks for handwritten images
7. Show current settings        Quick view of all flags
0. Exit                         Done
Changes are persisted to .env and require a Jarvis restart to take effect.
Works over SSH — no GUI dependencies. Perfect for headless Celeron laptops.

💬 Conversation Memory
Layer 3 will add toggleable conversation memory. When enabled, Jarvis remembers your last 10 turns and uses them as context for follow-up questions.
Storage: jarvis_memory.json (gitignored, plain JSON, you can inspect/edit it)
Example:
textYou:    "Jarvis, what's the capital of France?"
Jarvis: "Paris."
You:    "And what's the population?"
Jarvis: "About 2.1 million in the city proper."
The second question works because Jarvis has the first turn in context.
Toggle via:

Settings panel → Option 1
.env → set MEMORY_ENABLED=False
Or directly delete jarvis_memory.json


📄 Document Skills
Reading handwritten docs (OCR)
1. Drop your handwritten image (.jpg, .png, .webp, .heic) in the scans/ folder
2. Say "jarvis, read the document" (or "read this", "transcribe this", etc.)
3. Jarvis sends the image to Gemini Vision and transcribes it
4. Full transcript is saved as _transcript.txt next to the image
5. Jarvis speaks a short summary back

Tips for better OCR:

1. Good lighting, flat surface
2. Clear handwriting (cursive works, messy print doesn't)
3. Single page at a time

Creating documents
Say "jarvis, create a document about [topic]" and Jarvis generates a .docx file using Gemini for content structuring. Saved to the documents/ folder.
Examples:

"Create a document about my morning routine"
"Make a Word doc with a Python tutorial for beginners"
"Write a report on quarterly sales trends"


🛠️ Adding Custom Skills
Drop a new file in skills/ that inherits from Skill:
python# skills/my_skill.py
from .base import Skill

class MySkill(Skill):
    name = "my_skill"
    keywords = ["trigger phrase", "another phrase"]
    
    def handle(self, user_input: str) -> str:
        # Your logic here
        return "TTS-friendly response under 2 sentences"
Restart Jarvis — auto-discovery picks it up.

🧪 Testing
Smoke test (verify components)
bashpython smoke_test.py
Tests: mic input, Gemini API, TTS playback.
Manual test sequence
1. python main.py
2. Wait for "Listening for wake word" log
3. Say "jarvis" clearly
4. After the beep, speak a command
5. Verify response is spoken and logged

Memory test
1. Toggle memory ON via settings panel
2. Ask: "Jarvis, what's the capital of Japan?"
3. Ask: "What did I just ask you?"
4. Jarvis should remember Tokyo

🐛 Troubleshooting
"PORCUPINE_ACCESS_KEY not set"

Check .env exists and has no extra spaces/quotes around the key
Verify at https://console.picovoice.ai/

"Google Cloud credentials not found"

GOOGLE_APPLICATION_CREDENTIALS must be an absolute path to the JSON file
On Linux, check permissions: chmod 644 /path/to/service-account.json

"Device unavailable" / mic errors

Make sure no other app is using the mic (browser, Discord, etc.)
Test the mic: python -c "import pyaudio; p = pyaudio.PyAudio(); print(p.get_device_count())"
On Linux, you may need to add your user to the audio group: sudo usermod -aG audio $USER

"TTS API error: 403"

Service account needs both STT and TTS roles
Re-check IAM roles in Google Cloud Console

OCR returning garbage

Image too blurry or low-res → retake photo
Cursive + messy print + bad lighting = no model will save you
Try a clearer image first to verify the pipeline works

Memory not working
Check MEMORY_ENABLED=True in .env or settings panel
Verify jarvis_memory.json exists and is being written to
Restart Jarvis after toggling settings

High memory usage

Should run at 250–400MB RAM
If higher, check for zombie processes: ps aux | grep python
The wake word listener is the lowest-overhead piece; STT/TTS/LLM run only when active

Layer 1 mic conflict (legacy)

If you're on the pre-Layer-2 build, the wake word and listener fight for the mic
Apply the Layer 2 prompt (PROMPT_LAYER2.md) to fix this


💾 Memory Budget
Component RAM Usage:
Wake word (Porcupine)~30 MB
Python runtime~150 MB
Google API client libraries~50 MB
PyAudio + Pygame~30 MB
Total Jarvis overhead~400 MB
Heavy compute (STT, LLM, TTS) all happens in the cloud → 0 MB local.

📊 Project Status

Layer       Status             What's in it
Layer 1      Done              Core loop: wake → listen → think → speak
Layer 2      Done              Skills system, mic fix, retries, VAD, TTS fallback
Layer 3      Work in Progress  Doc reader (OCR), doc creator, memory, settings panel
Layer 4      Future            Proactive suggestions, web UI, smart home integration

📜 License
MIT — see LICENSE. Use it, fork it, sell it, just keep the credit.

🙏 Credits

Picovoice for the Porcupine wake word engine
Google Cloud for STT/TTS/Gemini APIs
wttr.in for free weather data
The Python community for the libraries that make this possible
