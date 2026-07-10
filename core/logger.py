"""
DEBBY! -- core/logger.py
Phase 6: simple JSON-lines event log. brain.py calls log_event() at key
moments; gui.py polls the same file to display live activity, without
the two processes needing to talk to each other directly.
"""

import json
from pathlib import Path
from datetime import datetime

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
LOG_PATH = WORKSPACE_ROOT / "logs" / "debby.log"


def log_event(event_type: str, content: str, role: str = None):
    """
    event_type: 'chat' | 'code' | 'internet' | 'system'
    role: 'user' | 'assistant' | None (for system-level events)
    """
    LOG_PATH.parent.mkdir(exist_ok=True)
    entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "type": event_type,
        "role": role,
        "content": content,
    }
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")
