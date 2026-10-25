import logging
import os

from config import (
    DOCS_OUTPUT_DIR,
    MEMORY_ENABLED,
    MEMORY_MAX_TURNS,
    OCR_TEMP_DIR,
)
from memory import ConversationMemory

logger = logging.getLogger(__name__)


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")

def show_menu():
    print("""
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
""")

def update_env(key: str, value: str):
    """Update the environment variable in the .env file."""
    env_path = ".env"
    lines = []
    found = False
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    else:
        logger.warning(f"{env_path} not found — creating a new one.")

    with open(env_path, "w", encoding="utf-8") as f:
        for line in lines:
            if line.strip().startswith(f"{key}="):
                f.write(f"{key}={value}\n")
                found = True
            else:
                f.write(line if line.endswith("\n") else line + "\n")
        if not found:
            f.write(f"{key}={value}\n")

def main():
    memory = ConversationMemory()
    while True:
        clear_screen()
        show_menu()
        choice = input("Enter your choice: ").strip()

        if choice == "1":
            new_state = memory.toggle()
            update_env("MEMORY_ENABLED", "True" if new_state else "False")
            print(f"\n[OK] Memory is now {'ON' if new_state else 'OFF'}.")
            print(" Restart Jarvis for changes to take effect.")
        
        elif choice == "2":
            try:
                turns = int(input("Max conversation turns (1-50):"))
                if 1 <= turns <= 50:
                    update_env("MEMORY_MAX_TURNS", str(turns))
                    print(f"\n[OK] Memory max turns set to {turns}.")
                else:
                    print("\n[X] Must be between 1 and 50")
            except ValueError:
                print("\n[X] Invalid input. Please enter a number.")
        
        elif choice == "3":
            history = memory.get_context()
            if not history:
                print("\n (no memory yet)")
            else:
                print(f"\n {len(history) // 2} stored turns")
                for msg in history[-10:]:
                    prefix = "You:  " if msg["role"] == "user" else "Jarvis: "
                    print(f"{prefix}{msg['content'][:60]}")

        elif choice == "4":
            if input("Clear all memory? (yes/no): ").strip().lower() == "yes":
                memory.clear_memory()
                print("\n[OK] All memory cleared.")

        elif choice == "5":
            new_dir = input(f"Documents directory [{DOCS_OUTPUT_DIR}]: ").strip()
            if new_dir:
                update_env("DOCS_OUTPUT_DIR", new_dir)
                print("\n[OK] Updated. Restart Jarvis to apply changes.")

        elif choice == "6":
            new_dir = input(f"Scans/OCR directory [{OCR_TEMP_DIR}]: ").strip()
            if new_dir:
                update_env("OCR_TEMP_DIR", new_dir)
                print("\n[OK] Updated. Restart Jarvis to apply changes.")

        elif choice == "7":
            print(f"Current settings:\n"
                  f"Memory Enabled: {MEMORY_ENABLED}\n"
                  f"Memory Max Turns: {MEMORY_MAX_TURNS}\n"
                  f"Documents Output Directory: {DOCS_OUTPUT_DIR}\n"
                  f"Scans/OCR Directory: {OCR_TEMP_DIR}")
        
        elif choice == "0":
            print("Exiting settings panel.")
            break
        else:
            print("Invalid choice. Please try again.")

        input("\nPress Enter to continue...")

if __name__ == "__main__":
    main()
        