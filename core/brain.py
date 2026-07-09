"""
DEBBY! -- core/brain.py
Phase 4: every message now goes through the router first. Chat stays
with the Brain model, code requests hand off to the Coder model and
get saved into the tools sandbox, and internet-requiring requests hit
a Y/N gatekeeper (actual search comes in Phase 5).
"""

import json
import sys
from pathlib import Path

try:
    import ollama
except ImportError:
    print("ERROR: 'ollama' python package not found.")
    print("Fix: activate your venv first -> source ~/debby_ai/bin/activate")
    sys.exit(1)

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

from memory.memory_helper import save_message, get_recent_messages, register_tool  # noqa: E402
from core.router import classify  # noqa: E402
from core.coder import build_tool  # noqa: E402

CURRENT_USER = "you"


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


def handle_code_request(user_input: str) -> str:
    print("[Router: code request -> handing off to Coder model...]")
    result = build_tool(user_input)
    if not result["success"]:
        return f"I tried to build that but hit an error: {result['error']}"

    register_tool(result["name"], result["description"], result["filepath"])
    return (
        f"Built it and saved it to tools/{result['name']}.py\n\n"
        f"```python\n{result['code']}\n```"
    )


def handle_internet_request(user_input: str) -> str:
    print("[Router: this needs internet access.]")
    answer = input("  DEBBY! wants to search the internet for this. Allow? (Y/N): ").strip().lower()
    if answer != "y":
        return "Okay, I won't search. I'll do my best with what I already know, but I may be out of date on this."
    # Actual search + save-to-knowledge logic lands in Phase 5.
    return "(Internet access approved, but the search function isn't built yet -- that's Phase 5. For now, here's my best answer from what I already know.)"


def main():
    config = load_config()
    model = config["brain_model"]
    system_prompt = config["system_prompt"]
    max_turns = config.get("max_context_turns", 10)

    check_ollama_running(model)

    history = get_recent_messages(CURRENT_USER, limit=max_turns)
    conversation = [{"role": "system", "content": system_prompt}] + history

    print(f"=== DEBBY! Brain (Phase 4) -- model: {model} -- user: {CURRENT_USER} ===")
    if history:
        print(f"(Loaded {len(history)} messages from memory.)")
    print("Type 'exit' or 'quit' to stop.\n")

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

        conversation.append({"role": "user", "content": user_input})
        save_message(CURRENT_USER, "user", user_input)

        category = classify(user_input, router_model=config["router_model"])

        if category == "code":
            reply = handle_code_request(user_input)
            print(f"DEBBY!: {reply}\n")
            conversation.append({"role": "assistant", "content": reply})
            save_message(CURRENT_USER, "assistant", reply)
            continue

        if category == "internet":
            note = handle_internet_request(user_input)
            # Feed the gatekeeper's note to the brain model as context so
            # its reply acknowledges the internet-access decision naturally.
            conversation.append({"role": "system", "content": note})

        trimmed = [conversation[0]] + conversation[-(max_turns * 2):]

        try:
            response = ollama.chat(model=model, messages=trimmed)
            reply = response["message"]["content"]
        except Exception as e:
            print(f"[ERROR talking to model: {e}]")
            continue

        print(f"DEBBY!: {reply}\n")
        conversation.append({"role": "assistant", "content": reply})
        save_message(CURRENT_USER, "assistant", reply)


if __name__ == "__main__":
    main()


"""
DEBBY! — core/brain.py
Phase 3: wired to the SQLite memory database. Conversations now persist
across restarts. Still no GUI, no tool-calling, no internet — those come
in later phases.


import json
import sys
from pathlib import Path

try:
    import ollama
except ImportError:
    print("ERROR: 'ollama' python package not found.")
    print("Fix: activate your venv first -> source ~/debby_ai/bin/activate")
    sys.exit(1)

# Add workspace root to path so we can import memory/memory_helper.py
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

from memory.memory_helper import save_message, get_recent_messages  # noqa: E402

# Hardcoded for now — Phase 8 (multi-user) replaces this with real
# session/user detection. Kept as a single variable so that change
# is small later, not a rewrite.
CURRENT_USER = "you"


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


def main():
    config = load_config()
    model = config["brain_model"]
    system_prompt = config["system_prompt"]
    max_turns = config.get("max_context_turns", 10)

    check_ollama_running(model)

    # Load past conversation from the database instead of starting empty.
    # This is the actual "remembers you across restarts" behavior.
    history = get_recent_messages(CURRENT_USER, limit=max_turns)
    conversation = [{"role": "system", "content": system_prompt}] + history

    print(f"=== DEBBY! Brain (Phase 3) — model: {model} — user: {CURRENT_USER} ===")
    if history:
        print(f"(Loaded {len(history)} messages from memory.)")
    print("Type 'exit' or 'quit' to stop.\n")

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

        conversation.append({"role": "user", "content": user_input})
        save_message(CURRENT_USER, "user", user_input)

        trimmed = [conversation[0]] + conversation[-(max_turns * 2):]

        try:
            response = ollama.chat(model=model, messages=trimmed)
            reply = response["message"]["content"]
        except Exception as e:
            print(f"[ERROR talking to model: {e}]")
            continue

        print(f"DEBBY!: {reply}\n")
        conversation.append({"role": "assistant", "content": reply})
        save_message(CURRENT_USER, "assistant", reply)


if __name__ == "__main__":
    main()

"""
"""
#DEBBY! — core/brain.py
#Phase 2: plain terminal chat loop, no memory, no GUI, no tool-calling yet.
#Just proves the Brain model responds correctly through Ollama.


import json
import sys
from pathlib import Path

try:
    import ollama
except ImportError:
    print("ERROR: 'ollama' python package not found.")
    print("Fix: activate your venv first -> source ~/debby_ai/bin/activate")
    sys.exit(1)


def load_config():
    config_path = Path(__file__).resolve().parent.parent / "config" / "config.json"
    if not config_path.exists():
        print(f"ERROR: config file not found at {config_path}")
        print("Fix: make sure config.json is saved in workspace/config/")
        sys.exit(1)
    with open(config_path, "r") as f:
        return json.load(f)


def check_ollama_running(model_name):
   # ""Fail fast with a clear message instead of a confusing traceback.""
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
        print("Fix: try 'ollama list' in a terminal to check the service.")
        sys.exit(1)


def main():
    config = load_config()
    model = config["brain_model"]
    system_prompt = config["system_prompt"]

    check_ollama_running(model)

    # In-memory only for now — resets every restart.
    # Phase 3 wires this to the SQLite memory database instead.
    conversation = [{"role": "system", "content": system_prompt}]

    print(f"=== DEBBY! Brain (Phase 2) — model: {model} ===")
    print("Type 'exit' or 'quit' to stop.\n")

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

        conversation.append({"role": "user", "content": user_input})

        # Keep context window bounded so the model doesn't slow down
        # or run out of context on long sessions.
        max_turns = config.get("max_context_turns", 10)
        trimmed = [conversation[0]] + conversation[-(max_turns * 2):]

        try:
            response = ollama.chat(model=model, messages=trimmed)
            reply = response["message"]["content"]
        except Exception as e:
            print(f"[ERROR talking to model: {e}]")
            continue

        print(f"DEBBY!: {reply}\n")
        conversation.append({"role": "assistant", "content": reply})


if __name__ == "__main__":
    main()
"""


