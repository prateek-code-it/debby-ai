"""
DEBBY! -- core/coder.py
Phase 4: when the router classifies a request as "code", this module
swaps in the coder model, gets a script back, saves it into the tools
sandbox, and registers it in the memory database.
"""

import re
import ollama
from pathlib import Path
from datetime import datetime

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = WORKSPACE_ROOT / "tools"

CODER_SYSTEM_PROMPT = """You are a coding specialist. Write clean, working
Python code for the user's request. Respond with a short one-line comment
describing what the script does, then the full code in a single code block.
Do not explain outside the code block -- keep any explanation as comments
inside the script itself."""


def _extract_code(response_text: str) -> str:
    """Pull the code out of a ```python ... ``` block if present, otherwise
    return the raw response (in case the model skipped the fence)."""
    match = re.search(r"```(?:python)?\s*\n(.*?)```", response_text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return response_text.strip()


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return slug[:40] or "tool"


def build_tool(request: str, coder_model: str = "qwen2.5-coder:7b",
                edit_filename: str = None, existing_code: str = None) -> dict:
    """
    Generate a script for `request`, save it to tools/, and return info
    about what was created so brain.py can report back to the user and
    register it in memory.

    If edit_filename + existing_code are provided, this is an EDIT of
    an existing tool (not a new one) -- the existing code is given as
    context, and the result overwrites the same file instead of
    creating a new timestamped one.
    """
    TOOLS_DIR.mkdir(exist_ok=True)

    if existing_code:
        user_message = (
            f"Here is the existing code:\n\n```python\n{existing_code}\n```\n\n"
            f"Modify it to: {request}\n\nReturn the FULL updated script, not just the changed part."
        )
    else:
        user_message = request

    try:
        response = ollama.chat(
            model=coder_model,
            messages=[
                {"role": "system", "content": CODER_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
        )
        raw = response["message"]["content"]
    except Exception as e:
        return {"success": False, "error": str(e)}

    code = _extract_code(raw)

    if edit_filename:
        name = edit_filename.replace(".py", "")
        filepath = TOOLS_DIR / edit_filename
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = f"{_slugify(request)}_{timestamp}"
        filepath = TOOLS_DIR / f"{name}.py"

    filepath.write_text(code)

    return {
        "success": True,
        "name": name,
        "filepath": str(filepath),
        "code": code,
        "description": request,
    } 
