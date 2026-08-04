import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "debby.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # 1. Create table with full schema if it doesn't exist
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            pin_hash TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 2. Check existing columns to handle migrations automatically
    cur.execute("PRAGMA table_info(users);")
    existing_columns = [column[1] for column in cur.fetchall()]
    
    # Safely add pin_hash if running on an old DB schema
    if "pin_hash" not in existing_columns:
        cur.execute("ALTER TABLE users ADD COLUMN pin_hash TEXT DEFAULT '';")
        print("Migrated schema: Added 'pin_hash' column to 'users' table.")
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialization complete.")
