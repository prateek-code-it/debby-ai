"""
DEBBY! -- core/search.py
Phase 5: actual internet search, only ever called after the Y/N
gatekeeper approves it. Also handles turning a free-text question into
a consistent topic tag, so the same subject can be looked up in the
knowledge table later without searching again.
"""

import re

STOPWORDS = {
    "what", "is", "the", "a", "an", "of", "in", "on", "for", "to", "and",
    "are", "how", "do", "does", "today", "current", "right", "now", "me",
    "tell", "about", "can", "you", "please", "will", "was", "were",
}


def slugify_topic(text: str, max_words: int = 5) -> str:
    """
    Turn a free-text question into a short, consistent topic key.
    e.g. "what's the weather in Chennai today" -> "weather_chennai"
    This is intentionally simple -- good enough to catch repeat
    questions on the same subject, not perfect NLP.
    """
    words = re.findall(r"[a-zA-Z0-9]+", text.lower())
    keywords = [w for w in words if w not in STOPWORDS]
    return "_".join(keywords[:max_words]) or "general"


def search_web(query: str, max_results: int = 3) -> list:
    """Returns a list of {title, snippet, url} dicts, or [] on failure."""
    try:
        from ddgs import DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS  # older package name, fallback
        except ImportError:
            print("[Search error: 'ddgs' not installed. Run: pip install ddgs]")
            return []

    results = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "snippet": r.get("body", ""),
                    "url": r.get("href", ""),
                })
    except Exception as e:
        print(f"[Search error: {e}]")
        return []

    return results

