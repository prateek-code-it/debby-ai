"""
DEBBY! -- core/preferences.py
Phase 8: lightweight preference detection, using the fast router model.
Runs alongside classification on every message -- if the user states a
preference ("I love jazz", "I'm vegetarian"), it gets pulled out and
saved. This is what makes "remembers my taste" actually work, instead
of just being conversation history the brain has to re-read every time.
"""

import ollama

EXTRACT_PROMPT = """Does this message state a personal preference, taste,
dietary restriction, or similar lasting fact about the user (not a
one-off question)? Examples that DO count: "I love jazz", "I'm
vegetarian", "I hate mornings", "my favorite color is blue".
Examples that DON'T count: questions, one-off requests, small talk.

If it does NOT state a preference, respond with exactly: none

If it DOES, respond in exactly this format, nothing else:
category: <short category, e.g. music_genre, diet, color>
value: <the actual preference, e.g. jazz, vegetarian, blue>

Message: "{message}"
"""


def extract_preference(message: str, router_model: str = "deepseek-r1:1.5b"):
    """Returns (category, value) tuple, or None if no preference found."""
    try:
        response = ollama.chat(
            model=router_model,
            messages=[{"role": "user", "content": EXTRACT_PROMPT.format(message=message)}],
        )
        raw = response["message"]["content"].strip()

        if "</think>" in raw:
            raw = raw.split("</think>")[-1].strip()

        if raw.lower().startswith("none") or "category" not in raw.lower():
            return None

        category, value = None, None
        for line in raw.splitlines():
            line = line.strip()
            if line.lower().startswith("category:"):
                category = line.split(":", 1)[1].strip().lower().replace(" ", "_")
            elif line.lower().startswith("value:"):
                value = line.split(":", 1)[1].strip().lower()

        if category and value:
            return (category, value)
        return None
    except Exception as e:
        print(f"[Preference extraction error, skipping: {e}]")
        return None


def format_preferences_for_prompt(preferences: list) -> str:
    """Turns stored preference rows into a short block for the system prompt."""
    if not preferences:
        return ""
    lines = [f"- {p['category']}: {p['value']}" for p in preferences[:10]]
    return "Known preferences about this user:\n" + "\n".join(lines)
