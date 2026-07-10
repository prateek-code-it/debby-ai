#!/bin/bash
# ============================================================
#  DEBBY! OS — Consolidated Setup Script
#  Target: Debian (CLI, no GUI) — 6GB RAM / 80GB storage
#  Run this as the normal user (NOT as root), it will sudo
#  where needed. Assumes you already installed base Debian
#  and created a non-root user during install.
# ============================================================
set -e   # stop on first error — don't silently continue on a failed step

echo "=== [1/9] Base sudo + user setup ==="
# NOTE: if you are still logged in as root for this first block, run it as root.
# If you're already a sudo-capable user, skip straight to step 2.
if [ "$EUID" -eq 0 ]; then
    apt update && apt install -y sudo
    read -p "Enter the username to add to sudo group: " DEBBY_USER
    usermod -aG sudo "$DEBBY_USER"
    echo ">>> Now reboot, log back in as $DEBBY_USER, and re-run this script."
    exit 0
fi

echo "=== [2/9] Swap file (insurance against OOM on 6GB RAM) ==="
if [ ! -f /swapfile ]; then
    sudo fallocate -l 4G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
else
    echo "Swapfile already exists, skipping."
fi

echo "=== [3/9] Core packages: X11, i3, terminal, tools ==="
sudo apt update
sudo apt install -y xinit xserver-xorg-core xserver-xorg i3-wm alacritty \
    git curl locales btop chromium xdotool build-essential dkms \
    x11-xserver-utils neovim ufw python3-pip python3-venv

echo "=== [4/9] Audio deps (for speech input, if used) ==="
sudo apt install -y portaudio19-dev flac libasound2-dev

echo "=== [5/9] Remote access layer (xrdp) — lets other devices on wifi connect ==="
# xrdp lets you RDP into this box from any phone/laptop on the same wifi.
# Windows: built-in Remote Desktop app. Mac/Linux/Android/iOS: Microsoft
# Remote Desktop app (free). This gives remote *control*, one active
# session at a time — matches "own display, but reachable over wifi."
sudo apt install -y xrdp
sudo adduser xrdp ssl-cert
echo "startdebby" | sudo tee /etc/xrdp/startwm-user 2>/dev/null || true
sudo systemctl enable xrdp

echo "=== [6/9] Locale setup ==="
sudo locale-gen en_US.UTF-8 en_IN.UTF-8
sudo update-locale LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8

echo "=== [7/9] Firewall (default deny inbound, allow outbound + RDP) ==="
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 3389/tcp    # xrdp port — needed for wifi remote access
sudo ufw --force enable

echo "=== [8/9] Ollama + models (SIZED FOR 6GB RAM — see note) ==="
# IMPORTANT: 8B models need ~5-6GB RAM each just to load — that leaves
# nothing for Pygame/X11/OS overhead, and makes hot-swapping between
# router and engineer models impossible without heavy disk thrashing.
# Using 1.5B variants to match the actual architecture doc.
curl -fsSL https://ollama.com/install.sh | sh
ollama pull deepseek-r1:1.5b
ollama pull qwen2.5-coder:1.5b
# If you later add RAM (e.g. 16GB+ mini PC), you can upgrade to:
#   ollama pull deepseek-r1:8b
#   ollama pull qwen2.5-coder:7b

echo "=== [9/9] Python virtual environment + libraries ==="
python3 -m venv ~/debby_ai
source ~/debby_ai/bin/activate
pip install --upgrade pip
pip install oterm pyautogui pygame pytest yt-dlp qrcode SpeechRecognition \
    pyaudio requests ollama ddgs
# NOTE: tensorflow dropped — nothing in the DEBBY! architecture uses it.
# Ollama handles all local inference. Add it back only if you build a
# specific offline audio/vision classifier that needs it.
deactivate

echo "=== Workspace + shell config ==="
mkdir -p ~/debby_ai/workspace/tools

# Auto-start X on tty1 login
if ! grep -q "startx" ~/.bash_profile 2>/dev/null; then
cat >> ~/.bash_profile << 'EOF'
if [ -z "$DISPLAY" ] && [ "$XDG_VTNR" -eq 1 ]; then
    exec startx
fi
EOF
fi

# .xinitrc — window manager launch config
cat > ~/.xinitrc << 'EOF'
#!/bin/sh
xset r rate 250 40
xset s off
xset -dpms
xsetroot -solid "#04104a"
exec i3
EOF
chmod +x ~/.xinitrc

echo ""
echo "============================================================"
echo " Setup complete. Next steps:"
echo " 1. Reboot: sudo reboot"
echo " 2. On first i3 launch: Enter to accept default config,"
echo "    choose Alt as Mod key."
echo " 3. To test remote access: from another device on the same"
echo "    wifi, open Microsoft Remote Desktop and connect to this"
echo "    machine's local IP (find it with: ip a)."
echo "============================================================"
