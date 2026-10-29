"""
chat.py — Talk to Jarvis in text. No microphone required.

Use this when the mic is not cooperating, or when you just want to type.

    python chat.py
    python chat.py --no-voice     print replies only, never speak them
    python chat.py --no-memory    start with a clean conversation

Everything else works exactly like the voice loop: the same skills, the same
function-calling tools, the same conversation memory.
"""

import logging
import os
import sys

try:
    from brain import Brain
    from config import validate_required_keys
    from conversation import handle_command, list_skills
except ImportError as e:
    print(f"\n  Missing dependency: {e}")
    print("  Install everything with:  pip install -r requirements.txt\n")
    sys.exit(1)

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

BANNER = r"""
  _                            _
 | |    __ _ _ __   __ _ _   _| |_ __ __ ___      __
 | |   / _` | '_ \ / _` | | | | __/ _` \ \ \ /\ / /
 | |__| (_| | |_) | (_| | |_| | || (_| |\ V  V /
 |____\__,_| .__/ \__,_|\__,_|\__\__,_| \_/\_/
           |_|                      text mode
"""

HELP = """
  Commands
  --------
  /help        show this help
  /skills      list available skills
  /memory      show the current conversation memory
  /clear       clear the conversation memory
  /voice on    speak replies out loud
  /voice off   print replies only
  /quit        exit (or Ctrl+C)

  Anything else is sent to Jarvis.
"""


class Chat:
    def __init__(self, voice: bool = True):
        self.brain = Brain()
        self.voice = voice
        self.speaker = None
        if voice:
            try:
                from speaker import Speaker

                self.speaker = Speaker()
            except Exception as e:
                logger.warning(f"Speech output unavailable: {e}")
                self.voice = False
                print("  (Voice output unavailable — running in text-only mode.)")

    def speak(self, text: str) -> None:
        if self.voice and self.speaker is not None:
            try:
                self.speaker.speak(text)
            except Exception as e:
                logger.warning(f"Speech failed: {e}")

    def run(self) -> None:
        print(BANNER)
        print(f"  Model : {self.brain.model}")
        print(f"  Memory: {'on' if self.brain.memory.enabled else 'off'} "
              f"({self.brain.memory.storage_path})")
        print("  Type /help for commands, /quit to exit.\n")

        while True:
            try:
                raw = input("You> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n  Bye.")
                break

            if not raw:
                continue

            if raw.startswith("/"):
                if self.handle_command_line(raw):
                    continue

            response, source = handle_command(raw, self.brain)
            if not response:
                continue

            print(f"\nJarvis> {response}")
            if source.startswith("skill:"):
                logger.info(f"handled by {source}")
            self.speak(response)
            print()

    def handle_command_line(self, raw: str) -> bool:
        """Handle a slash command. Returns True if it was consumed."""
        command = raw[1:].strip().lower()
        args = raw[1:].strip()

        if command in ("quit", "exit", "q"):
            print("  Bye.")
            raise SystemExit(0)

        if command in ("help", "h", "?"):
            print(HELP)

        elif command == "skills":
            names = list_skills()
            if names:
                print("\n  Skills:")
                for name in names:
                    print(f"    - {name}")
            else:
                print("\n  No skills loaded.")
            print()

        elif command == "memory":
            messages = self.brain.memory.get_messages()
            if not messages:
                print("\n  Memory is empty.\n")
            else:
                print(f"\n  Memory ({len(messages)} messages):")
                for message in messages:
                    role = message.get("role", "?")
                    content = message.get("content", "")
                    print(f"    {role:9}: {content[:120]}")
                print()

        elif command == "clear":
            self.brain.memory.clear()
            print("\n  Memory cleared.\n")

        elif command == "voice":
            parts = args.split()
            if len(parts) > 1 and parts[1].lower() in ("on", "off"):
                self.voice = parts[1].lower() == "on"
                if self.voice and self.speaker is None:
                    try:
                        from speaker import Speaker

                        self.speaker = Speaker()
                    except Exception as e:
                        logger.warning(f"Speech unavailable: {e}")
                        self.voice = False
                print(f"\n  Voice output {'ON' if self.voice else 'OFF'}.\n")
            else:
                print(f"\n  Voice output is {'ON' if self.voice else 'OFF'}.\n")

        else:
            print(f"\n  Unknown command '/{command}'. Type /help.\n")

        return True


def main() -> None:
    validate_required_keys()

    voice = "--no-voice" not in sys.argv
    if "--no-memory" in sys.argv:
        os.environ["MEMORY_ENABLED"] = "False"

    Chat(voice=voice).run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n  Bye.")
    except SystemExit:
        pass
