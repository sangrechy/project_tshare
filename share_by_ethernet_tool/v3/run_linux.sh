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
    echo "Please install Python 3 (e.g. sudo apt install python3 python3-pip python3-venv)"
    exit 1
fi

# Set up virtualenv
if [ ! -d "venv" ]; then
    echo "[*] Creating virtual environment..."
    python3 -m venv venv || python3 -m venv --without-pip venv
fi

if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# Verify dependencies
if ! python3 -c "import webview, psutil" 2>/dev/null; then
    echo "[*] Installing required packages..."
    pip install -r requirements.txt
fi

echo "[*] Starting T-Share v3..."
python3 app.py
