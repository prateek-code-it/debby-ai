"""
DEBBY! — core/brain.py
Phase 2: plain terminal chat loop, no memory, no GUI, no tool-calling yet.
Just proves the Brain model responds correctly through Ollama.
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


def load_config():
    config_path = Path(__file__).resolve().parent.parent / "config" / "config.json"
    if not config_path.exists():
        print(f"ERROR: config file not found at {config_path}")
        print("Fix: make sure config.json is saved in workspace/config/")
        sys.exit(1)
    with open(config_path, "r") as f:
        return json.load(f)


def check_ollama_running(model_name):
    """Fail fast with a clear message instead of a confusing traceback."""
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
