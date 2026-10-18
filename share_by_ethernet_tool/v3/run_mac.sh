#!/usr/bin/env bash
# T-Share v3 macOS Launcher
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================================"
echo "  T-Share v3: High-Speed Direct Ethernet File Transfer"
echo "========================================================"

if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 could not be found."
    exit 1
fi

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

pip install -r requirements.txt --quiet
python3 app.py
