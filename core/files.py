"""
DEBBY! -- core/files.py
Media/file handling, text-based to start. Reads a file's content so
the brain model can answer questions about it. Only triggered via the
explicit "/file <path> <question>" command -- DEBBY! never reads
files on its own initiative.
"""

from pathlib import Path

TEXT_EXTENSIONS = {".txt", ".md", ".py", ".json", ".csv", ".log", ".yaml", ".yml", ".xml", ".html"}
PDF_EXTENSIONS = {".pdf"}

MAX_CHARS = 6000  # keeps content well within the brain model's context window


def read_file_content(filepath: str) -> dict:
    """
    Returns: {"success": bool, "content": str, "truncated": bool} or
              {"success": False, "error": str}
    """
    path = Path(filepath).expanduser()

    if not path.exists():
        return {"success": False, "error": f"File not found: {filepath}"}
    if not path.is_file():
        return {"success": False, "error": f"Not a file: {filepath}"}

    ext = path.suffix.lower()

    if ext in TEXT_EXTENSIONS:
        try:
            text = path.read_text(errors="replace")
        except Exception as e:
            return {"success": False, "error": f"Couldn't read file: {e}"}

    elif ext in PDF_EXTENSIONS:
        try:
            from pypdf import PdfReader
        except ImportError:
            return {"success": False, "error": "Run: pip install pypdf"}
        try:
            reader = PdfReader(str(path))
            pages = []
            for page in reader.pages:
                pages.append(page.extract_text() or "")
                if sum(len(p) for p in pages) > MAX_CHARS:
                    break
            text = "\n".join(pages)
        except Exception as e:
            return {"success": False, "error": f"Couldn't read PDF: {e}"}

    else:
        supported = ", ".join(sorted(TEXT_EXTENSIONS | PDF_EXTENSIONS))
        return {
            "success": False,
            "error": f"Unsupported file type '{ext}'. Supported: {supported}",
        }

    truncated = len(text) > MAX_CHARS
    if truncated:
        text = text[:MAX_CHARS]

    return {"success": True, "content": text, "truncated": truncated}
