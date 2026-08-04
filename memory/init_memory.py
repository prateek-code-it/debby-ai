import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "debby.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # 1. Users Table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            pin_hash TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Migration check for users
    cur.execute("PRAGMA table_info(users);")
    user_cols = [col[1] for col in cur.fetchall()]
    if "pin_hash" not in user_cols:
        cur.execute("ALTER TABLE users ADD COLUMN pin_hash TEXT DEFAULT '';")

    # 2. Preferences Table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            category TEXT NOT NULL,
            value TEXT NOT NULL,
            weight REAL DEFAULT 1.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    ''')

    # 3. Memories Table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            content TEXT NOT NULL,
            category TEXT DEFAULT 'general',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    ''')

    # 4. Conversations Table (uses 'content' column)
    cur.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    ''')

    # Migration check for conversations: ensure 'content' exists
    cur.execute("PRAGMA table_info(conversations);")
    conv_cols = [col[1] for col in cur.fetchall()]
    if "content" not in conv_cols and "message" in conv_cols:
        cur.execute("ALTER TABLE conversations RENAME COLUMN message TO content;")
    elif "content" not in conv_cols:
        cur.execute("ALTER TABLE conversations ADD COLUMN content TEXT DEFAULT '';")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database schema synchronized and initialized.") 
