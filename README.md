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
3. Install required system dependencies (PyAudio and PortAudio) `sudo apt install portaudio19-dev python3-pip`
4. `pip install -r requirements.txt`
5. `python main.py`

## API Keys Needed
- **Porcupine** — https://picovoice.ai/ (free personal tier)
- **Google Cloud Speech** — https://console.cloud.google.com/ (enable Speech-to-Text API, create service account)
- **Gemini** — https://aistudio.google.com/ (free API key)

## Memory Budget
Target: <400MB RAM. Cloud services handle the heavy lifting.

## Common Errors & Troubleshooting
1. Could not find a verison that satisfies the requirement pyaudio - Install PortAudio `sudo apt install portaudio19-dev` and retry
2. PORCUPINE_ACCESS_KEY not set - Ensure `.env` file exists and contains the key
3. Google Cloud Speech: 403 Permission denied - Check that your service account has the Speech-to-Text API enabled and the JSON path is correct
4. pygame.error: Couldn't open audio device - Install ALSA or PulseAudio drivers. On headless systems, use `export SDL_AUDIODRIVER=alsa`
5. ModuleNotFoundError: No module named 'google' - Install `google-cloud-speech` and `google-auth` from `requirements.txt`
6. RuntimeError: No audio input device found - Check your microphone connection and permissions. Use `arecord -l` to list devices

## Status
🚧 Layer 1: Core loop (wake → listen → think → speak)
    
    Update 1.1 : Minor code fixes and update to the README.md
