import json
import logging
import os
import platform
import subprocess
import threading
import time
from datetime import datetime, timezone
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

from config import SCREENSHOTS_DIR

logger = logging.getLogger(__name__)

SKILL_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Get the current time, date, or day of the week",
            "parameters": {
                "type": "object",
                "properties": {
                    "what": {
                        "type": "string",
                        "enum": ["time", "date", "day"],
                        "description": "What to get: time, date, or day",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City name"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "tell_joke",
            "description": "Tell the user a random joke",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_timer",
            "description": "Set a timer for N seconds, minutes, or hours",
            "parameters": {
                "type": "object",
                "properties": {
                    "duration": {"type": "integer"},
                    "unit": {"type": "string", "enum": ["seconds", "minutes", "hours"]},
                },
                "required": ["duration", "unit"],
            },
        },
    },
    {
       "type": "function",
       "function": {
           "name": "web_search",
           "description": "Search the web for current information",
           "parameters": {
               "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
           },
       },
    },
    {
        "type": "function",
        "function": {
            "name": "open_application",
            "description": "Open a desktop application or website",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_volume",
            "description": "Set system volume to a specific level (0-100)",
            "parameters": {
                "type": "object",
                "properties": {"level": {"type": "integer"}},
                "required": ["level"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "take_screenshot",
            "description": "Take a screenshot of the current screen",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

def execute_tool(function_name: str, args: dict) -> str:
    """Route a function call to the appropriate implementation."""
    try:
        if function_name == "get_current_time": return _get_time(args.get("what", "time"))
        if function_name == "get_weather": return _get_weather(args.get("location", ""))
        if function_name == "tell_joke": return _tell_joke()
        if function_name == "set_timer": return _set_timer(args.get("duration", 0), args.get("unit", "minutes"))
        if function_name == "web_search": return _web_search(args.get("query", ""))
        if function_name == "open_application": return _open_app(args.get("name", ""))
        if function_name == "set_volume": return _set_volume(args.get("level", 50))
        if function_name == "take_screenshot": return _take_screenshot()
        return f"Tool {function_name} not found."
    except (ImportError, OSError, subprocess.SubprocessError, TypeError, ValueError) as e:
        logger.error(f"Tool execution error ({function_name}): {e}")
        return f"Sorry, I failed to execute {function_name}."

def _get_time(what: str) -> str:
    now = datetime.now().astimezone()
    if what == "date": return now.strftime("Today is %B %d, %Y.")
    if what == "day": return now.strftime("Today is %A.")
    return now.strftime("It's %I:%M %p.")

def _get_weather(location: str = "") -> str:
    try:
        url = f"https://wttr.in/{location}?format=j1" if location else "https://wttr.in?format=j1"
        req = Request(url, headers={"User-Agent": "jarvis"})
        with urlopen(req, timeout=5) as resp:
            data = json.load(resp)
        current = data.get("current_condition", [{}])[0]
        temp = current.get("temp_C", "?")
        desc = current.get("weatherDesc", [{}])[0].get("value", "unknown")
        return f"Weather in {location or 'your area'}: {desc.lower()}, {temp}C."
    except (OSError, ValueError, TypeError):
        return "Weather data unavailable."

def _tell_joke() -> str:
    try:
        from joke_skill import JokeSkill
        return JokeSkill().handle("joke")
    except (ImportError, AttributeError):
        return "Why don't scientists trust atoms? Because they make up everything."

def _set_timer(duration: int, unit: str) -> str:
    if duration <= 0:
        return "Please specify a positive duration."
    unit = (unit or "minutes").lower()
    if unit.startswith("hour") or unit.startswith("hr"):
        seconds = duration * 3600
    elif unit.startswith("min"):
        seconds = duration * 60
    elif unit.startswith("sec"):
        seconds = duration
    else:
        seconds = duration * 60  # default to minutes

    def _fire(delay: int) -> None:
        time.sleep(delay)
        try:
            from speaker import Speaker
            Speaker().speak("Timer has ended!")
        except (ImportError, OSError, AttributeError, RuntimeError):
            pass

    threading.Thread(target=_fire, args=(seconds,), daemon=True).start()
    return f"Timer set for {duration} {unit}."

def _web_search(query: str) -> str:
    if not query: return "No search query provided."
    try:
        url = f"https://api.duckduckgo.com/?q={quote_plus(query)}&format=json&no_html=1"
        req = Request(url, headers={"User-Agent": "jarvis"})
        with urlopen(req, timeout=8) as resp:
            data = json.load(resp)
        abstract = (data.get("AbstractText") or "").strip()
        if abstract:
            return f"Here's what I found: {abstract[:300]}"
        related = data.get("RelatedTopics", [])
        snippets = [t.get("Text", "") for t in related[:3] if isinstance(t, dict) and t.get("Text")]
        if snippets:
            return f"Search results: {' | '.join(snippets)[:300]}"
        return f"Nothing specific found for '{query}'."
    except (OSError, ValueError, TypeError):
        return "Web search failed."

def _open_app(name: str) -> str:
    name = (name or "").strip()
    if not name: return "No application specified."

    system = platform.system()
    if "." in name and not name.endswith(".exe") and " " not in name:
        url = name if name.startswith("http") else f"https://{name}"
        try:
            if system == "Windows": os.startfile(url)
            elif system == "Darwin": subprocess.Popen(["open", url])
            else: subprocess.Popen(["xdg-open", url])
            return f"Opening {url}."
        except (OSError, ValueError, TypeError, subprocess.SubprocessError) as e: return f"Couldn't open URL: {e}"

    name = name.lower()
    apps = {
        "chrome": {"Windows": "chrome.exe", "Darwin": "Google Chrome", "Linux": "google-chrome"},
        "code": {"Windows": "code.cmd", "Darwin": "Visual Studio Code", "Linux": "code"},
        "notepad": {"Windows": "notepad.exe", "Darwin": "TextEdit", "Linux": "gedit"},
        "calculator": {"Windows": "calc.exe", "Darwin": "Calculator", "Linux": "gnome-calculator"}
    }
    app = apps.get(name, {}).get(system, name)

    try:
        if system == "Windows": os.startfile(app)
        elif system == "Darwin": subprocess.Popen(["open", "-a", app])
        else: subprocess.Popen([app])
        return f"Opening {name}."
    except (OSError, ValueError, TypeError, subprocess.SubprocessError): return f"Couldn't open {name}."

def _set_volume(level: int) -> str:
    level = max(0, min(100, int(level)))
    system = platform.system()

    if system == "Windows":
        try:
            from ctypes import POINTER, cast

            from comtypes import CLSCTX_ALL  # type: ignore[import-not-found]
            from pycaw.pycaw import (  # type: ignore[import-not-found]
                AudioUtilities,
                IAudioEndpointVolume,
            )
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            volume.SetMasterVolumeLevelScalar(level / 100.0, None)
            return f"Volume set to {level}%."
        except ImportError:
            return "Need pycaw and comtypes for Windows volume. Run: pip install pycaw comtypes"
        except (AttributeError, OSError, TypeError, ValueError) as e:
            return f"Volume control failed: {e}"
    elif system == "Darwin":
        subprocess.run(["osascript", "-e", f"set volume output volume {level}"], check=True)
        return f"Volume set to {level}%."
    else:
        try:
            subprocess.run(["amixer", "-D", "pulse", "sset", "Master", f"{level}%"], check=True, capture_output=True)
            return f"Volume set to {level}%."
        except FileNotFoundError:
            return "amixer not found. Install via: sudo apt install alsa-utils"

def _take_screenshot() -> str:
    try:
        from importlib import import_module

        ImageGrab = import_module("PIL.ImageGrab")
        os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
        filename = os.path.join(SCREENSHOTS_DIR, f"shot_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.png")
        ImageGrab.grab().save(filename)
        return "Screenshot saved."
    except ImportError:
        return "Screenshot support requires Pillow. Install it with: pip install Pillow."
    except (OSError, AttributeError, ValueError, TypeError):
        return "Couldn't take screenshot. (Linux requires scrot or gnome-screenshot)."