"""
DEBBY! -- core/os_bridge.py
Phase 7: controlled launching of external applications. DEBBY! can only
ever open apps listed in config/authorized_apps.json -- this is a hard
allowlist, not a suggestion, checked before any subprocess call.

Deliberately kept standalone and NOT wired into brain.py/router.py yet.
Test this module directly first (see bottom of file / roadmap) before
connecting it to the conversation flow -- that way if something's wrong
with app-launching, you're not also debugging it through the chat loop.
"""

import json
import subprocess
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
ALLOWLIST_PATH = WORKSPACE_ROOT / "config" / "authorized_apps.json"


def _load_allowlist() -> dict:
    if not ALLOWLIST_PATH.exists():
        print(f"[OS Bridge] WARNING: allowlist not found at {ALLOWLIST_PATH}")
        return {}
    with open(ALLOWLIST_PATH, "r") as f:
        return json.load(f)


def match_app_request(user_input: str, router_model: str = "qwen2.5:1.5b") -> str:
    """
    Given a natural-language request like "open a browser" or "launch
    the terminal", figures out which authorized app (if any) matches.
    Returns the app key, or None if nothing matches -- deliberately
    returns None rather than guessing, since launch_app() already
    refuses anything not on the allowlist anyway; this is just about
    picking the right key from what the user actually meant.
    """
    import ollama

    apps = list(_load_allowlist().keys())
    if not apps:
        return None

    prompt = f"""The user said: "{user_input}"

Which of these authorized apps did they mean? {apps}

Respond with ONLY the exact app name from the list, or "none" if none match.
No explanation, just the word."""

    try:
        response = ollama.chat(
            model=router_model,
            messages=[{"role": "user", "content": prompt}],
            options={"num_predict": 20},
        )
        raw = response["message"]["content"].strip().lower().strip('"').strip("'")
        if "</think>" in raw:
            raw = raw.split("</think>")[-1].strip()
        for app in apps:
            if app.lower() in raw:
                return app
        return None
    except Exception as e:
        print(f"[App matching error: {e}]")
        return None


def list_authorized_apps() -> list:
    return list(_load_allowlist().keys())


def is_authorized(app_name: str) -> bool:
    return app_name in _load_allowlist()


def launch_app(app_name: str) -> dict:
    """
    Launch an app by its allowlist key (e.g. 'chromium', not the raw
    binary name). Refuses anything not explicitly listed -- no
    exceptions, no fuzzy matching, no "close enough" name guessing.
    """
    allowlist = _load_allowlist()

    if app_name not in allowlist:
        return {
            "success": False,
            "error": f"'{app_name}' is not in the authorized apps list. "
                     f"Authorized apps: {list(allowlist.keys())}",
        }

    command = allowlist[app_name]
    try:
        # Popen (not run) so DEBBY! doesn't hang waiting for the app to close
        subprocess.Popen(
            [command],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return {"success": True, "app": app_name, "command": command}
    except FileNotFoundError:
        return {
            "success": False,
            "error": f"'{command}' is authorized but not installed/not found on this system.",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    # Standalone test -- run this file directly:
    #   python core/os_bridge.py
    print("Authorized apps:", list_authorized_apps())
    test_app = input("Enter an app name to test-launch (or blank to skip): ").strip()
    if test_app:
        result = launch_app(test_app)
        print(result) 
