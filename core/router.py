"""
DEBBY! -- core/router.py
Phase 4: fast classification of each user message using the small,
cheap router model (deepseek-r1:1.5b). Decides: plain chat, a coding
request, or something that needs internet access.

This keeps the expensive 7B brain model from wasting cycles on
classification -- the 1.5B model is fast enough to run on every single
message without adding noticeable delay.
"""

import ollama

VALID_CATEGORIES = {"chat", "code", "internet"}

CLASSIFY_PROMPT = """You are a request classifier. Read the user's message and
respond with EXACTLY ONE WORD, nothing else, no punctuation, no explanation:

- "code" if they want a script, program, automation, or file/OS-level task built
- "internet" if answering requires current/live information you would need to search for
- "chat" for everything else (conversation, questions you can answer from general knowledge)

User message: "{message}"

Answer with one word only:"""


def classify(message: str, router_model: str = "deepseek-r1:1.5b") -> str:
    try:
        response = ollama.chat(
            model=router_model,
            messages=[{"role": "user", "content": CLASSIFY_PROMPT.format(message=message)}],
        )
        raw = response["message"]["content"].strip().lower()

        if "</think>" in raw:
            raw = raw.split("</think>")[-1].strip()

        for category in VALID_CATEGORIES:
            if category in raw:
                return category

        return "chat"
    except Exception as e:
        print(f"[Router error, defaulting to chat: {e}]")
        return "chat"
