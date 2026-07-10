"""
DEBBY! -- one-time migration: adds the 'users' table for real
authentication (name + PIN), replacing the free-text name login.
Safe to run even if the table already exists (CREATE TABLE IF NOT EXISTS).
"""

import sqlite3
from pathlib import Path

DB_PATH = Path.home() / "debby_ai" / "workspace" / "memory" / "debby.db"


def migrate():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            pin_hash TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
    print(f"'users' table ready in {DB_PATH}")


if __name__ == "__main__":
    migrate()
