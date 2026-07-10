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
