"""
DEBBY! -- core/file_ops.py
File create/edit/delete/list, strictly sandboxed to the tools/
directory. This is the safety boundary: no matter what DEBBY! is
asked to do, these functions physically cannot touch anything outside
tools/ -- paths are resolved and checked before every operation.
"""

from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = WORKSPACE_ROOT / "tools"
TOOLS_DIR.mkdir(exist_ok=True)


def _safe_path(filename: str) -> Path:
    """
    Resolves filename to an absolute path INSIDE tools/, refusing
    anything that would escape the sandbox (e.g. '../../etc/passwd').
    Raises ValueError rather than silently doing something dangerous.
    """
    candidate = (TOOLS_DIR / filename).resolve()
    if not str(candidate).startswith(str(TOOLS_DIR.resolve())):
        raise ValueError(f"Refused: '{filename}' would escape the tools/ sandbox.")
    return candidate


def create_file(filename: str, content: str) -> dict:
    try:
        path = _safe_path(filename)
        path.write_text(content)
        return {"success": True, "filepath": str(path)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def edit_file(filename: str, new_content: str) -> dict:
    try:
        path = _safe_path(filename)
        if not path.exists():
            return {"success": False, "error": f"'{filename}' doesn't exist in tools/."}
        path.write_text(new_content)
        return {"success": True, "filepath": str(path)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def delete_file(filename: str) -> dict:
    try:
        path = _safe_path(filename)
        if not path.exists():
            return {"success": False, "error": f"'{filename}' doesn't exist in tools/."}
        path.unlink()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


def read_file(filename: str) -> dict:
    try:
        path = _safe_path(filename)
        if not path.exists():
            return {"success": False, "error": f"'{filename}' doesn't exist in tools/."}
        return {"success": True, "content": path.read_text()}
    except Exception as e:
        return {"success": False, "error": str(e)}


def list_sandbox_files() -> list:
    return [f.name for f in TOOLS_DIR.iterdir() if f.is_file()]
