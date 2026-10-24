"""Smoke test for errors in code. Costs ~2 API calls."""
import os
import sys


def test_imports():
    from brain import Brain
    from listener import Listener
    assert Brain is not None
    assert Listener is not None
    print("[1] All imports OK")

def test_brain_endpoint():
    from brain import Brain
    b = Brain()
    print(f"[2] Brain model: {b.model}")
    assert b.model, "model name is empty"

def test_llm_call():
    from brain import Brain
    b = Brain()
    reply = b.get_response("What is 2+2? Answer with just the number.")
    print(f"[3] LLM reply: {reply[:80]}")
    assert reply, "empty LLM reply"

def test_memory_roundtrip():
    from memory import ConversationMemory
    mem = ConversationMemory(storage_path="./_smoke_mem.json")
    mem.enabled = True
    mem.clear()
    mem.add_turn("hello","hi")
    mem.add_turn("bye","cya")
    msgs = mem.get_messages()
    assert len(msgs) == 4, f"expected 4 messages, got {len(msgs)}"
    assert msgs[0] == {"role": "user", "content": "hello"}
    assert msgs[1] == {"role": "assistant", "content": "hi"}
    mem.clear()
    if os.path.exists("./_smoke_mem.json"):
        os.remove("./_smoke_mem.json")
    print("[4] Memory roundtrip OK")

def test_skill_discovery():
    from registry import SkillRegistry
    SkillRegistry.discover()
    names = {s.name for s in SkillRegistry._skills}
    print(f"[5] Skills: {sorted(names)}")
    for required in ("time", "date", "joke", "timer", "weather", "document_creator", "document_reader"):
        assert required in names, f"missing skill: {required}"

def main():
    test_imports()
    test_brain_endpoint()
    test_memory_roundtrip()
    test_skill_discovery()
    if "--online" in sys.argv:
        test_llm_call()
    else:
        print("[3] (skipped live LLM call - pass --online to enable)")
    print("\nAll smoke tests passed")

if __name__ == "__main__":
    main()



    