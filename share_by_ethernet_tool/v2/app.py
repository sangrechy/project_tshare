"""Main Application Launcher for Ethernet File Transfer & Deep Verification Suite v2.

Unifies High-Speed Robocopy File Transfer, Receiver Listener, Multi-Level Cryptographic
Verification, and Persistent SQLite History into a single Dark Neumorphic Soft UI application.
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

from backend.bridge import UnifiedBridge
from backend.history_db import init_db
from backend.network_detector import revoke_network_share
from backend.receiver_engine import ReceiverEngine
from backend.transfer_engine import TransferEngine
from backend.verify_engine import VerificationEngine
from platforms import check_and_cleanup_startup_leases

active_window = None
transfer_engine: TransferEngine | None = None
verify_engine: VerificationEngine | None = None
receiver_engine: ReceiverEngine | None = None
bridge: UnifiedBridge | None = None


def engine_event_dispatcher(event_type: str, data: Any) -> None:
    """Push real-time events from background Python threads to the WebView frontend."""
    global active_window
    if not active_window:
        return

    try:
        if event_type == "log":
            level = data.get("level", "info")
            text = data.get("text", "")
            js_call = f"if (window.onBackendLog) window.onBackendLog({json.dumps(level)}, {json.dumps(text)});"
            active_window.evaluate_js(js_call)

        elif event_type == "transfer_finished":
            js_call = f"if (window.onTransferFinished) window.onTransferFinished({json.dumps(data)});"
            active_window.evaluate_js(js_call)

        elif event_type == "verification_finished":
            js_call = f"if (window.onVerificationFinished) window.onVerificationFinished({json.dumps(data)});"
            active_window.evaluate_js(js_call)

        elif event_type == "receiver_update":
            js_call = f"if (window.onReceiverUpdate) window.onReceiverUpdate({json.dumps(data)});"
            active_window.evaluate_js(js_call)

    except Exception:
        pass


def on_closing() -> bool:
    """Handle window close event: confirm if active transfer or Verifier is running, and revoke share permissions."""
    global transfer_engine, verify_engine, receiver_engine

    if transfer_engine and transfer_engine.is_managed_running():
        if sys.platform.startswith("win"):
            MB_YESNOCANCEL = 0x00000003
            MB_ICONQUESTION = 0x00000020
            IDYES = 6
            IDNO = 7
            IDCANCEL = 2

            res = ctypes.windll.user32.MessageBoxW(
                None,
                "A high-speed file transfer is currently running in the background.\n\n"
                "• Click YES to stop the transfer safely, revoke share permissions, and exit.\n"
                "• Click NO to leave it running in the background (monitor will re-attach on next launch).\n"
                "• Click CANCEL to keep the application window open.",
                "Transfer in Progress",
                MB_YESNOCANCEL | MB_ICONQUESTION,
            )
            if res == IDCANCEL:
                return False  # Prevent closing
            elif res == IDYES:
                transfer_engine.stop_transfer()
                try:
                    revoke_network_share("Transfers")
                except Exception:
                    pass
                return True
            elif res == IDNO:
                return True  # Exit without killing transfer
        else:
            transfer_engine.stop_transfer()
            try:
                revoke_network_share("Transfers")
            except Exception:
                pass
            return True

    # Revoke any temporary network shares created during the session
    try:
        revoke_network_share("Transfers")
    except Exception:
        pass

    if verify_engine and verify_engine.is_running:
        verify_engine.stop_verification()

    if receiver_engine and receiver_engine.is_monitoring:
        receiver_engine.stop_monitoring()

    return True


def run_app(source_path: str = "", dest_path: str = "", startup_cleanup: dict[str, Any] | None = None) -> None:
    """Launch the unified desktop application using PyWebView with Edge WebView2."""
    global active_window, transfer_engine, verify_engine, receiver_engine, bridge
    import webview

    # Ensure startup orphaned share cleanup has occurred
    if startup_cleanup is None:
        startup_cleanup = check_and_cleanup_startup_leases()

    # Initialize SQLite database
    init_db()

    # Initialize engines
    transfer_engine = TransferEngine(on_event=engine_event_dispatcher)
    verify_engine = VerificationEngine(on_event=engine_event_dispatcher)
    receiver_engine = ReceiverEngine(on_event=engine_event_dispatcher)

    if source_path:
        transfer_engine.source_path = source_path
        verify_engine.source_path = source_path
    if dest_path:
        transfer_engine.dest_path = dest_path
        verify_engine.dest_path = dest_path

    bridge = UnifiedBridge(
        transfer_engine=transfer_engine,
        verify_engine=verify_engine,
        receiver_engine=receiver_engine,
        cleanup_info=startup_cleanup,
    )

    html_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "ui", "index.html"))
    file_url = f"file:///{html_path.replace(os.sep, '/')}"

    active_window = webview.create_window(
        title="⚡ T-Share v2 • Ethernet Transfer & Deep Verification Cockpit",
        url=file_url,
        js_api=bridge,
        width=1240,
        height=860,
        min_size=(960, 680),
        background_color="#1a1d21",
    )

    bridge.set_window(active_window)
    active_window.events.closing += on_closing

    webview.start(debug=False)


def main() -> None:
    # --------------------------------------------------------------------------
    # CRITICAL STARTUP SAFETY: The very first action on startup is checking and
    # revoking any orphaned share permissions left from an abrupt shutdown or crash.
    # --------------------------------------------------------------------------
    startup_cleanup = check_and_cleanup_startup_leases()

    parser = argparse.ArgumentParser(description="Ethernet Transfer & Deep Verification Suite v2")
    parser.add_argument("--source", default="", help="Default source directory path")
    parser.add_argument("--dest", default="", help="Default destination directory path")
    args = parser.parse_args()

    run_app(source_path=args.source, dest_path=args.dest, startup_cleanup=startup_cleanup)


if __name__ == "__main__":
    main()
