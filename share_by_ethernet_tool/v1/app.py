"""Main Application Launcher for Robocopy Transfer Monitor & Safe Resume.

Features:
- Primary GUI: Native WebView2 window with full Dark Neumorphic Soft UI
  derived from E:\\projects\\.res\\ui_theme\\neumorphism-soft-ui.
- Secondary GUI: Tkinter dark fallback (run with --tk).
- Safe Resume Engine: Robocopy /E /Z /J /XO with Windows process identity protection.
- Live Telemetry: Speed, Equalizer, Elapsed, ETA (Estimation Time), and Stream Logs.
"""
from __future__ import annotations

import argparse
import ctypes
import json
import os
import sys
import threading
import time
from typing import Any, Dict

from backend.transfer_engine import (
    TransferEngine,
    DEFAULT_SOURCE,
    DEFAULT_DEST,
    MUTEX_NAME,
)

# Global references
active_window = None
transfer_engine: TransferEngine | None = None


class AppBridge:
    """JS-to-Python API bridge exposed via window.pywebview.api."""

    def __init__(self, engine: TransferEngine) -> None:
        self.engine = engine

    def get_telemetry(self) -> dict[str, Any]:
        return self.engine.get_system_status()

    def start_transfer(self, options: dict[str, Any] | None = None) -> dict[str, Any]:
        options = options or {}
        threads = int(options.get("threads", 8))
        restartable = bool(options.get("restartable", True))
        unbuffered = bool(options.get("unbuffered", True))
        exclude_older = bool(options.get("exclude_older", True))
        exclude_system = bool(options.get("exclude_system", True))
        retry_count = int(options.get("retry_count", 2))
        retry_wait = int(options.get("retry_wait", 2))

        ok, msg = self.engine.start_transfer(
            threads=threads,
            restartable=restartable,
            unbuffered=unbuffered,
            exclude_older=exclude_older,
            exclude_system=exclude_system,
            retry_count=retry_count,
            retry_wait=retry_wait,
        )
        return {"success": ok, "message": msg}

    def stop_transfer(self) -> dict[str, Any]:
        ok, msg = self.engine.stop_transfer()
        return {"success": ok, "message": msg}

    def trigger_scan(self) -> dict[str, Any]:
        self.engine.start_background_scan()
        return {"success": True, "message": "Background scan started."}

    def open_folder(self, target: str) -> dict[str, Any]:
        try:
            path = self.engine.dest_path if target == "dest" else self.engine.source_path
            if os.path.exists(path):
                os.startfile(path)
                return {"success": True, "message": f"Opened {path}"}
            else:
                return {"success": False, "message": f"Path does not exist: {path}"}
        except Exception as e:
            return {"success": False, "message": str(e)}


def engine_event_dispatcher(event_type: str, data: Any) -> None:
    """Push engine events directly to the WebView UI."""
    global active_window
    if not active_window:
        return

    try:
        if event_type == "log":
            level = data.get("level", "info")
            text = data.get("text", "")
            escaped_text = json.dumps(text)
            js_call = f"window.onBackendLog('{level}', {escaped_text});"
            active_window.evaluate_js(js_call)
    except Exception:
        pass


def on_closing() -> bool:
    """Handle window closing event: prompt if Robocopy is running."""
    global transfer_engine
    if not transfer_engine:
        return True

    status = transfer_engine.get_system_status()
    if status["is_managed_running"]:
        MB_YESNOCANCEL = 0x00000003
        MB_ICONQUESTION = 0x00000020
        IDYES = 6
        IDNO = 7
        IDCANCEL = 2

        res = ctypes.windll.user32.MessageBoxW(
            None,
            "A Robocopy transfer is currently running.\n\n"
            "• Click YES to stop the copy safely and exit.\n"
            "• Click NO to leave it running in background (monitor will re-attach on next launch).\n"
            "• Click CANCEL to keep the monitor open.",
            "Transfer in Progress",
            MB_YESNOCANCEL | MB_ICONQUESTION,
        )
        if res == IDCANCEL:
            return False  # Prevent closing
        elif res == IDYES:
            transfer_engine.stop_transfer()
            return True
        elif res == IDNO:
            return True  # Leave running

    return True


def run_webview_app(source_path: str = DEFAULT_SOURCE, dest_path: str = DEFAULT_DEST) -> None:
    """Launch the primary Neumorphic Soft UI WebView application."""
    global active_window, transfer_engine
    import webview

    transfer_engine = TransferEngine(on_event=engine_event_dispatcher)
    transfer_engine.source_path = source_path
    transfer_engine.dest_path = dest_path
    transfer_engine.current_folder = os.path.basename(source_path.rstrip(r"\/")) or "Source"
    api = AppBridge(transfer_engine)

    html_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "ui", "index.html"))

    active_window = webview.create_window(
        title="Ethernet Transfer Cockpit • Robocopy Safe Resume Monitor",
        url=f"file:///{html_path.replace(os.sep, '/')}",
        js_api=api,
        width=980,
        height=740,
        min_size=(820, 620),
        background_color="#24272c",
    )

    active_window.events.closing += on_closing

    # Start initial background scan after UI is ready
    def startup_worker() -> None:
        time.sleep(0.8)
        transfer_engine.start_background_scan()

    threading.Thread(target=startup_worker, daemon=True).start()

    webview.start(debug=False)


def acquire_single_instance_mutex() -> Any:
    """Acquire single-instance mutex to prevent duplicate monitor windows."""
    try:
        mutex = ctypes.windll.kernel32.CreateMutexW(None, True, MUTEX_NAME)
        last_err = ctypes.windll.kernel32.GetLastError()
        if last_err == 183:  # ERROR_ALREADY_EXISTS
            ctypes.windll.user32.MessageBoxW(
                None,
                "The Robocopy Transfer Monitor is already running on this machine.",
                "Already Running",
                0x00000040,
            )
            return None
        return mutex
    except Exception:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Robocopy Safe Resume Monitor & Launcher")
    parser.add_argument("--tk", "--tkinter", action="store_true", help="Launch Tkinter dark fallback interface")
    parser.add_argument("--source", default=DEFAULT_SOURCE, help="Source directory or UNC path")
    parser.add_argument("--dest", default=DEFAULT_DEST, help="Destination directory path")
    args = parser.parse_args()

    mutex = acquire_single_instance_mutex()
    if mutex is None:
        sys.exit(0)

    try:
        if args.tk:
            from tkinter_app import run_tkinter_app
            run_tkinter_app(source_path=args.source, dest_path=args.dest)
        else:
            try:
                run_webview_app(source_path=args.source, dest_path=args.dest)
            except Exception as exc:
                print(f"WebView launch failed ({exc}), falling back to Tkinter...")
                from tkinter_app import run_tkinter_app
                run_tkinter_app(source_path=args.source, dest_path=args.dest)
    finally:
        if mutex:
            try:
                ctypes.windll.kernel32.CloseHandle(mutex)
            except Exception:
                pass


if __name__ == "__main__":
    main()
