"""
test_compat.py — Verify all Layer 3+4 dependencies work on this Python.

Run after `pip install -r requirements.txt`:
    python test_compat.py

Reports which packages are working, which are missing, and whether
fallbacks are available.
"""

import platform
import sys

print("=" * 60)
print("  JARVIS — Dependency Compatibility Check")
print("=" * 60)
print(f"  Python:  {sys.version.split()[0]}")
print(f"  Platform: {platform.system()} {platform.release()} ({platform.machine()})")
print()

REQUIRED = [
    ("pvporcupine", "Wake word detection"),
    ("openai", "LLM + STT (Groq)"),
    ("dotenv", ".env loading"),
    ("google.cloud.texttospeech", "TTS (Google Cloud)"),
    ("google.cloud.vision", "OCR (Google Cloud)"),
    ("docx", "Document creation (.docx)"),
    ("PIL", "Image handling / screenshots"),
    ("requests", "HTTP for Google TTS"),
]

OPTIONAL = [
    ("webrtcvad", "VAD (C extension)"),
    ("sounddevice", "Audio (alternative to pyaudio)"),
    ("pycaw", "Windows volume control"),
    ("pywin32", "Windows fallback for volume"),
    ("comtypes", "Windows COM (pycaw dep)"),
    ("pyobjc", "macOS support"),
]

print("--- Required packages ---")
failed = []
for module, description in REQUIRED:
    try:
        __import__(module)
        print(f"  [OK]   {module:30} {description}")
    except ImportError as e:
        print(f"  [FAIL] {module:30} MISSING ({e})")
        failed.append(module)

print()
print("--- Optional packages ---")
for module, description in OPTIONAL:
    try:
        __import__(module)
        print(f"  [OK]   {module:30} {description}")
    except ImportError:
        print(f"  [SKIP] {module:30} not installed (may be fine)")

print()
print("--- Audio backend ---")
try:
    from importlib import import_module
    pyaudio = import_module("pyaudio")
    p = pyaudio.PyAudio()
    count = p.get_device_count()
    p.terminate()
    print(f"  [OK]   pyaudio found {count} audio device(s)")
except ImportError:
    print("  [SKIP] pyaudio not installed")
except (OSError, RuntimeError) as e:
    print(f"  [WARN] pyaudio installed but failed: {e}")

from importlib.util import find_spec

if find_spec("sounddevice") is not None:
    print("  [OK]   sounddevice available")
else:
    print("  [SKIP] sounddevice not installed")

print()
print("--- VAD backend ---")
from importlib.util import find_spec

if find_spec("webrtcvad") is not None:
    print("  [OK]   webrtcvad available (C extension, faster)")
else:
    print("  [SKIP] webrtcvad not installed")
    try:
        from simple_vad import SimpleVAD
        vad = SimpleVAD(2)
        test = b"\x00\x10" * 480  # ~30ms of low-amplitude audio
        assert vad.is_speech(test) is False
        print("  [OK]   SimpleVAD available as fallback (pure Python)")
    except ImportError:
        print("  [FAIL] NEITHER webrtcvad NOR simple_vad available")
        failed.append("vad")

print()
print("--- API configuration ---")
try:
    import os
    from importlib import import_module
    from pathlib import Path

    import_module("dotenv").load_dotenv(Path(__file__).parent / ".env")

    checks = [
        ("PORCUPINE_ACCESS_KEY", "Picovoice wake word"),
        ("OPENAI_API_KEY", "Groq LLM + STT"),
        ("OPENAI_BASE_URL", "Groq endpoint"),
        ("OPENAI_MODEL", "LLM model"),
        ("GOOGLE_APPLICATION_CREDENTIALS", "Google Cloud TTS + Vision"),
    ]
    for var, description in checks:
        value = os.getenv(var)
        if value:
            if "CREDENTIALS" in var:
                path = Path(value)
                if path.is_absolute():
                    exists = path.exists()
                else:
                    exists = (Path(__file__).parent / path).exists()
                status = "[OK]" if exists else "[FAIL] file not found"
                print(f"  {status} {var:32} {description}")
                if not exists:
                    failed.append(var)
            else:
                masked = value[:8] + "..." if len(value) > 12 else value
                print(f"  [OK]   {var:32} {description} ({masked})")
        else:
            print(f"  [FAIL] {var:32} NOT SET — {description}")
            failed.append(var)
except ImportError:
    print("  [SKIP] python-dotenv not installed, can't check .env")

print()
print("=" * 60)
if failed:
    print(f"  RESULT: {len(failed)} issue(s) found")
    for item in failed:
        print(f"    - {item}")
    print()
    print("  Fix: pip install -r requirements.txt")
    print("  See API_SETUP_GUIDE.md for key setup")
    print("=" * 60)
    sys.exit(1)
else:
    print("  RESULT: All checks passed — Jarvis is ready to run")
    print()
    print("  Next: python main.py")
    print("=" * 60)
