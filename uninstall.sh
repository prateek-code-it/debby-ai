#!/bin/bash
# ============================================================
#   DEBBY! -- uninstall.sh (Modular & Interactive)
# ============================================================
set -e

BOLD='\033[1m'
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$(dirname "$REPO_DIR")"
DB_PATH="$REPO_DIR/memory/debby.db"

echo -e "${BOLD}${CYAN}=== DEBBY! Uninstall & Cleanup Tool ===${NC}\n"

# --- Option 1: Remove Python Virtual Environment ---
read -p "1. Remove Python virtual environment ($VENV_DIR)? [y/N]: " REMOVE_VENV
if [[ "$REMOVE_VENV" =~ ^[Yy]$ ]]; then
    if [ -d "$VENV_DIR/bin" ]; then
        rm -rf "$VENV_DIR/bin" "$VENV_DIR/lib" "$VENV_DIR/pyvenv.cfg" "$VENV_DIR/share" "$VENV_DIR/include" 2>/dev/null || true
        echo -e "${GREEN}✔ Virtual environment removed.${NC}"
    else
        echo -e "${YELLOW}➜ [SKIP] Virtual environment not found.${NC}"
    fi
fi

# --- Option 2: Remove All User Accounts & Preferences ---
read -p "2. Wipe all user accounts, memories, and preferences from database? [y/N]: " REMOVE_USERS
if [[ "$REMOVE_USERS" =~ ^[Yy]$ ]]; then
    if [ -f "$DB_PATH" ]; then
        python3 -c "
import sqlite3
try:
    conn = sqlite3.connect('$DB_PATH')
    cur = conn.cursor()
    cur.execute('DELETE FROM users;')
    cur.execute('DELETE FROM preferences;')
    cur.execute('DELETE FROM memories;')
    cur.execute('DELETE FROM conversations;')
    conn.commit()
    conn.close()
    print('Users, memories, and preferences wiped successfully.')
except Exception as e:
    print(f'Error clearing user data: {e}')
"
        echo -e "${GREEN}✔ All user accounts and related data purged.${NC}"
    else
        echo -e "${YELLOW}➜ [SKIP] Database file not found at $DB_PATH.${NC}"
    fi
fi

# --- Option 3: Delete Entire Database File ---
read -p "3. Delete the database file (debby.db) completely? [y/N]: " REMOVE_DB
if [[ "$REMOVE_DB" =~ ^[Yy]$ ]]; then
    if [ -f "$DB_PATH" ]; then
        rm -f "$DB_PATH"
        echo -e "${GREEN}✔ Database file $DB_PATH removed.${NC}"
    else
        echo -e "${YELLOW}➜ [SKIP] Database file not found.${NC}"
    fi
fi

# --- Option 4: Remove Ollama Models ---
read -p "4. Remove downloaded Ollama models (qwen2.5, deepseek-r1)? [y/N]: " REMOVE_MODELS
if [[ "$REMOVE_MODELS" =~ ^[Yy]$ ]]; then
    if command -v ollama >/dev/null 2>&1; then
        ollama rm qwen2.5:7b 2>/dev/null || true
        ollama rm qwen2.5-coder:7b 2>/dev/null || true
        ollama rm qwen2.5:1.5b 2>/dev/null || true
        ollama rm deepseek-r1:1.5b 2>/dev/null || true
        echo -e "${GREEN}✔ DEBBY! Ollama models removed.${NC}"
    else
        echo -e "${YELLOW}➜ [SKIP] Ollama is not installed.${NC}"
    fi
fi

echo -e "\n${BOLD}${GREEN}Cleanup complete!${NC}\n" 
