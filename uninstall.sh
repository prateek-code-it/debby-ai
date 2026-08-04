#!/bin/bash
# ============================================================
#   DEBBY! -- uninstall.sh (Customizable & Interactive)
# ============================================================
set -e

# --- COLOR DEFINITIONS ---
BOLD='\033[1m'
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log_step() { echo -e "\n${BOLD}${CYAN}=== $1 ===${NC}"; }
log_info() { echo -e "${GREEN}✔ $1${NC}"; }
log_skip() { echo -e "${YELLOW}➜ [SKIP] $1${NC}"; }
log_warn() { echo -e "${RED}⚠ $1${NC}"; }

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$(dirname "$REPO_DIR")"

echo -e "\n${BOLD}${RED}============================================================${NC}"
echo -e "${BOLD}${RED}           DEBBY! UNINSTALLATION & CLEANUP                  ${NC}"
echo -e "${BOLD}${RED}============================================================${NC}\n"
echo -e "Choose which components you want to remove:\n"

# Helper function for yes/no prompts with one-line descriptions
ask_choice() {
    local prompt_text="$1"
    local description="$2"
    echo -e "${BOLD}$prompt_text${NC}"
    echo -e "   ${CYAN}Description:${NC} $description"
    read -p "   Remove this component? [y/N]: " choice
    case "$choice" in 
        [yY][eE][sS]|[yY]) return 0 ;;
        *) return 1 ;;
    esac
}

# --- SELECTION PROMPTS ---
echo ""
REMOVE_VENV=false
ask_choice "1. Python Virtual Environment ($VENV_DIR)" \
           "Deletes the Python virtualenv folder containing all installed pip packages." && REMOVE_VENV=true

echo ""
REMOVE_DB=false
ask_choice "2. Memory Database & User Files ($REPO_DIR/memory/debby.db)" \
           "Deletes all local SQLite databases containing chat history, facts, and user accounts." && REMOVE_DB=true

echo ""
REMOVE_MODELS=false
ask_choice "3. Ollama AI Models (Qwen & DeepSeek)" \
           "Deletes downloaded LLM model weights (qwen2.5, deepseek-r1) from local Ollama storage." && REMOVE_MODELS=true

echo ""
REMOVE_SWAP=false
ask_choice "4. Swapfile (/swapfile)" \
           "Removes the 4G system swap file and cleans its entry from /etc/fstab." && REMOVE_SWAP=false || REMOVE_SWAP=$?
# Fixed boolean logic for swap assignment
if [ "$REMOVE_SWAP" -eq 0 ]; then REMOVE_SWAP=true; else REMOVE_SWAP=false; fi

echo ""
REMOVE_X11=false
ask_choice "5. Desktop & Startup Configurations (~/.xinitrc & ~/.bash_profile)" \
           "Removes auto-startx hooks and resets the standard desktop initialization files." && REMOVE_X11=true

echo ""
REMOVE_OLLAMA_BIN=false
ask_choice "6. Ollama Service Engine" \
           "Uninstalls the Ollama binary executable and its system service entirely." && REMOVE_OLLAMA_BIN=true

# --- EXECUTION PHASE ---

log_step "[1/6] Removing Python Virtual Environment"
if [ "$REMOVE_VENV" = true ]; then
    if [ -d "$VENV_DIR/bin" ]; then
        rm -rf "$VENV_DIR/bin" "$VENV_DIR/lib" "$VENV_DIR/pyvenv.cfg" "$VENV_DIR/include"
        log_info "Python virtual environment removed."
    else
        log_skip "Virtual environment not found."
    fi
else
    log_skip "Kept Python virtual environment."
fi

log_step "[2/6] Removing Database & User Files"
if [ "$REMOVE_DB" = true ]; then
    if [ -d "$REPO_DIR/memory" ]; then
        rm -rf "$REPO_DIR/memory/*.db" "$REPO_DIR/memory/__pycache__"
        log_info "Database and memory cache files removed."
    else
        log_skip "Memory directory not found."
    fi
else
    log_skip "Kept database and user records."
fi

log_step "[3/6] Removing Downloaded Ollama Models"
if [ "$REMOVE_MODELS" = true ]; then
    if command -v ollama >/dev/null 2>&1; then
        ollama rm qwen2.5:7b 2>/dev/null || true
        ollama rm qwen2.5-coder:7b 2>/dev/null || true
        ollama rm qwen2.5:1.5b 2>/dev/null || true
        ollama rm deepseek-r1:1.5b 2>/dev/null || true
        log_info "Ollama AI models removed."
    else
        log_skip "Ollama binary not present to remove models."
    fi
else
    log_skip "Kept Ollama AI models."
fi

log_step "[4/6] Removing Swapfile"
if [ "$REMOVE_SWAP" = true ]; then
    if [ -f /swapfile ]; then
        sudo swapoff /swapfile 2>/dev/null || true
        sudo rm -f /swapfile
        sudo sed -i '\|/swapfile none swap sw 0 0|d' /etc/fstab
        log_info "Swapfile removed and fstab updated."
    else
        log_skip "No swapfile found at /swapfile."
    fi
else
    log_skip "Kept system swapfile."
fi

log_step "[5/6] Cleaning X11 & Profile Configurations"
if [ "$REMOVE_X11" = true ]; then
    if [ -f ~/.xinitrc ]; then
        rm -f ~/.xinitrc
        log_info "Removed ~/.xinitrc."
    fi
    if [ -f ~/.bash_profile ]; then
        sed -i '/exec startx/d' ~/.bash_profile
        sed -i '/if \[ -z "$DISPLAY" \] && \[ "$XDG_VTNR" -eq 1 \]; then/d' ~/.bash_profile
        log_info "Cleaned startx entries from ~/.bash_profile."
    fi
else
    log_skip "Kept desktop configs."
fi

log_step "[6/6] Removing Ollama Engine"
if [ "$REMOVE_OLLAMA_BIN" = true ]; then
    if command -v ollama >/dev/null 2>&1; then
        sudo systemctl stop ollama 2>/dev/null || true
        sudo systemctl disable ollama 2>/dev/null || true
        sudo rm -f /usr/local/bin/ollama
        sudo rm -rf /usr/share/ollama
        log_info "Ollama engine uninstalled."
    else
        log_skip "Ollama is not installed."
    fi
else
    log_skip "Kept Ollama engine."
fi

echo -e "\n${BOLD}${GREEN}============================================================${NC}"
echo -e "${BOLD}${GREEN}           UNINSTALLATION PROCESS COMPLETED                 ${NC}"
echo -e "${BOLD}${GREEN}============================================================${NC}\n"
