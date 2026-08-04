#!/bin/bash
# ============================================================
#   DEBBY! -- install.sh (Universal Linux, Auto-Venv, Idempotent)
#   Supports: Debian/Ubuntu, Arch/Manjaro, Fedora/RHEL, openSUSE
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
log_err()  { echo -e "${RED}✘ ERROR: $1${NC}"; }

# Detect workspace directory and target venv path
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$(dirname "$REPO_DIR")"

log_step "[0/8] Detecting OS & Package Manager"
if [ ! -f /etc/os-release ]; then
    log_err "Cannot detect your OS using /etc/os-release."
    exit 1
fi
source /etc/os-release

DISTRO_FAMILY=""
if [[ "$ID" == "debian" || "$ID_LIKE" == *"debian"* || "$ID_LIKE" == *"ubuntu"* ]]; then
    DISTRO_FAMILY="debian"
elif [[ "$ID" == "arch" || "$ID_LIKE" == *"arch"* ]]; then
    DISTRO_FAMILY="arch"
elif [[ "$ID" == "fedora" || "$ID_LIKE" == *"fedora"* || "$ID_LIKE" == *"rhel"* ]]; then
    DISTRO_FAMILY="fedora"
elif [[ "$ID" == "opensuse"* || "$ID_LIKE" == *"suse"* ]]; then
    DISTRO_FAMILY="suse"
else
    log_err "Unsupported OS: $PRETTY_NAME"
    echo "DEBBY! currently supports Debian/Ubuntu, Arch, Fedora, and openSUSE based systems."
    exit 1
fi
log_info "Detected OS: $PRETTY_NAME ($DISTRO_FAMILY family)"


log_step "[1/8] Sudo Access Check"
if [ "$EUID" -eq 0 ]; then
    read -p "Enter the normal username to add to sudo group: " DEBBY_USER
    if [ -z "$DEBBY_USER" ]; then
        log_err "Username cannot be empty."
        exit 1
    fi

    case "$DISTRO_FAMILY" in
        debian)
            apt update && apt install -y sudo
            usermod -aG sudo "$DEBBY_USER"
            ;;
        arch)
            pacman -Sy --noconfirm sudo
            usermod -aG wheel "$DEBBY_USER"
            if ! grep -q "^%wheel ALL=(ALL:ALL) ALL" /etc/sudoers; then
                cp /etc/sudoers /etc/sudoers.debby_backup
                sed -i 's/^# %wheel ALL=(ALL:ALL) ALL/%wheel ALL=(ALL:ALL) ALL/' /etc/sudoers
                log_info "Enabled wheel group in /etc/sudoers"
            fi
            ;;
        fedora|suse)
            usermod -aG wheel "$DEBBY_USER"
            ;;
    esac

    log_info "User '$DEBBY_USER' configured. Please log back in as '$DEBBY_USER' and rerun this script."
    exit 0
else
    log_skip "Running as non-root user '$(whoami)'. Proceeding..."
fi


log_step "[2/8] Swapfile Configuration"
if [ -f /swapfile ]; then
    log_skip "Swapfile already exists at /swapfile."
else
    log_info "Creating 4G swapfile..."
    sudo fallocate -l 4G /swapfile || sudo dd if=/dev/zero of=/swapfile bs=1M count=4096
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    
    if ! grep -q "/swapfile" /etc/fstab; then
        echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    fi
    log_info "Swapfile configured successfully."
fi


log_step "[3/8] System Packages"
log_info "Installing core dependencies for $DISTRO_FAMILY..."
case "$DISTRO_FAMILY" in
    debian)
        sudo apt update
        sudo apt install -y \
            xinit xserver-xorg-core xserver-xorg i3-wm alacritty git curl \
            locales btop chromium xdotool build-essential dkms x11-xserver-utils \
            neovim ufw python3-pip python3-venv python3-dev \
            portaudio19-dev flac libasound2-dev espeak-ng alsa-utils \
            xrdp
        ;;
    arch)
        sudo pacman -Syu --noconfirm
        sudo pacman -S --needed --noconfirm \
            xorg-xinit xorg-server i3-wm alacritty git curl \
            btop chromium xdotool base-devel dkms xorg-xset xorg-xsetroot \
            neovim ufw python python-pip \
            portaudio flac alsa-lib espeak-ng alsa-utils \
            xrdp
        ;;
    fedora)
        sudo dnf check-update || true
        sudo dnf install -y \
            xorg-x11-xinit xorg-x11-server-Xorg i3 alacritty git curl \
            btop chromium xdotool gcc gcc-c++ make dkms xorg-x11-server-utils \
            neovim ufw python3 python3-pip python3-devel \
            portaudio-devel flac-devel alsa-lib-devel espeak-ng alsa-utils \
            xrdp
        ;;
    suse)
        sudo zypper refresh
        sudo zypper install -y \
            xinit xorg-x11-server i3 alacritty git curl \
            btop chromium xdotool pattern:devel_basis dkms \
            neovim ufw python3 python3-pip python3-devel \
            portaudio-devel flac-devel libasound2 espeak-ng alsa-utils \
            xrdp
        ;;
esac
log_info "System package installation completed."


log_step "[4/8] Locale Setup"
if [ "$DISTRO_FAMILY" == "debian" ]; then
    sudo locale-gen en_US.UTF-8 || true
    sudo update-locale LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8 || true
elif [ "$DISTRO_FAMILY" == "arch" ]; then
    sudo sed -i 's/^#en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen
    sudo locale-gen
    echo "LANG=en_US.UTF-8" | sudo tee /etc/locale.conf >/dev/null
else
    sudo localectl set-locale LANG=en_US.UTF-8 || true
fi
log_info "Locale configured."


log_step "[5/8] Firewall & XRDP Remote Access"
sudo systemctl enable --now xrdp || true

if [ "$DISTRO_FAMILY" == "debian" ]; then
    if id -nG xrdp 2>/dev/null | grep -qw "ssl-cert"; then
        log_skip "User 'xrdp' is already in 'ssl-cert' group."
    else
        sudo adduser xrdp ssl-cert || true
    fi
fi

if sudo ufw status | grep -q "Status: active"; then
    log_skip "UFW Firewall is already active."
else
    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    sudo ufw allow 3389/tcp
    sudo ufw --force enable || true
    log_info "UFW Firewall configured and enabled."
fi


log_step "[6/8] Ollama Engine & AI Models"
if command -v ollama >/dev/null 2>&1; then
    log_skip "Ollama binary found."
else
    log_info "Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
fi

pull_model_if_missing() {
    local model=$1
    if ollama list 2>/dev/null | grep -q "${model%%:*}"; then
        log_skip "Ollama model '$model' already downloaded."
    else
        log_info "Pulling model '$model'..."
        ollama pull "$model"
    fi
}

pull_model_if_missing "qwen2.5:7b"
pull_model_if_missing "qwen2.5-coder:7b"
pull_model_if_missing "qwen2.5:1.5b"
pull_model_if_missing "deepseek-r1:1.5b"


log_step "[7/8] Python Virtual Environment & Pip Dependencies"
# --- AUTO CREATION OF VENV ---
if [ ! -d "$VENV_DIR/bin" ] || [ ! -f "$VENV_DIR/bin/activate" ]; then
    log_info "No venv detected at '$VENV_DIR'. Creating Python venv automatically..."
    python3 -m venv "$VENV_DIR"
    log_info "Virtualenv created at '$VENV_DIR'."
else
    log_skip "Python venv found at '$VENV_DIR'."
fi

source "$VENV_DIR/bin/activate"
log_info "Upgrading pip..."
pip install --upgrade pip

log_info "Installing required Python packages..."
# Fixed package name 'ddgs' -> 'duckduckgo_search'
pip install \
    pygame pyautogui pytest requests ollama \
    duckduckgo_search faster-whisper pyttsx3 pypdf \
    SpeechRecognition pyaudio qrcode yt-dlp oterm

log_info "Python dependencies installed successfully."


log_step "[8/8] Memory Initialization, User Setup & X11 Config"

# Step A: Always ensure database schema is initialized FIRST
if [ -f "$REPO_DIR/memory/init_memory.py" ]; then
    "$VENV_DIR/bin/python3" "$REPO_DIR/memory/init_memory.py"
    log_info "Memory database schema initialized."
fi

# Step B: Check for existing users safely
EXISTING_USERS=""
if [ -f "$REPO_DIR/memory/debby.db" ]; then
    EXISTING_USERS=$("$VENV_DIR/bin/python3" -c "
import sqlite3
try:
    conn = sqlite3.connect('$REPO_DIR/memory/debby.db')
    cur = conn.cursor()
    cur.execute('SELECT display_name FROM users;')
    users = [str(row[0]) for row in cur.fetchall()]
    print(', '.join(users))
    conn.close()
except Exception:
    print('')
" 2>/dev/null || true)
fi

# Step C: Prompt to create the first admin user ONLY if table is empty
if [ -n "$EXISTING_USERS" ]; then
    log_skip "Existing user(s) detected: ${BOLD}$EXISTING_USERS${NC}"
else
    if [ -f "$REPO_DIR/core/admin.py" ]; then
        echo -e "\n${BOLD}${CYAN}--- Creating First Admin User Account ---${NC}"
        "$VENV_DIR/bin/python3" "$REPO_DIR/core/admin.py" || true
    fi
fi

# 4. Configure ~/.bash_profile and ~/.xinitrc
if ! grep -q "exec startx" ~/.bash_profile 2>/dev/null; then
    cat >> ~/.bash_profile << 'EOF'

if [ -z "$DISPLAY" ] && [ "$XDG_VTNR" -eq 1 ]; then
    exec startx
fi
EOF
    log_info "Added startx hook to ~/.bash_profile"
else
    log_skip "startx hook already in ~/.bash_profile."
fi

cat > ~/.xinitrc << 'EOF'
#!/bin/sh
xset r rate 250 40
xset s off
xset -dpms
xsetroot -solid "#04104a"
exec i3
EOF
chmod +x ~/.xinitrc
log_info "Configured ~/.xinitrc"

deactivate

echo -e "\n${BOLD}${GREEN}============================================================${NC}"
echo -e "${BOLD}${GREEN}  DEBBY! check/installation completed on $PRETTY_NAME.${NC}"
echo -e "${BOLD}${GREEN}============================================================${NC}\n"
echo -e " ${BOLD}User Accounts:${NC}"
if [ -n "$EXISTING_USERS" ]; then
    echo -e "   • Registered User(s): ${GREEN}${BOLD}$EXISTING_USERS${NC}"
else
    echo -e "   • Registered User(s): ${YELLOW}No users found (Run admin.py to create one)${NC}"
fi
echo -e "   • Add more users anytime: ${CYAN}python core/admin.py${NC}"
echo -e ""
echo -e " ${BOLD}To launch DEBBY!:${NC}"
echo -e "   1. ${CYAN}source $VENV_DIR/bin/activate${NC}"
echo -e "   2. ${CYAN}cd $REPO_DIR${NC}"
echo -e "   3. ${CYAN}python core/brain.py${NC}"
echo -e "============================================================\n"
