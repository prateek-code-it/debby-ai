"""
DEBBY! -- core/deep.py
On-demand deep reasoning. deepseek-r1 always "thinks" at length before
answering -- that's a feature, not a bug, but you don't want it running
on every routine message. This module is only ever called when the
user explicitly types "/deep <question>".
"""

import ollama


def deep_think(question: str, model: str = "deepseek-r1:1.5b") -> dict:
    """
    Runs the question through the reasoning model with NO token cap --
    unlike the router, here the whole point is letting it think as long
    as it needs to. Returns both the thinking trace and final answer
    separately, so brain.py can choose what to show.
    """
    try:
        response = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": question}],
        )
        raw = response["message"]["content"]
    except Exception as e:
        return {"success": False, "error": str(e)}

    thinking = ""
    answer = raw

    if "<think>" in raw and "</think>" in raw:
        thinking = raw.split("<think>")[1].split("</think>")[0].strip()
        answer = raw.split("</think>")[-1].strip()

    return {"success": True, "thinking": thinking, "answer": answer}
