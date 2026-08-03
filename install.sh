#!/bin/bash
# ============================================================
#  DEBBY! -- install.sh
#  Run this from INSIDE the cloned repo, as a normal user (not root).
#
#  Expected layout:
#    ~/debby_ai/          <- Python venv lives here
#    ~/debby_ai/workspace <- this repo, cloned here
#
#  If you haven't cloned yet, do this first:
#    python3 -m venv ~/debby_ai
#    cd ~/debby_ai
#    git clone <your-repo-url> workspace
#    cd workspace
#    bash install.sh
# ============================================================
set -e

echo "=== [0/8] Compatibility check ==="
if [ ! -f /etc/os-release ]; then
    echo "ERROR: Can't detect your OS. This installer only supports Debian/Ubuntu."
    exit 1
fi
source /etc/os-release
if [[ "$ID" != "debian" && "$ID_LIKE" != *"debian"* ]]; then
    echo "ERROR: DEBBY! only supports Debian-based systems (Debian, Ubuntu, etc)."
    echo "Detected: $PRETTY_NAME"
    echo "This script uses 'apt', which doesn't exist on your distro."
    echo "Arch/Fedora/etc support isn't built yet -- Debian only for now."
    exit 1
fi
echo "OS check passed: $PRETTY_NAME"

echo "=== [1/8] Sudo access ==="
if [ "$EUID" -eq 0 ]; then
    apt update && apt install -y sudo
    read -p "Enter the username to add to sudo group: " DEBBY_USER
    usermod -aG sudo "$DEBBY_USER"
    echo ">>> Now reboot, log back in as $DEBBY_USER, cd back into this repo, and re-run install.sh"
    exit 0
fi

echo "=== [2/8] Swapfile (safety net on constrained RAM) ==="
if [ ! -f /swapfile ]; then
    sudo fallocate -l 4G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
else
    echo "Swapfile already exists, skipping."
fi

echo "=== [3/8] System packages ==="
sudo apt update
sudo apt install -y \
    xinit xserver-xorg-core xserver-xorg i3-wm alacritty git curl \
    locales btop chromium xdotool build-essential dkms x11-xserver-utils \
    neovim ufw python3-pip python3-venv \
    portaudio19-dev flac libasound2-dev espeak-ng alsa-utils \
    xrdp

echo "=== [4/8] Locale ==="
sudo locale-gen en_US.UTF-8 en_IN.UTF-8
sudo update-locale LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8

echo "=== [5/8] Firewall + remote access ==="
sudo adduser xrdp ssl-cert
sudo systemctl enable xrdp
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 3389/tcp
sudo ufw --force enable

echo "=== [6/8] Ollama + models ==="
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5:7b
ollama pull qwen2.5-coder:7b
ollama pull qwen2.5:1.5b
ollama pull deepseek-r1:1.5b
# AirLLM's extra deps (torch etc) are NOT installed here -- disabled
# by default, install only if you flip airllm_enabled in config.json

echo "=== [7/8] Python venv + dependencies ==="
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$(dirname "$REPO_DIR")"

if [ ! -f "$VENV_DIR/bin/activate" ]; then
    echo "ERROR: Expected a venv at $VENV_DIR but didn't find one."
    echo "Run this first: python3 -m venv $VENV_DIR"
    exit 1
fi

source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install \
    pygame pyautogui pytest requests ollama \
    ddgs faster-whisper pyttsx3 pypdf \
    SpeechRecognition pyaudio qrcode yt-dlp oterm

echo "=== [8/8] Database + X11 config ==="
python3 "$REPO_DIR/memory/init_memory.py"

if ! grep -q "startx" ~/.bash_profile 2>/dev/null; then
cat >> ~/.bash_profile << 'EOF'
if [ -z "$DISPLAY" ] && [ "$XDG_VTNR" -eq 1 ]; then
    exec startx
fi
EOF
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

deactivate

echo ""
echo "============================================================"
echo " DEBBY! installed."
echo ""
echo " Next steps:"
echo "   source $VENV_DIR/bin/activate"
echo "   cd $REPO_DIR"
echo "   python core/admin.py     <- create your first user account"
echo "   python core/brain.py     <- start chatting"
echo "============================================================"
