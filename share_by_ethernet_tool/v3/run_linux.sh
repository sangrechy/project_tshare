#!/usr/bin/env bash
# T-Share v3 Linux Launcher
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================================"
echo "  T-Share v3: High-Speed Direct Ethernet File Transfer"
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

# Set up virtual environment if needed
if [ ! -d "venv" ]; then
    echo "[*] Initializing virtual environment..."
    if ! python3 -m venv venv 2>/dev/null; then
        echo "[WARNING] python3-venv package might be missing."
        echo "Please install it: sudo apt install -y python3-venv"
        python3 -m venv --without-pip venv 2>/dev/null || true
    fi
fi

if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# Verify dependencies
if ! python3 -c "import webview, psutil" 2>/dev/null; then
    echo "[*] Installing required Python packages..."
    pip install -r requirements.txt || python3 -m pip install -r requirements.txt
fi

# Check for Linux GUI WebKit backend
if ! python3 -c "import gi; gi.require_version('WebKit2', '4.1')" 2>/dev/null && \
   ! python3 -c "import gi; gi.require_version('WebKit2', '4.0')" 2>/dev/null && \
   ! python3 -c "from PyQt5 import QtWebEngineWidgets" 2>/dev/null && \
   ! python3 -c "from PyQt6 import QtWebEngineWidgets" 2>/dev/null; then
    echo "[INFO] If GUI does not open, install WebKit2GTK runtime:"
    echo "  Ubuntu/Debian: sudo apt install -y python3-gi gir1.2-webkit2-4.1"
    echo "  Fedora:        sudo dnf install -y python3-gobject webkit2gtk4.1"
    echo "  Arch Linux:    sudo pacman -S python-gobject webkit2gtk-4.1"
    echo ""
fi

echo "[*] Starting T-Share v3..."
python3 app.py
