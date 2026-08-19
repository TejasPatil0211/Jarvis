# Jarvis 🎙️

Personal voice assistant built on Python, running on a 2GB Celeron laptop.

## Stack
- **Wake word:** Porcupine ("Yo Jarvis")
- **STT:** Google Cloud Speech-to-Text
- **LLM:** Gemini 1.5 Flash
- **TTS:** Gemini TTS
- **Audio:** pyaudio + pygame

## Project Structure
```
jarvis/
├── main.py              # entry point, runs the core loop
├── config.py            # loads .env, defines constants
├── wake_word.py         # Porcupine listener (continuous)
├── listener.py          # post-wake command capture + STT
├── brain.py             # Gemini API call
├── speaker.py           # TTS playback via pygame
├── .env                 # API keys (gitignored)
├── .env.example         # template
├── requirements.txt     # pinned deps
└── README.md
```

## Setup
1. Clone this repo
2. Copy `.env.example` to `.env` and fill in your API keys
3. `pip install -r requirements.txt`
4. `python main.py`

## API Keys Needed
- **Porcupine** — https://picovoice.ai/ (free personal tier)
- **Google Cloud Speech** — https://console.cloud.google.com/ (enable Speech-to-Text API, create service account)
- **Gemini** — https://aistudio.google.com/ (free API key)

## Memory Budget
Target: <400MB RAM. Cloud services handle the heavy lifting.

## Status
🚧 Layer 1: Core loop (wake → listen → think → speak)
