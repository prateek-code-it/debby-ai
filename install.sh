#!/bin/bash
# ============================================================
#  DEBBY! -- install.sh
#  Supports Debian-based AND Arch-based systems.
#
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
#
#  NOTE ON ARCH SUPPORT: tested less thoroughly than Debian. Arch is
#  rolling-release, so package versions/names can drift over time in
#  ways Debian's stable releases don't. If something breaks here on
#  Arch specifically, check whether package names have changed.
# ============================================================
set -e

echo "=== [0/8] Detecting your OS ==="
if [ ! -f /etc/os-release ]; then
    echo "ERROR: Can't detect your OS. Supported: Debian-based or Arch-based systems."
    exit 1
fi
source /etc/os-release

DISTRO_FAMILY=""
if [[ "$ID" == "debian" || "$ID_LIKE" == *"debian"* ]]; then
    DISTRO_FAMILY="debian"
elif [[ "$ID" == "arch" || "$ID_LIKE" == *"arch"* ]]; then
    DISTRO_FAMILY="arch"
else
    echo "ERROR: Unsupported OS: $PRETTY_NAME"
    echo "DEBBY! supports Debian-based (Debian, Ubuntu) or Arch-based (Arch, Manjaro) systems only."
    exit 1
fi
echo "Detected: $PRETTY_NAME ($DISTRO_FAMILY family)"

echo "=== [1/8] Sudo access ==="
if [ "$EUID" -eq 0 ]; then
    if [ "$DISTRO_FAMILY" == "debian" ]; then
        apt update && apt install -y sudo
        read -p "Enter the username to add to sudo group: " DEBBY_USER
        usermod -aG sudo "$DEBBY_USER"
    else
        pacman -Sy --noconfirm sudo
        read -p "Enter the username to add to the wheel group: " DEBBY_USER
        usermod -aG wheel "$DEBBY_USER"
        # Enable the wheel group in sudoers -- this is the riskier step on
        # Arch. Back up sudoers first, then uncomment the wheel line.
        cp /etc/sudoers /etc/sudoers.debby_backup
        sed -i 's/^# %wheel ALL=(ALL:ALL) ALL/%wheel ALL=(ALL:ALL) ALL/' /etc/sudoers
        echo ">>> Modified /etc/sudoers to enable the wheel group."
        echo ">>> Backup saved at /etc/sudoers.debby_backup -- check this"
        echo ">>> file if anything about sudo seems wrong after rebooting."
    fi
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
if [ "$DISTRO_FAMILY" == "debian" ]; then
    sudo apt update
    sudo apt install -y \
        xinit xserver-xorg-core xserver-xorg i3-wm alacritty git curl \
        locales btop chromium xdotool build-essential dkms x11-xserver-utils \
        neovim ufw python3-pip python3-venv \
        portaudio19-dev flac libasound2-dev espeak-ng alsa-utils \
        xrdp
else
    sudo pacman -Syu --noconfirm
    sudo pacman -S --noconfirm \
        xorg-xinit xorg-server i3-wm alacritty git curl \
        btop chromium xdotool base-devel dkms xorg-xset xorg-xsetroot \
        neovim ufw python python-pip \
        portaudio flac alsa-lib espeak-ng alsa-utils \
        xrdp
fi

echo "=== [4/8] Locale ==="
if [ "$DISTRO_FAMILY" == "debian" ]; then
    sudo locale-gen en_US.UTF-8 en_IN.UTF-8
    sudo update-locale LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8
else
    sudo sed -i 's/^#en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen
    sudo sed -i 's/^#en_IN.UTF-8 UTF-8/en_IN.UTF-8 UTF-8/' /etc/locale.gen
    sudo locale-gen
    echo "LANG=en_US.UTF-8" | sudo tee /etc/locale.conf
fi

echo "=== [5/8] Firewall + remote access ==="
sudo systemctl enable xrdp
if [ "$DISTRO_FAMILY" == "debian" ]; then
    sudo adduser xrdp ssl-cert
fi
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
echo " DEBBY! installed on $PRETTY_NAME."
echo ""
echo " Next steps:"
echo "   source $VENV_DIR/bin/activate"
echo "   cd $REPO_DIR"
echo "   python core/admin.py     <- create your first user account"
echo "   python core/brain.py     <- start chatting"
echo "============================================================" 
