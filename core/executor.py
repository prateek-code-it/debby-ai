"""
DEBBY! -- core/executor.py
Terminal command execution. This is the most dangerous capability in
DEBBY! -- unlike everything else, there's no allowlist possible for
"any shell command." The safety model here is: this module NEVER
decides to run something on its own. brain.py always shows the exact
command and gets explicit Y/N confirmation BEFORE calling run_command.

Two safety measures that ARE built in here:
- Working directory is locked to tools/ (commands operate there, not
  wherever the process happens to be)
- Hard timeout -- a hung command can't freeze the whole assistant
"""

import subprocess
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = WORKSPACE_ROOT / "tools"


def run_command(command: str, timeout: int = 30) -> dict:
    """
    Runs `command` as a shell command, cwd locked to tools/.
    NOTE: shell=True is used deliberately here so natural commands
    like "python3 script.py" or "pip install requests" work as typed
    -- but this means the confirmation step in brain.py is the ONLY
    thing standing between the user and whatever they approve. This
    is by design (you asked for real terminal control), not an
    oversight -- there's no way to have both "run arbitrary shell
    commands" and "sandbox against everything" at the same time.
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(TOOLS_DIR),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "success": True,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"Command timed out after {timeout} seconds."}
    except Exception as e:
        return {"success": False, "error": str(e)}


def suggest_run_command(filepath: str) -> str:
    """Best-effort guess at how to run a file, based on its extension."""
    ext = Path(filepath).suffix.lower()
    name = Path(filepath).name
    if ext == ".py":
        return f"python3 {name}"
    if ext == ".sh":
        return f"bash {name}"
    if ext == ".js":
        return f"node {name}"
    return f"./{name}"
