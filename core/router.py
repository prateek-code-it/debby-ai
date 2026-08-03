"""
DEBBY! -- core/router.py
Merged version: one router-model call now does BOTH classification
AND preference extraction, instead of two separate calls. Cuts one
full model invocation off every single message.
"""

import json
import ollama

VALID_CATEGORIES = {"chat", "code", "internet", "app"}

COMBINED_PROMPT = """Analyze this message and respond with ONLY a JSON object,
nothing else, no explanation, no markdown fences:

{{
  "category": "chat" or "code" or "internet" or "app",
  "preference_category": null or a short category like "music_genre"/"diet"/"color",
  "preference_value": null or the preference value
}}

category rules:
- "code": user wants a script, program, or automation BUILT (not opened)
- "app": user wants an EXISTING application opened/launched (e.g. "open chromium", "launch a terminal")
- "internet": answering needs current/live info you'd have to search for
- "chat": everything else

preference rules: only fill preference_category/preference_value if the
message states a lasting personal preference/taste/restriction (e.g.
"I love jazz", "I'm vegetarian") -- NOT for questions or one-off requests.
Otherwise both stay null.

Message: "{message}"
"""


def classify_and_extract(message: str, router_model: str = "deepseek-r1:1.5b") -> dict:
    """
    Returns: {"category": str, "preference": (cat, val) tuple or None}
    """
    default = {"category": "chat", "preference": None}
    try:
        response = ollama.chat(
            model=router_model,
            messages=[{"role": "user", "content": COMBINED_PROMPT.format(message=message)}],
            options={"num_predict": 150},  # hard cap -- this task never needs more
        )
        raw = response["message"]["content"].strip()

        if "</think>" in raw:
            raw = raw.split("</think>")[-1].strip()

        # small models sometimes wrap JSON in markdown fences anyway -- strip if present
        if raw.startswith("```"):
            raw = raw.strip("`").replace("json", "", 1).strip()

        data = json.loads(raw)
        category = data.get("category", "chat")
        if category not in VALID_CATEGORIES:
            category = "chat"

        pref = None
        if data.get("preference_category") and data.get("preference_value"):
            pref = (
                str(data["preference_category"]).lower().replace(" ", "_"),
                str(data["preference_value"]).lower(),
            )

        return {"category": category, "preference": pref}
    except Exception as e:
        print(f"[Router error, defaulting to chat: {e}]")
        return default


# Kept for backwards compatibility with anything still calling the old API
def classify(message: str, router_model: str = "deepseek-r1:1.5b") -> str:
    return classify_and_extract(message, router_model)["category"] 
