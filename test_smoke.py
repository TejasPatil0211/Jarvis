"""
Smoke test for Jarvis. Costs ~2 API calls with --online.

Usage:
    python test_smoke.py            # offline checks only
    python test_smoke.py --online   # also makes a live LLM call
"""

import os
import sys
import traceback

RESULTS = []


def run(label, fn):
    """Run a check, record the outcome, and keep going on failure."""
    try:
        fn()
    except Exception as e:
        RESULTS.append((label, False, f"{type(e).__name__}: {e}"))
        print(f"[FAIL] {label} — {type(e).__name__}: {e}")
        if os.environ.get("JARVIS_TRACE"):
            traceback.print_exc()
    else:
        RESULTS.append((label, True, ""))
        print(f"[ OK ] {label}")


def test_imports():
    from brain import Brain
    from listener import Listener
    from speaker import Speaker
    assert Brain is not None
    assert Listener is not None
    assert Speaker is not None


def test_tools_registered():
    """Every Layer 4 tool must be wired up — a broken import here means
    the whole function-calling layer is silently disabled."""
    import tools
    from config import SCREENSHOTS_DIR
    assert tools.SCREENSHOTS_DIR == SCREENSHOTS_DIR, "screenshot dir mismatch"
    expected = {
        "get_current_time", "get_weather", "tell_joke", "set_timer",
        "web_search", "open_application", "set_volume", "take_screenshot",
    }
    names = {t["function"]["name"] for t in tools.SKILL_TOOLS}
    missing = expected - names
    assert not missing, f"missing tools: {sorted(missing)}"


def test_brain_endpoint():
    from brain import Brain
    b = Brain()
    assert b.model, "model name is empty"


def test_memory_roundtrip():
    from memory import ConversationMemory
    mem = ConversationMemory(storage_path="./_smoke_mem.json")
    mem.enabled = True
    mem.clear()
    mem.add_turn("hello", "hi")
    mem.add_turn("bye", "cya")
    msgs = mem.get_messages()
    assert len(msgs) == 4, f"expected 4 messages, got {len(msgs)}"
    assert msgs[0] == {"role": "user", "content": "hello"}
    assert msgs[1] == {"role": "assistant", "content": "hi"}
    # persistence check — this used to silently fail
    assert os.path.exists("./_smoke_mem.json"), "memory was not written to disk"
    mem.clear()
    if os.path.exists("./_smoke_mem.json"):
        os.remove("./_smoke_mem.json")


def test_skill_discovery():
    from registry import SkillRegistry
    SkillRegistry.discover()
    names = {s.name for s in SkillRegistry._skills}
    for required in ("time", "date", "joke", "timer", "weather",
                     "document_creator", "document_reader"):
        assert required in names, f"missing skill: {required}"


def test_llm_call():
    from brain import Brain
    b = Brain()
    reply = b.get_response("What is 2+2? Answer with just the number.")
    assert reply, "empty LLM reply"
    print(f"       reply: {reply[:80]}")


def main():
    print("=" * 62)
    print("  JARVIS — Smoke test")
    print("=" * 62)

    run("imports", test_imports)
    run("layer 4 tools registered", test_tools_registered)
    run("memory roundtrip", test_memory_roundtrip)
    run("skill discovery", test_skill_discovery)

    if "--online" in sys.argv:
        run("brain endpoint", test_brain_endpoint)
        run("live LLM call", test_llm_call)
    else:
        print("[SKIP] brain endpoint + live LLM call (pass --online to enable)")

    print()
    print("=" * 62)
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    total = len(RESULTS)
    if passed == total:
        print(f"  RESULT: {passed}/{total} passed")
        print("=" * 62)
        sys.exit(0)

    print(f"  RESULT: {passed}/{total} passed, {total - passed} FAILED")
    for label, ok, detail in RESULTS:
        if not ok:
            print(f"    - {label}: {detail}")
    print()
    print("  Missing a module? Run: python test_compat.py")
    print("=" * 62)
    sys.exit(1)


if __name__ == "__main__":
    main()
