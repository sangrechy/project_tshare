"""
T-Share v3 Web Server & Browser Mode Fallback
Runs a zero-dependency HTTP server when native GTK/WebKit GUI is not available on Linux.
Seamlessly maps REST API endpoints to BridgeAPI methods.
"""

import os
import sys
import json
import mimetypes
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Optional
from .bridge import BridgeAPI

DEFAULT_WEB_PORT = 52003


class BridgeHTTPHandler(BaseHTTPRequestHandler):
    bridge: Optional[BridgeAPI] = None
    ui_dir: str = ""

    def log_message(self, format: str, *args: Any) -> None:
        # Suppress noisy HTTP access logs
        return

    def do_GET(self) -> None:
        path = self.path.split("?")[0]
        if path in ["/", "/index.html"]:
            filepath = os.path.join(self.ui_dir, "index.html")
        else:
            clean_path = path.lstrip("/").replace("..", "")
            filepath = os.path.join(self.ui_dir, clean_path)

        if os.path.isfile(filepath):
            if filepath.endswith(".js"):
                mime_type = "application/javascript"
            elif filepath.endswith(".css"):
                mime_type = "text/css"
            elif filepath.endswith(".html") or filepath.endswith(".htm"):
                mime_type = "text/html"
            elif filepath.endswith(".svg"):
                mime_type = "image/svg+xml"
            elif filepath.endswith(".json"):
                mime_type = "application/json"
            else:
                mime_type, _ = mimetypes.guess_type(filepath)
                if not mime_type:
                    mime_type = "application/octet-stream"

            self.send_response(200)
            self.send_header("Content-Type", mime_type)
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()

            with open(filepath, "rb") as f:
                self.wfile.write(f.read())
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"404 Not Found")

    def do_OPTIONS(self) -> None:
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self) -> None:
        if self.path.startswith("/api/"):
            method_name = self.path[len("/api/"):]
            if not self.bridge or not hasattr(self.bridge, method_name):
                self.send_response(404)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Method {method_name} not found"}).encode("utf-8"))
                return

            content_len = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_len) if content_len > 0 else b"[]"
            try:
                args = json.loads(body_bytes.decode("utf-8")) if body_bytes else []
                if not isinstance(args, list):
                    args = [args]
            except Exception:
                args = []

            func = getattr(self.bridge, method_name)
            try:
                result = func(*args)
            except Exception as e:
                result = {"error": str(e), "success": False}

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))
        else:
            self.send_response(400)
            self.end_headers()


def start_browser_mode(bridge: BridgeAPI, ui_dir: str, start_port: int = DEFAULT_WEB_PORT) -> None:
    """Launches local HTTP server and opens application in default web browser."""
    bridge.start_background_services()

    BridgeHTTPHandler.bridge = bridge
    BridgeHTTPHandler.ui_dir = ui_dir

    server = None
    active_port = start_port
    for p in range(start_port, start_port + 10):
        try:
            server = HTTPServer(("127.0.0.1", p), BridgeHTTPHandler)
            active_port = p
            break
        except OSError:
            continue

    if not server:
        raise RuntimeError(f"Could not bind web server on ports {start_port}-{start_port+9}")

    url = f"http://127.0.0.1:{active_port}"
    print(f"\n========================================================")
    print(f"  [WEB MODE] T-Share v3 running at: {url}")
    print(f"  Opening default web browser (Chrome / Firefox / Edge)...")
    print(f"  Press Ctrl+C to exit.")
    print(f"========================================================\n")

    try:
        webbrowser.open(url)
    except Exception:
        pass

    try:
        server.serve_forever()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        bridge.stop_background_services()
        server.server_close()
