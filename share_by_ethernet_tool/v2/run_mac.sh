#!/usr/bin/env bash
# ==============================================================================
# ⚡ T-Share v2 • macOS Application Launcher
# Checks dependencies, auto-installs missing packages, and starts Cockpit.
# ==============================================================================

set -e

# Change directory to the folder containing this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "====================================================================="
echo " ⚡ T-Share v2 • macOS Ethernet Transfer & Deep Verification Cockpit"
echo "====================================================================="

# 1. Locate Python 3
PYTHON_BIN=""
if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
fi

if [ -z "$PYTHON_BIN" ]; then
    echo "[ERROR] Python 3 was not found on your Mac."
    echo "Please install Python 3 via Homebrew ('brew install python') or from https://www.python.org/"
    exit 1
fi

# 2. Check and Install Python Dependencies
echo "[*] Checking Python runtime dependencies..."
if ! "$PYTHON_BIN" -c "import webview, objc, WebKit" >/dev/null 2>&1; then
    echo "[!] Missing required Python packages (pywebview / WebKit bindings)."
    echo "[*] Installing dependencies from requirements.txt via pip..."

    if ! "$PYTHON_BIN" -m pip --version >/dev/null 2>&1; then
        echo "[ERROR] pip is not available for $PYTHON_BIN."
        echo "Please install pip or ensure your Python environment is configured."
        exit 1
    fi

    "$PYTHON_BIN" -m pip install -r requirements.txt
    echo "[OK] Dependencies successfully installed."
else
    echo "[OK] Python dependencies verified."
fi

# 3. Launch Application
echo "[*] Launching T-Share v2 Cockpit..."
exec "$PYTHON_BIN" app.py "$@"
