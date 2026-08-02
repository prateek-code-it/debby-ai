"""
DEBBY! -- core/brain.py
Phase 8: real user identification (asked at startup, not hardcoded),
and preference extraction running alongside the router on every
message. Known preferences get folded into the system prompt so the
brain naturally uses them without needing to be reminded each time.
"""

import json
import sys
import getpass
from pathlib import Path

try:
    import ollama
except ImportError:
    print("ERROR: 'ollama' python package not found.")
    print("Fix: activate your venv first -> source ~/debby_ai/bin/activate")
    sys.exit(1)

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

from memory.memory_helper import (  # noqa: E402
    save_message, get_recent_messages, register_tool,
    save_knowledge, search_knowledge,
    save_preference, get_preferences,
    verify_login, list_users,
)
from core.router import classify_and_extract  # noqa: E402
from core.coder import build_tool  # noqa: E402
from core.search import search_web, slugify_topic  # noqa: E402
from core.logger import log_event  # noqa: E402
from core.preferences import format_preferences_for_prompt  # noqa: E402
from core.deep import deep_think  # noqa: E402
from core.voice import listen_and_transcribe  # noqa: E402


def load_config():
    config_path = WORKSPACE_ROOT / "config" / "config.json"
    if not config_path.exists():
        print(f"ERROR: config file not found at {config_path}")
        sys.exit(1)
    with open(config_path, "r") as f:
        return json.load(f)


def check_ollama_running(model_name):
    try:
        models = ollama.list()
        available = [m["model"] for m in models.get("models", [])]
        if not any(model_name in m for m in available):
            print(f"ERROR: model '{model_name}' not found in Ollama.")
            print(f"Available models: {available}")
            print(f"Fix: ollama pull {model_name}")
            sys.exit(1)
    except Exception as e:
        print("ERROR: could not reach Ollama. Is it running?")
        print(f"Details: {e}")
        sys.exit(1)


def handle_deep_request(question: str, deep_model: str) -> str:
    print("[/deep -- letting deepseek-r1 think this through, may take a bit longer...]")
    result = deep_think(question, model=deep_model)
    if not result["success"]:
        return f"Deep reasoning failed: {result['error']}"
    return result["answer"]


def handle_code_request(user_input: str) -> str:
    print("[Router: code request -> handing off to Coder model...]")
    log_event("code", f"Building tool for: {user_input}", role="system")
    result = build_tool(user_input)
    if not result["success"]:
        return f"I tried to build that but hit an error: {result['error']}"

    register_tool(result["name"], result["description"], result["filepath"])
    return (
        f"Built it and saved it to tools/{result['name']}.py\n\n"
        f"```python\n{result['code']}\n```"
    )


def handle_internet_request(user_input: str, brain_model: str, user_id: str) -> str:
    topic = slugify_topic(user_input)

    cached = search_knowledge(topic, user_id=user_id)
    if cached:
        print(f"[Found existing knowledge on '{topic}' -- answering offline, no search needed.]")
        facts = "\n".join(f"- {c['fact']}" for c in cached[:3])
        return f"From what I already know about this:\n{facts}"

    print(f"[Router: this needs internet access. No stored knowledge found for '{topic}'.]")
    answer = input("  DEBBY! wants to search the internet for this. Allow? (Y/N): ").strip().lower()
    if answer != "y":
        return "Okay, I won't search. I'll do my best with what I already know, but I may be out of date on this."

    print("[Searching...]")
    log_event("internet", f"Searching: {user_input}", role="system")
    results = search_web(user_input, max_results=3)
    if not results:
        return "I tried to search but didn't get any usable results. My apologies."

    snippet_text = "\n\n".join(f"{r['title']}: {r['snippet']} (source: {r['url']})" for r in results)
    synth_prompt = (
        f"Based on these search results, answer the question concisely in 2-4 sentences:\n\n"
        f"Question: {user_input}\n\nSearch results:\n{snippet_text}"
    )
    try:
        synth = ollama.chat(model=brain_model, messages=[{"role": "user", "content": synth_prompt}])
        summary = synth["message"]["content"].strip()
    except Exception as e:
        return f"Found search results but couldn't summarize them: {e}"

    sources = ", ".join(r["url"] for r in results)
    save_knowledge(topic, summary, source=sources, user_id=user_id)
    print(f"[Saved to knowledge base under topic '{topic}' for future offline use.]")

    return summary


def get_user_id() -> str:
    """
    Real authentication: name + PIN, checked against the users table.
    brain.py can only log people INTO existing accounts -- it has no
    ability to create new ones. Run core/admin.py to add/remove users.
    """
    users = list_users()
    if not users:
        print("No user accounts exist yet.")
        print("Run this first: python core/admin.py")
        sys.exit(1)

    for attempt in range(3):
        user_id = input("Username: ").strip().lower().replace(" ", "_")
        pin = getpass.getpass("PIN: ").strip()
        if verify_login(user_id, pin):
            return user_id
        print(f"Login failed. ({2 - attempt} attempts left)\n")

    print("Too many failed attempts. Exiting.")
    sys.exit(1)


def main():
    config = load_config()
    model = config["brain_model"]
    base_system_prompt = config["system_prompt"]
    max_turns = config.get("max_context_turns", 10)

    check_ollama_running(model)

    user_id = get_user_id()

    # Fold known preferences into the system prompt so the brain uses
    # them naturally, without brain.py having to inject reminders
    # into every single message.
    prefs = get_preferences(user_id)
    pref_block = format_preferences_for_prompt(prefs)
    system_prompt = base_system_prompt
    if pref_block:
        system_prompt += "\n\n" + pref_block

    history = get_recent_messages(user_id, limit=max_turns)
    conversation = [{"role": "system", "content": system_prompt}] + history

    print(f"\n=== DEBBY! Brain (Phase 8) -- model: {model} -- user: {user_id} ===")
    if history:
        print(f"(Loaded {len(history)} messages from memory.)")
    if prefs:
        print(f"(Recalled {len(prefs)} known preferences about you.)")
    print("Type 'exit' or 'quit' to stop.")
    print("Type '/deep <question>' for slower, deeper reasoning on hard questions.")
    print("Type '/voice' (or '/voice 8' for 8 seconds) to speak instead of type.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nShutting down.")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            print("Shutting down.")
            break

        # /voice records from the mic and transcribes offline, then the
        # transcribed text flows into the SAME pipeline as typed input
        # (router, /deep, memory, etc.) -- no special-casing downstream.
        if user_input.lower().startswith("/voice"):
            parts = user_input.split()
            duration = config.get("voice_duration", 5)
            if len(parts) > 1 and parts[1].isdigit():
                duration = int(parts[1])

            print(f"[Listening for {duration} seconds... speak now]")
            result = listen_and_transcribe(duration=duration, model_size=config["voice_model"])
            if not result["success"]:
                print(f"[Voice error: {result['error']}]\n")
                continue

            user_input = result["text"]
            print(f"You (voice): {user_input}")

        conversation.append({"role": "user", "content": user_input})
        save_message(user_id, "user", user_input)
        log_event("chat", user_input, role="user")

        # /deep command bypasses the router entirely -- explicit user
        # override, not something the classifier should ever decide.
        if user_input.lower().startswith("/deep "):
            question = user_input[len("/deep "):].strip()
            reply = handle_deep_request(question, config["deep_model"])
            print(f"DEBBY! [DEEP]: {reply}\n")
            conversation.append({"role": "assistant", "content": reply})
            save_message(user_id, "assistant", reply)
            log_event("deep", reply, role="assistant")
            continue

        # ONE router call now does both classification and preference
        # detection -- was two separate model calls before.
        result = classify_and_extract(user_input, router_model=config["router_model"])
        category = result["category"]
        if result["preference"]:
            pref_category, pref_value = result["preference"]
            save_preference(user_id, pref_category, pref_value)
            print(f"[Noted preference: {pref_category} = {pref_value}]")

        if category == "code":
            reply = handle_code_request(user_input)
            print(f"DEBBY!: {reply}\n")
            conversation.append({"role": "assistant", "content": reply})
            save_message(user_id, "assistant", reply)
            log_event("code", reply, role="assistant")
            continue

        if category == "internet":
            reply = handle_internet_request(user_input, model, user_id)
            print(f"DEBBY!: {reply}\n")
            conversation.append({"role": "assistant", "content": reply})
            save_message(user_id, "assistant", reply)
            log_event("internet", reply, role="assistant")
            continue

        trimmed = [conversation[0]] + conversation[-(max_turns * 2):]

        try:
            response = ollama.chat(model=model, messages=trimmed)
            reply = response["message"]["content"]
        except Exception as e:
            print(f"[ERROR talking to model: {e}]")
            continue

        print(f"DEBBY!: {reply}\n")
        conversation.append({"role": "assistant", "content": reply})
        save_message(user_id, "assistant", reply)
        log_event("chat", reply, role="assistant")


if __name__ == "__main__":
    main()
 
