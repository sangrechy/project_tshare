#!/usr/bin/env bash
# T-Share Linux Launcher
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================================"
echo "  T-Share: Unified Wire P2P & LAN Web Sharing Suite"
echo "========================================================"
echo ""

if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 could not be found."
    echo "Please install Python 3:"
    echo "  Ubuntu/Debian: sudo apt update && sudo apt install -y python3 python3-pip python3-venv"
    echo "  Fedora:        sudo dnf install -y python3 python3-pip"
    echo "  Arch Linux:    sudo pacman -S python python-pip"
    exit 1
fi

if [ ! -d "venv" ]; then
    echo "[*] Initializing virtual environment..."
    if ! python3 -m venv --system-site-packages venv 2>/dev/null; then
        python3 -m venv venv 2>/dev/null || true
    fi
fi

if [ -f "venv/pyvenv.cfg" ]; then
    sed -i 's/include-system-site-packages = false/include-system-site-packages = true/' venv/pyvenv.cfg 2>/dev/null || true
fi

if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

if ! python3 -c "import psutil" 2>/dev/null; then
    echo "[*] Installing required Python packages..."
    pip install -r requirements.txt || python3 -m pip install -r requirements.txt
fi

echo "[*] Starting T-Share Unified..."
python3 app.py "$@"
