API Setup Guide
Everything you need to get Jarvis running from scratch. All services used have generous free tiers.
Time to complete: ~20 minutes
Total cost: $0

Overview





























#ServiceWhat it doesKey needed1Picovoice PorcupineWake word detectionPORCUPINE_ACCESS_KEY2GroqLLM brain + speech recognitionOPENAI_API_KEY3Google CloudText-to-speech + OCRGOOGLE_APPLICATION_CREDENTIALS

Want to skip Google Cloud? TTS can fall back to local espeak (robotic but free/offline). Vision OCR would need an alternative. Everything else works without it.


1. Picovoice Porcupine (Wake Word)
What it does
Listens for "jarvis" in the background. Runs 100% locally on your CPU — no API calls, no latency, no cost.
Setup
1.Go to https://console.picovoice.ai/2.Sign up (free — GitHub or Google login works)3.Dashboard → Access Key tab → Create Access Key4.Copy the key (long string starting with letters/numbers)
Optional: Custom wake word
The built-in keyword is "jarvis". For something like "Yo Jarvis" or your own phrase:
1.In the Picovoice console → Keywords tab → Custom Keyword2.Record 3+ samples of yourself saying the phrase3.Train it (takes ~2 minutes)4.Download the .ppn file5.Put it in your project folder as jarvis_wake.ppn6.Add to .env:
envPORCUPINE_KEYWORD_PATH=./jarvis_wake.ppn
Note: If you don't set PORCUPINE_KEYWORD_PATH, Jarvis uses the built-in "jarvis" keyword. Both work.
Verify
bashpython -c "import pvporcupine; print('Porcupine OK')"
Free tier

3 custom keywords
Unlimited usage on personal devices
No credit card required


2. Groq (LLM + Speech-to-Text)
What it does

LLM: the brain — generates responses, decides which skill to call
STT: converts your speech to text

Setup
1.Go to https://console.groq.com/keys2.Sign up with Google/GitHub3.Click "Create API Key"4.Name it jarvis → Create5.Copy the key (starts with gsk_)
Add to .env
envOPENAI_API_KEY=gsk_your_actual_key_here
OPENAI_BASE_URL=https://api.groq.com/openai/v1
OPENAI_MODEL=openai/gpt-oss-120b
GROQ_STT_MODEL=whisper-large-v3-turbo
Verify (test the LLM)
bashpython -c "from openai import OpenAI; import os; from dotenv import load_dotenv; load_dotenv(); c=OpenAI(api_key=os.getenv('OPENAI_API_KEY'), base_url=os.getenv('OPENAI_BASE_URL')); r=c.chat.completions.create(model=os.getenv('OPENAI_MODEL'), messages=[{'role':'user','content':'Say OK'}]); print(r.choices[0].message.content)"
Should print "OK" or similar.
List available models
bashpython -c "from openai import OpenAI; import os; from dotenv import load_dotenv; load_dotenv(); c=OpenAI(api_key=os.getenv('OPENAI_API_KEY'), base_url=os.getenv('OPENAI_BASE_URL')); [print(m.id) for m in c.models.list().data]"
If openai/gpt-oss-120b isn't listed, try one that is (e.g., llama-3.3-70b-versatile) and update .env.
Model options



































ModelSpeedQualityUse foropenai/gpt-oss-120bFastGreatDefault — smart + quickllama-3.3-70b-versatileMediumGreatComplex reasoningllama-3.1-8b-instantVery fastGoodSimple commands, quick chatmixtral-8x7b-32768FastGoodBalanced alternative
Free tier

~14,000 requests/day
~30 requests/minute
No credit card needed
Response time: ~200ms (very fast)


3. Google Cloud (TTS + OCR)
What it does

TTS: converts Jarvis's text response into natural speech
Vision (OCR): reads handwritten text from images

Step 3.1 — Create a project
1.Go to https://console.cloud.google.com/2.Click the project dropdown (top bar) → "New Project"3.Name: jarvis (or anything)4.Click Create
Step 3.2 — Enable billing (REQUIRED for free tier)

⚠️ This step trips people up. Even with free tier, Google requires a billing account linked to the project. You will not be charged unless you exceed free tier.

1.Go to https://console.cloud.google.com/billing2.Click "Link a billing account" → "Create billing account"3.Enter your details:

Country/region: India
Payment method: a debit/credit card (you won't be charged)
4.Accept terms → Create5.Make sure the new billing account is linked to your jarvis project
Add a budget alert (recommended):
1.Go to https://console.cloud.google.com/billing2.Budgets & alerts → Create budget3.Amount: $5 (or 1 USD)4.Add your email5.This way you get notified if anything goes wrong
Step 3.3 — Enable the APIs
Go to https://console.cloud.google.com/apis/library and enable each:




















APISearch forPurpose1Cloud Text-to-Speech APIJarvis speaking2Cloud Vision APIOCR for documents
For each: click the API name → Enable button.

Note: You do NOT need "Cloud Speech-to-Text API" anymore — that moved to Groq in Layer 3.

Step 3.4 — Create a service account
1.Go to https://console.cloud.google.com/iam-admin/serviceaccounts2.+ CREATE SERVICE ACCOUNT3.Name: jarvis-service-account4.Create and Continue5.Grant access to project → select role: Cloud TTS User6.Add another role → Cloud Vision User7.Continue → Done
Step 3.5 — Create a JSON key
1.Click the service account email → Keys tab2.+ ADD KEY → Create new key → JSON3.Download the file — it will be named something like jarvis-service-account-abc123.json4.Move it into your project folder and rename it:
bashmv ~/Downloads/jarvis-service-account-*.json ./gcp-credentials.json
Step 3.6 — Add to .env
envGOOGLE_APPLICATION_CREDENTIALS=./gcp-credentials.json

Use a relative path (as above) so the project stays portable. Absolute paths work too but break if you move the folder.

Step 3.7 — Verify
bashpython -c "from google.cloud import texttospeech; c=texttospeech.TextToSpeechClient(); r=c.synthesize_speech(text='Hello from Jarvis', voice=texttospeech.VoiceSelectionParams(language_code='en-US', name='en-US-Standard-A'), audio_config=texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)); print('TTS OK' if r.audio_content else 'TTS FAILED')"
Should print TTS OK.
Free tier

















APIFree TierCloud Text-to-Speech4 million characters/month (Standard voices)Cloud Vision1,000 images/month
For reference: a typical Jarvis response is ~80 characters. That's 50,000 free responses per month on TTS. You'll never hit the cap.
TTS voice options

























VoiceQualityNotesen-US-Standard-AGoodAlways availableen-US-Neural2-JExcellentMay need to be enabled (see below)en-US-Neural2-CExcellentFemale alternative
To use Neural2 voices, request access at:
https://cloud.google.com/text-to-speech/docs/voices → find the voice → "Request access"
Default in config.py is en-US-Standard-A for reliability.

4. (Optional) Alternative AI Provider
Don't want to use Groq? Any OpenAI-compatible API works. Just change three lines in .env:
DeepSeek (very cheap, capable)
1.Go to https://platform.deepseek.com/2.Sign up → API keys → create key3.Update .env:
envOPENAI_API_KEY=sk-your_deepseek_key
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_MODEL=deepseek-chat
GROQ_STT_MODEL=whisper-large-v3-turbo   # ← still needs Groq for STT
Note: STT still needs Groq. To keep everything on one provider, use Groq for STT and DeepSeek for the LLM (set OPENAI_BASE_URL per-component in code).

OpenAI (best quality, paid)
envOPENAI_API_KEY=sk-your_openai_key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
Ollama (fully local, no API)
bashollama pull llama3.1:8b
envOPENAI_API_KEY=ollama
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_MODEL=llama3.1:8b

⚠️ Local models need a GPU or 16GB+ RAM for decent speed. Not recommended on your Celeron.


📋 Complete .env Template
env# ─── Wake word (Picovoice) ───
# Get: https://console.picovoice.ai/
PORCUPINE_ACCESS_KEY=

# Optional: custom wake word (.ppn file)
# PORCUPINE_KEYWORD_PATH=./jarvis_wake.ppn

# ─── LLM + STT (Groq) ───
# Get: https://console.groq.com/keys
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.groq.com/openai/v1
OPENAI_MODEL=openai/gpt-oss-120b
GROQ_STT_MODEL=whisper-large-v3-turbo

# ─── TTS + OCR (Google Cloud) ───
# See API_SETUP_GUIDE.md Section 3
GOOGLE_APPLICATION_CREDENTIALS=./gcp-credentials.json

# ─── Feature flags (optional) ───
MEMORY_ENABLED=true
MEMORY_MAX_TURNS=10
DOCS_OUTPUT_DIR=./documents
OCR_TEMP_DIR=./scans
SCREENSHOTS_DIR=./screenshots

✅ Final Verification
Run this after setup. It checks every dependency:
```bash
python test_compat.py```
Then test each service:
bash# LLM
python -c "from brain import Brain; b=Brain(); print(b.get_response('say hi'))"

# STT (record 5 seconds, then transcribe)
python -c "from mic_manager import MicManager; from listener import Listener; m=MicManager(); a=m.record_command(); print(Listener().transcribe(a))"

# TTS
python -c "from speaker import Speaker; Speaker().speak('Testing one two three')"

# Full loop
python main.py

🆘 Troubleshooting
"PORCUPINE_ACCESS_KEY not set"

.env file missing? Run cp .env.example .env
Check for typos: PORCUPINE not POCUPINE
No quotes around values
Restart Jarvis after editing

"401 Unauthorized" from Groq

Key is wrong or has whitespace
Regenerate at https://console.groq.com/keys
Make sure OPENAI_API_KEY=gsk_... (Groq keys start with gsk_)

"404 Model not found" from Groq

Model name doesn't exist on your account
Run the "list available models" command above
Update OPENAI_MODEL in .env

"429 Rate limit" from Groq

You hit 30 req/min or 14k/day
Wait a few seconds — Jarvis auto-retries
Check usage at https://console.groq.com

Google TTS "401" or "403"

Service account JSON path is wrong
Service account is missing the TTS/Vision roles
Regenerate the key if expired
Verify billing is linked to the project

"DefaultCredentialsError" from Google

GOOGLE_APPLICATION_CREDENTIALS points to a non-existent file
Use a path relative to where you run the command

"Wake word never detected"

Wrong mic? Check OS sound settings
Test mic: python -c "import pyaudio; p=pyaudio.PyAudio(); print(p.get_device_count())"
Speak clearly and at normal volume
If using custom .ppn, verify the path in .env

"Device unavailable" / mic errors

Another app is holding the mic (Discord, browser, Zoom)
Close them and retry

Nothing happens after "jarvis"

The mic might be recording silence — check jarvis.log
Look for Recording command... then Transcribed: ... lines


📚 Quick Links





































ResourceURLPicovoice Consolehttps://console.picovoice.ai/Groq Consolehttps://console.groq.com/keysGoogle Cloud Consolehttps://console.cloud.google.com/Google Cloud Billinghttps://console.cloud.google.com/billingTTS Voice Listhttps://cloud.google.com/text-to-speech/docs/voicesVision API Pricinghttps://cloud.google.com/vision/pricingGroq Rate Limitshttps://ai.google.dev/gemini-api/docs/rate-limits (for reference)

Setup done. Run python main.py and say "jarvis". 🚀