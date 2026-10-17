"""Deep Transaction Verification Cockpit Launcher.

Launches the Dark Neumorphic Soft UI Verifier with SHA-256 bit-by-bit verification,
smart block checksums, metadata parity checks, and exportable audit certificates.
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

from backend.verify_engine import (
    VerificationEngine,
    DEFAULT_SOURCE,
    DEFAULT_DEST,
)

active_window = None
verifier_engine: VerificationEngine | None = None


class VerifierBridge:
    def __init__(self, engine: VerificationEngine) -> None:
        self.engine = engine

    def get_verifier_status(self) -> dict[str, Any]:
        return self.engine.get_status()

    def start_verification(self, mode: str = "metadata", workers: int = 4) -> dict[str, Any]:
        ok, msg = self.engine.start_verification(mode=mode, workers=workers)
        return {"success": ok, "message": msg}

    def stop_verification(self) -> dict[str, Any]:
        self.engine.stop_verification()
        return {"success": True, "message": "Verification stopped."}

    def export_report(self) -> dict[str, Any]:
        try:
            report_path = self.engine.export_html_report()
            if os.path.exists(report_path):
                os.startfile(report_path)
            return {"success": True, "path": report_path}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def open_folder(self, target: str) -> dict[str, Any]:
        try:
            path = self.engine.dest_path if target == "dest" else self.engine.source_path
            if os.path.exists(path):
                os.startfile(path)
                return {"success": True, "message": f"Opened {path}"}
            return {"success": False, "message": f"Path not found: {path}"}
        except Exception as e:
            return {"success": False, "message": str(e)}


def engine_event_dispatcher(event_type: str, data: Any) -> None:
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


def run_webview_verifier(source_path: str = DEFAULT_SOURCE, dest_path: str = DEFAULT_DEST) -> None:
    global active_window, verifier_engine
    import webview

    verifier_engine = VerificationEngine(on_event=engine_event_dispatcher)
    verifier_engine.source_path = source_path
    verifier_engine.dest_path = dest_path
    api = VerifierBridge(verifier_engine)

    html_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "ui_verify", "index.html"))

    active_window = webview.create_window(
        title="Transaction Deep Verifier • File Parity & Bit-Level Audit",
        url=f"file:///{html_path.replace(os.sep, '/')}",
        js_api=api,
        width=1040,
        height=780,
        min_size=(880, 640),
        background_color="#24272c",
    )

    webview.start(debug=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Transaction Deep Verifier")
    parser.add_argument("--tk", "--tkinter", action="store_true", help="Launch Tkinter dark verifier fallback")
    parser.add_argument("--source", default=DEFAULT_SOURCE, help="Source directory or UNC path")
    parser.add_argument("--dest", default=DEFAULT_DEST, help="Destination directory path")
    args = parser.parse_args()

    if args.tk:
        from verify_tkinter import run_tkinter_verifier
        run_tkinter_verifier(source_path=args.source, dest_path=args.dest)
    else:
        try:
            run_webview_verifier(source_path=args.source, dest_path=args.dest)
        except Exception as exc:
            print(f"WebView verifier launch failed ({exc}), falling back to Tkinter...")
            from verify_tkinter import run_tkinter_verifier
            run_tkinter_verifier(source_path=args.source, dest_path=args.dest)


if __name__ == "__main__":
    main()
