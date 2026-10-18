#!/usr/bin/env bash
# ==============================================================================
# ⚡ T-Share v2 • Linux Application Launcher
# Checks dependencies, auto-installs missing packages, and starts Cockpit.
# ==============================================================================

set -e

# Change directory to the folder containing this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "====================================================================="
echo " ⚡ T-Share v2 • Linux Ethernet Transfer & Deep Verification Cockpit"
echo "====================================================================="

# 1. Locate Python 3
PYTHON_BIN=""
if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
fi

if [ -z "$PYTHON_BIN" ]; then
    echo "[ERROR] Python 3 was not found on your system."
    echo "Please install Python 3 using your distribution package manager:"
    echo "  Debian/Ubuntu: sudo apt update && sudo apt install python3 python3-pip"
    echo "  Fedora:        sudo dnf install python3 python3-pip"
    echo "  Arch Linux:    sudo pacman -S python python-pip"
    exit 1
fi

# 2. Check for rsync
if ! command -v rsync >/dev/null 2>&1; then
    echo "[!] Warning: 'rsync' is not installed on this system."
    echo "    High-speed transfers require rsync. Please install it:"
    echo "    Debian/Ubuntu: sudo apt install rsync"
    echo "    Fedora:        sudo dnf install rsync"
    echo "    Arch Linux:    sudo pacman -S rsync"
    echo ""
fi

# 3. Check and Install Python Dependencies
echo "[*] Checking Python runtime dependencies..."
if ! "$PYTHON_BIN" -c "import webview" >/dev/null 2>&1; then
    echo "[!] Missing required Python package: pywebview"
    echo "[*] Installing dependencies from requirements.txt via pip..."

    if ! "$PYTHON_BIN" -m pip --version >/dev/null 2>&1; then
        echo "[ERROR] pip is not available for $PYTHON_BIN."
        echo "Please install pip: sudo apt install python3-pip (or distro equivalent)"
        exit 1
    fi

    "$PYTHON_BIN" -m pip install -r requirements.txt
    echo "[OK] Dependencies successfully installed."
else
    echo "[OK] Python dependencies verified."
fi

# 4. Check for Linux GUI WebView backend
HAS_BACKEND=false
if "$PYTHON_BIN" -c "import gi; gi.require_version('WebKit2', '4.0')" >/dev/null 2>&1; then
    HAS_BACKEND=true
elif "$PYTHON_BIN" -c "import gi; gi.require_version('WebKit2', '4.1')" >/dev/null 2>&1; then
    HAS_BACKEND=true
elif "$PYTHON_BIN" -c "import PyQt5.QtWebEngineWidgets" >/dev/null 2>&1; then
    HAS_BACKEND=true
elif "$PYTHON_BIN" -c "import PyQt6.QtWebEngineWidgets" >/dev/null 2>&1; then
    HAS_BACKEND=true
fi

if [ "$HAS_BACKEND" = false ]; then
    echo "[i] Note: If the graphical window does not open, install WebKit2GTK:"
    echo "    Ubuntu/Debian: sudo apt install python3-gi gir1.2-webkit2-4.1 (or gir1.2-webkit2-4.0)"
    echo "    Fedora:        sudo dnf install webkit2gtk4.1"
    echo "    Arch Linux:    sudo pacman -S webkit2gtk-4.1"
    echo ""
fi

# 5. Launch Application
echo "[*] Launching T-Share v2 Cockpit..."
exec "$PYTHON_BIN" app.py "$@"
