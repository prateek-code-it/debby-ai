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
    list_tools, delete_tool,
)
from core.router import classify_and_extract  # noqa: E402
from core.coder import build_tool  # noqa: E402
from core.search import search_web, slugify_topic  # noqa: E402
from core.logger import log_event  # noqa: E402
from core.preferences import format_preferences_for_prompt  # noqa: E402
from core.deep import deep_think  # noqa: E402
from core.voice import listen_and_transcribe, speak  # noqa: E402
from core.airllm_bridge import ask_airllm  # noqa: E402
from core.os_bridge import match_app_request, launch_app, list_authorized_apps  # noqa: E402
from core.files import read_file_content  # noqa: E402
from core.file_ops import delete_file, list_sandbox_files, read_file as read_tool_file  # noqa: E402
from core.executor import run_command, suggest_run_command  # noqa: E402
import shlex  # noqa: E402


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


def handle_file_request(raw_args: str, brain_model: str) -> str:
    """
    raw_args is everything after '/file '. Path first (quote it if it
    has spaces), then an optional question. Defaults to a summary
    if no question is given.
    """
    try:
        parts = shlex.split(raw_args)
    except ValueError as e:
        return f"Couldn't parse that -- if your path has spaces, wrap it in quotes. ({e})"

    if not parts:
        return "Usage: /file <path> [question]  -- e.g. /file ~/notes.txt what does this say about the budget?"

    filepath = parts[0]
    question = " ".join(parts[1:]).strip() or "Summarize this file."

    result = read_file_content(filepath)
    if not result["success"]:
        return result["error"]

    note = " (file was long, only the first portion was used)" if result["truncated"] else ""
    prompt = f"Here is the content of a file:\n\n{result['content']}\n\n{question}{note}"

    try:
        response = ollama.chat(model=brain_model, messages=[{"role": "user", "content": prompt}])
        return response["message"]["content"]
    except Exception as e:
        return f"Read the file fine, but couldn't get an answer from the model: {e}"


def handle_app_request(user_input: str, router_model: str) -> str:
    app_key = match_app_request(user_input, router_model=router_model)
    if not app_key:
        available = ", ".join(list_authorized_apps())
        return f"I'm not sure which app you meant. I can open: {available}"

    result = launch_app(app_key)
    if result["success"]:
        return f"Opening {app_key}."
    return f"Couldn't open {app_key}: {result['error']}"


def handle_airllm_request(question: str, config: dict) -> str:
    result = ask_airllm(question, config)
    if not result["success"]:
        return result["error"]
    return result["answer"]


def handle_deep_request(question: str, deep_model: str) -> str:
    print("[/deep -- letting deepseek-r1 think this through, may take a bit longer...]")
    result = deep_think(question, model=deep_model)
    if not result["success"]:
        return f"Deep reasoning failed: {result['error']}"
    return result["answer"]


def handle_tools_list() -> str:
    tools = list_tools()
    if not tools:
        return "No tools built yet."
    lines = [f"- {t['name']}: {t['description']}" for t in tools]
    return "Saved tools:\n" + "\n".join(lines)


def handle_run_command_request(toolname: str) -> str:
    tools = list_tools()
    match = next((t for t in tools if t["name"] == toolname), None)
    if not match:
        return f"No tool named '{toolname}'. Try /tools to see what's available."

    run_cmd = suggest_run_command(match["filepath"])
    print(f"About to run: {run_cmd}")
    answer = input("  Confirm? (Y/N): ").strip().lower()
    if answer != "y":
        return "Cancelled."

    result = run_command(run_cmd)
    if not result["success"]:
        return f"Couldn't run it: {result['error']}"
    output = result["stdout"] or "(no output)"
    if result["stderr"]:
        output += f"\n\n[stderr]\n{result['stderr']}"
    return f"Output:\n```\n{output}\n```"


def handle_edit_request(raw_args: str, coder_model: str) -> str:
    parts = raw_args.split(maxsplit=1)
    if len(parts) < 2:
        return "Usage: /edit <toolname> <what to change>"
    toolname, change_request = parts[0], parts[1]

    filename = f"{toolname}.py" if not toolname.endswith(".py") else toolname
    existing = read_tool_file(filename)
    if not existing["success"]:
        return existing["error"]

    result = build_tool(
        change_request, coder_model=coder_model,
        edit_filename=filename, existing_code=existing["content"],
    )
    if not result["success"]:
        return f"Edit failed: {result['error']}"

    return f"Updated tools/{filename}\n\n```python\n{result['code']}\n```"


def handle_delete_request(toolname: str) -> str:
    filename = f"{toolname}.py" if not toolname.endswith(".py") else toolname
    print(f"About to delete: tools/{filename}")
    answer = input("  Confirm? (Y/N): ").strip().lower()
    if answer != "y":
        return "Cancelled."

    result = delete_file(filename)
    if not result["success"]:
        return result["error"]
    delete_tool(toolname.replace(".py", ""))
    return f"Deleted tools/{filename}."


def handle_shell_request(command: str) -> str:
    print(f"About to run in tools/: {command}")
    answer = input("  This runs a raw terminal command. Confirm? (Y/N): ").strip().lower()
    if answer != "y":
        return "Cancelled."

    result = run_command(command)
    if not result["success"]:
        return f"Error: {result['error']}"
    output = result["stdout"] or "(no output)"
    if result["stderr"]:
        output += f"\n\n[stderr]\n{result['stderr']}"
    return f"Output:\n```\n{output}\n```"


def handle_code_request(user_input: str) -> str:
    print("[Router: code request -> handing off to Coder model...]")
    log_event("code", f"Building tool for: {user_input}", role="system")
    result = build_tool(user_input)
    if not result["success"]:
        return f"I tried to build that but hit an error: {result['error']}"

    register_tool(result["name"], result["description"], result["filepath"])
    reply = (
        f"Built it and saved it to tools/{result['name']}.py\n\n"
        f"```python\n{result['code']}\n```"
    )

    run_cmd = suggest_run_command(result["filepath"])
    answer = input(f"  Want me to run it now? ({run_cmd}) (Y/N): ").strip().lower()
    if answer == "y":
        print(f"[Running: {run_cmd}]")
        run_result = run_command(run_cmd)
        if run_result["success"]:
            output = run_result["stdout"] or "(no output)"
            if run_result["stderr"]:
                output += f"\n\n[stderr]\n{run_result['stderr']}"
            reply += f"\n\nOutput:\n```\n{output}\n```"
        else:
            reply += f"\n\nCouldn't run it: {run_result['error']}"

    return reply


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
    print("Type '/voice' (or '/voice 8' for 8 seconds) to speak instead of type.")
    print("Type '/file <path> [question]' to ask about a text file or PDF.")
    print("Type '/tools' to list built scripts, '/run <name>' to execute one.")
    print("Type '/edit <name> <change>' or '/delete <name>' to modify/remove a tool.")
    print("Type '/shell <command>' for raw terminal control (always asks to confirm).")
    if config.get("airllm_enabled", False):
        print("Type '/airllm <question>' to use the AirLLM model.\n")
    else:
        print("(/airllm is available but disabled -- see config.json to enable it later)\n")

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
        used_voice = False
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
            used_voice = True
            print(f"You (voice): {user_input}")

        conversation.append({"role": "user", "content": user_input})
        save_message(user_id, "user", user_input)
        log_event("chat", user_input, role="user")

        # New file-management + terminal-control commands. All
        # destructive/execution actions (run, delete, shell) require
        # explicit Y/N confirmation inside their handler functions.
        if user_input.lower() == "/tools":
            reply = handle_tools_list()
            print(f"DEBBY!: {reply}\n")
            conversation.append({"role": "assistant", "content": reply})
            save_message(user_id, "assistant", reply)
            continue

        if user_input.lower().startswith("/run "):
            reply = handle_run_command_request(user_input[len("/run "):].strip())
            print(f"DEBBY!: {reply}\n")
            conversation.append({"role": "assistant", "content": reply})
            save_message(user_id, "assistant", reply)
            log_event("run", reply, role="assistant")
            continue

        if user_input.lower().startswith("/edit "):
            reply = handle_edit_request(user_input[len("/edit "):].strip(), config["coder_model"])
            print(f"DEBBY!: {reply}\n")
            conversation.append({"role": "assistant", "content": reply})
            save_message(user_id, "assistant", reply)
            log_event("edit", reply, role="assistant")
            continue

        if user_input.lower().startswith("/delete "):
            reply = handle_delete_request(user_input[len("/delete "):].strip())
            print(f"DEBBY!: {reply}\n")
            conversation.append({"role": "assistant", "content": reply})
            save_message(user_id, "assistant", reply)
            log_event("delete", reply, role="assistant")
            continue

        if user_input.lower().startswith("/shell "):
            reply = handle_shell_request(user_input[len("/shell "):].strip())
            print(f"DEBBY!: {reply}\n")
            conversation.append({"role": "assistant", "content": reply})
            save_message(user_id, "assistant", reply)
            log_event("shell", reply, role="assistant")
            continue

        # /file bypasses the router entirely -- explicit user override.
        if user_input.lower().startswith("/file "):
            raw_args = user_input[len("/file "):].strip()
            reply = handle_file_request(raw_args, model)
            print(f"DEBBY!: {reply}\n")
            if used_voice:
                speak(reply)
            conversation.append({"role": "assistant", "content": reply})
            save_message(user_id, "assistant", reply)
            log_event("file", reply, role="assistant")
            continue

        # /airllm bypasses the router entirely -- explicit user override.
        # Disabled by default (see config.json) -- gives a clear message
        # explaining why, rather than silently failing, when off.
        if user_input.lower().startswith("/airllm "):
            question = user_input[len("/airllm "):].strip()
            reply = handle_airllm_request(question, config)
            print(f"DEBBY! [AIRLLM]: {reply}\n")
            conversation.append({"role": "assistant", "content": reply})
            save_message(user_id, "assistant", reply)
            log_event("airllm", reply, role="assistant")
            continue

        # /deep command bypasses the router entirely -- explicit user
        # override, not something the classifier should ever decide.
        if user_input.lower().startswith("/deep "):
            question = user_input[len("/deep "):].strip()
            reply = handle_deep_request(question, config["deep_model"])
            print(f"DEBBY! [DEEP]: {reply}\n")
            if used_voice:
                speak(reply)
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

        if category == "app":
            print("[Router: app request -> checking authorized apps...]")
            reply = handle_app_request(user_input, config["router_model"])
            print(f"DEBBY!: {reply}\n")
            if used_voice:
                speak(reply)
            conversation.append({"role": "assistant", "content": reply})
            save_message(user_id, "assistant", reply)
            log_event("app", reply, role="assistant")
            continue

        if category == "code":
            reply = handle_code_request(user_input)
            print(f"DEBBY!: {reply}\n")
            if used_voice:
                speak("I've built that and saved it to your tools folder.")
            conversation.append({"role": "assistant", "content": reply})
            save_message(user_id, "assistant", reply)
            log_event("code", reply, role="assistant")
            continue

        if category == "internet":
            reply = handle_internet_request(user_input, model, user_id)
            print(f"DEBBY!: {reply}\n")
            if used_voice:
                speak(reply)
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
        if used_voice:
            speak(reply)
        conversation.append({"role": "assistant", "content": reply})
        save_message(user_id, "assistant", reply)
        log_event("chat", reply, role="assistant")


if __name__ == "__main__":
    main() 
