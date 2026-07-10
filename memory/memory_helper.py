"""
DEBBY! — memory/memory_helper.py
Phase 3: functions wrapping the SQLite memory database so other modules
(brain.py, future tool logic) never touch raw SQL directly.
"""

import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).resolve().parent / "debby.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets us access columns by name
    return conn


# ---------------------------------------------------------------
# Conversation history
# ---------------------------------------------------------------

def save_message(user_id: str, role: str, content: str):
    """Save one message (user or assistant) to persistent history."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO conversations (user_id, role, content) VALUES (?, ?, ?)",
        (user_id, role, content),
    )
    conn.commit()
    conn.close()


def get_recent_messages(user_id: str, limit: int = 10):
    """
    Return the last `limit` exchanges (user+assistant pairs) for this
    user, oldest first, formatted for direct use in an Ollama messages list.
    """
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT role, content FROM conversations
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (user_id, limit * 2),  # *2 because each exchange = 1 user + 1 assistant msg
    ).fetchall()
    conn.close()
    # rows come back newest-first, reverse to chronological order
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


# ---------------------------------------------------------------
# Long-term knowledge (things learned from the internet, topic-tagged)
# ---------------------------------------------------------------

def save_knowledge(topic: str, fact: str, source: str = None, user_id: str = None):
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO knowledge (topic, user_id, fact, source)
        VALUES (?, ?, ?, ?)
        """,
        (topic, user_id, fact, source),
    )
    conn.commit()
    conn.close()


def search_knowledge(topic: str, user_id: str = None):
    """
    Check what DEBBY! already knows about a topic before deciding
    whether to search the internet. Returns shared (user_id NULL)
    knowledge plus anything specific to this user.
    """
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT fact, source, created_at FROM knowledge
        WHERE topic = ? AND (user_id = ? OR user_id IS NULL)
        ORDER BY created_at DESC
        """,
        (topic, user_id),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------
# User preferences (music taste, food, etc.)
# ---------------------------------------------------------------

def save_preference(user_id: str, category: str, value: str, weight: float = 1.0):
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO preferences (user_id, category, value, weight, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id, category, value)
        DO UPDATE SET weight = weight + ?, updated_at = ?
        """,
        (user_id, category, value, weight, datetime.now(), weight, datetime.now()),
    )
    conn.commit()
    conn.close()


def register_tool(name: str, description: str, filepath: str):
    """
    Record a script DEBBY! has built for itself, so future requests
    can check 'have I already built something for this?' first.
    """
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO tools (name, description, filepath)
        VALUES (?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET description = ?, filepath = ?
        """,
        (name, description, filepath, description, filepath),
    )
    conn.commit()
    conn.close()


def list_tools():
    conn = get_connection()
    rows = conn.execute("SELECT name, description, filepath FROM tools ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_preferences(user_id: str, category: str = None):
    conn = get_connection()
    if category:
        rows = conn.execute(
            "SELECT category, value, weight FROM preferences WHERE user_id = ? AND category = ? ORDER BY weight DESC",
            (user_id, category),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT category, value, weight FROM preferences WHERE user_id = ? ORDER BY weight DESC",
            (user_id,),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------
# Authentication (users table) -- Phase 8.5
# ---------------------------------------------------------------

import hashlib


def _hash_pin(user_id: str, pin: str) -> str:
    """Simple salted hash -- adequate for a trusted home device, NOT
    bank-grade security. The user_id itself acts as the salt, which is
    enough to stop casual name-typing impersonation, which was the
    actual threat model here."""
    return hashlib.sha256(f"{user_id}:{pin}:debby_salt".encode()).hexdigest()


def create_user(user_id: str, display_name: str, pin: str, is_admin: bool = False):
    conn = get_connection()
    conn.execute(
        "INSERT INTO users (user_id, display_name, pin_hash, is_admin) VALUES (?, ?, ?, ?)",
        (user_id, display_name, _hash_pin(user_id, pin), int(is_admin)),
    )
    conn.commit()
    conn.close()


def delete_user(user_id: str):
    conn = get_connection()
    conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def list_users():
    conn = get_connection()
    rows = conn.execute("SELECT user_id, display_name, is_admin FROM users ORDER BY created_at").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def user_exists(user_id: str) -> bool:
    conn = get_connection()
    row = conn.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return row is not None


def verify_login(user_id: str, pin: str) -> bool:
    conn = get_connection()
    row = conn.execute("SELECT pin_hash FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    if row is None:
        return False
    return row["pin_hash"] == _hash_pin(user_id, pin)


def is_admin(user_id: str) -> bool:
    conn = get_connection()
    row = conn.execute("SELECT is_admin FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return bool(row and row["is_admin"])








"""
DEBBY! — memory/memory_helper.py
Phase 3: functions wrapping the SQLite memory database so other modules
(brain.py, future tool logic) never touch raw SQL directly.
""$

import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).resolve().parent / "debby.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets us access columns by name
    return conn


# ---------------------------------------------------------------
# Conversation history
# ---------------------------------------------------------------

def save_message(user_id: str, role: str, content: str):
    $""Save one message (user or assistant) to persistent history.""$
    conn = get_connection()
    conn.execute(
        "INSERT INTO conversations (user_id, role, content) VALUES (?, ?, ?)",
        (user_id, role, content),
    )
    conn.commit()
    conn.close()


def get_recent_messages(user_id: str, limit: int = 10):
    $""
    Return the last `limit` exchanges (user+assistant pairs) for this
    user, oldest first, formatted for direct use in an Ollama messages list.
    ""$
    conn = get_connection()
    rows = conn.execute(
        $""
        SELECT role, content FROM conversations
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT ?
        ""$,
        (user_id, limit * 2),  # *2 because each exchange = 1 user + 1 assistant msg
    ).fetchall()
    conn.close()
    # rows come back newest-first, reverse to chronological order
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


# ---------------------------------------------------------------
# Long-term knowledge (things learned from the internet, topic-tagged)
# ---------------------------------------------------------------

def save_knowledge(topic: str, fact: str, source: str = None, user_id: str = None):
    conn = get_connection()
    conn.execute(
        $""
        INSERT INTO knowledge (topic, user_id, fact, source)
        VALUES (?, ?, ?, ?)
        ""$,
        (topic, user_id, fact, source),
    )
    conn.commit()
    conn.close()


def search_knowledge(topic: str, user_id: str = None):
    $""
    Check what DEBBY! already knows about a topic before deciding
    whether to search the internet. Returns shared (user_id NULL)
    knowledge plus anything specific to this user.
    ""$
    conn = get_connection()
    rows = conn.execute(
        $""
        SELECT fact, source, created_at FROM knowledge
        WHERE topic = ? AND (user_id = ? OR user_id IS NULL)
        ORDER BY created_at DESC
        ""$,
        (topic, user_id),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------
# User preferences (music taste, food, etc.)
# ---------------------------------------------------------------

def save_preference(user_id: str, category: str, value: str, weight: float = 1.0):
    conn = get_connection()
    conn.execute(
        $""
        INSERT INTO preferences (user_id, category, value, weight, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id, category, value)
        DO UPDATE SET weight = weight + ?, updated_at = ?
        ""$,
        (user_id, category, value, weight, datetime.now(), weight, datetime.now()),
    )
    conn.commit()
    conn.close()


def register_tool(name: str, description: str, filepath: str):
    $""
    Record a script DEBBY! has built for itself, so future requests
    can check 'have I already built something for this?' first.
    ""$
    conn = get_connection()
    conn.execute(
        $""
        INSERT INTO tools (name, description, filepath)
        VALUES (?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET description = ?, filepath = ?
        ""$,
        (name, description, filepath, description, filepath),
    )
    conn.commit()
    conn.close()


def list_tools():
    conn = get_connection()
    rows = conn.execute("SELECT name, description, filepath FROM tools ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_preferences(user_id: str, category: str = None):
    conn = get_connection()
    if category:
        rows = conn.execute(
            "SELECT category, value, weight FROM preferences WHERE user_id = ? AND category = ? ORDER BY weight DESC",
            (user_id, category),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT category, value, weight FROM preferences WHERE user_id = ? ORDER BY weight DESC",
            (user_id,),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

"""





"""
DEBBY! — memory/memory_helper.py
Phase 3: functions wrapping the SQLite memory database so other modules
(brain.py, future tool logic) never touch raw SQL directly.


import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).resolve().parent / "debby.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets us access columns by name
    return conn


# ---------------------------------------------------------------
# Conversation history
# ---------------------------------------------------------------

def save_message(user_id: str, role: str, content: str):
    $""Save one message (user or assistant) to persistent history.""$
    conn = get_connection()
    conn.execute(
        "INSERT INTO conversations (user_id, role, content) VALUES (?, ?, ?)",
        (user_id, role, content),
    )
    conn.commit()
    conn.close()


def get_recent_messages(user_id: str, limit: int = 10):
    $""
    Return the last `limit` exchanges (user+assistant pairs) for this
    user, oldest first, formatted for direct use in an Ollama messages list.
    ""$
    conn = get_connection()
    rows = conn.execute(
        $""
        SELECT role, content FROM conversations
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT ?
        ""$,
        (user_id, limit * 2),  # *2 because each exchange = 1 user + 1 assistant msg
    ).fetchall()
    conn.close()
    # rows come back newest-first, reverse to chronological order
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


# ---------------------------------------------------------------
# Long-term knowledge (things learned from the internet, topic-tagged)
# ---------------------------------------------------------------

def save_knowledge(topic: str, fact: str, source: str = None, user_id: str = None):
    conn = get_connection()
    conn.execute(
        $""
        INSERT INTO knowledge (topic, user_id, fact, source)
        VALUES (?, ?, ?, ?)
        ""$,
        (topic, user_id, fact, source),
    )
    conn.commit()
    conn.close()


def search_knowledge(topic: str, user_id: str = None):
    $""
    Check what DEBBY! already knows about a topic before deciding
    whether to search the internet. Returns shared (user_id NULL)
    knowledge plus anything specific to this user.
    ""$
    conn = get_connection()
    rows = conn.execute(
        $""
        SELECT fact, source, created_at FROM knowledge
        WHERE topic = ? AND (user_id = ? OR user_id IS NULL)
        ORDER BY created_at DESC
        ""$,
        (topic, user_id),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------
# User preferences (music taste, food, etc.)
# ---------------------------------------------------------------

def save_preference(user_id: str, category: str, value: str, weight: float = 1.0):
    conn = get_connection()
    conn.execute(
        $""
        INSERT INTO preferences (user_id, category, value, weight, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id, category, value)
        DO UPDATE SET weight = weight + ?, updated_at = ?
        ""$,
        (user_id, category, value, weight, datetime.now(), weight, datetime.now()),
    )
    conn.commit()
    conn.close()


def get_preferences(user_id: str, category: str = None):
    conn = get_connection()
    if category:
        rows = conn.execute(
            "SELECT category, value, weight FROM preferences WHERE user_id = ? AND category = ? ORDER BY weight DESC",
            (user_id, category),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT category, value, weight FROM preferences WHERE user_id = ? ORDER BY weight DESC",
            (user_id,),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
"""
