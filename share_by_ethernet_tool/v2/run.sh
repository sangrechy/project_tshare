#!/usr/bin/env bash
# ==============================================================================
# ⚡ T-Share v2 • Universal POSIX Launcher (Linux / macOS)
# Auto-detects operating system and launches the appropriate launcher.
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

OS="$(uname -s 2>/dev/null || echo "Unknown")"

case "$OS" in
    Darwin*)
        exec ./run_mac.sh "$@"
        ;;
    Linux*)
        exec ./run_linux.sh "$@"
        ;;
    *)
        # Default fallback to linux launcher
        exec ./run_linux.sh "$@"
        ;;
esac
