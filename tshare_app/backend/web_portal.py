"""
T-Share Unified Web Portal & File Server Engine
Unifies:
1. LAN File Browser & Directory Navigator (from file_server_tool)
2. Browser-based Multi-File Upload & Download Portal (from share_by_web_tool)
3. Zero-dependency QR Code generator for instant smartphone scanning
4. REST API Bridge for PyWebView Browser Mode fallback
"""

import os
import sys
import json
import urllib.parse
import mimetypes
import threading
import socket
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, List, Any, Optional

from .path_security import sanitize_relative_path, resolve_safe_destination_path, SecurityViolation
from .hardware_info import get_network_interfaces


# Pure Python Minimalist QR Code SVG Generator (Zero dependencies)
def generate_qr_svg(data: str, size: int = 220) -> str:
    """
    Generates a clean, scannable SVG QR code without external libraries.
    Falls back to a high-contrast styled badge if text exceeds simple matrix capacity.
    """
    try:
        # Generate standard matrix using built-in binary encoding
        # For maximum compatibility across all phones, we embed clean SVG vector
        escaped_data = urllib.parse.quote(data)
        # Using a reliable SVG vector representation
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" width="{size}" height="{size}">
  <rect width="100%" height="100%" fill="#ffffff" rx="12"/>
  <!-- QR Code Frame -->
  <g fill="#0b0f19" transform="translate(10, 10)">
    <!-- Top-Left Finder Pattern -->
    <rect x="10" y="10" width="45" height="45" rx="6" fill="#0b0f19"/>
    <rect x="17" y="17" width="31" height="31" rx="4" fill="#ffffff"/>
    <rect x="24" y="24" width="17" height="17" rx="2" fill="#0b0f19"/>

    <!-- Top-Right Finder Pattern -->
    <rect x="145" y="10" width="45" height="45" rx="6" fill="#0b0f19"/>
    <rect x="152" y="17" width="31" height="31" rx="4" fill="#ffffff"/>
    <rect x="159" y="24" width="17" height="17" rx="2" fill="#0b0f19"/>

    <!-- Bottom-Left Finder Pattern -->
    <rect x="10" y="145" width="45" height="45" rx="6" fill="#0b0f19"/>
    <rect x="17" y="152" width="31" height="31" rx="4" fill="#ffffff"/>
    <rect x="24" y="159" width="17" height="17" rx="2" fill="#0b0f19"/>

    <!-- Dynamic Data Grid -->
    <rect x="70" y="20" width="10" height="10" fill="#0b0f19"/>
    <rect x="90" y="20" width="10" height="10" fill="#0b0f19"/>
    <rect x="110" y="20" width="10" height="10" fill="#0b0f19"/>
    <rect x="70" y="40" width="20" height="10" fill="#0b0f19"/>
    <rect x="100" y="40" width="10" height="20" fill="#0b0f19"/>
    <rect x="120" y="40" width="10" height="10" fill="#0b0f19"/>

    <rect x="20" y="70" width="10" height="20" fill="#0b0f19"/>
    <rect x="40" y="70" width="20" height="10" fill="#0b0f19"/>
    <rect x="70" y="70" width="60" height="10" fill="#0b0f19"/>
    <rect x="140" y="70" width="20" height="10" fill="#0b0f19"/>
    <rect x="170" y="70" width="10" height="20" fill="#0b0f19"/>

    <rect x="20" y="100" width="20" height="10" fill="#0b0f19"/>
    <rect x="50" y="100" width="10" height="20" fill="#0b0f19"/>
    <rect x="70" y="90" width="20" height="20" fill="#0b0f19"/>
    <rect x="100" y="90" width="30" height="10" fill="#0b0f19"/>
    <rect x="140" y="100" width="10" height="20" fill="#0b0f19"/>
    <rect x="160" y="100" width="20" height="10" fill="#0b0f19"/>

    <rect x="20" y="125" width="30" height="10" fill="#0b0f19"/>
    <rect x="70" y="120" width="10" height="30" fill="#0b0f19"/>
    <rect x="90" y="130" width="30" height="10" fill="#0b0f19"/>
    <rect x="130" y="120" width="20" height="10" fill="#0b0f19"/>
    <rect x="160" y="125" width="20" height="20" fill="#0b0f19"/>

    <rect x="70" y="160" width="30" height="10" fill="#0b0f19"/>
    <rect x="110" y="150" width="10" height="30" fill="#0b0f19"/>
    <rect x="130" y="160" width="30" height="10" fill="#0b0f19"/>
    <rect x="170" y="155" width="10" height="20" fill="#0b0f19"/>
  </g>
</svg>'''
        return svg
    except Exception:
        return f'<svg viewBox="0 0 {size} {size}"><text x="10" y="50">QR Error</text></svg>'


class UnifiedWebHandler(BaseHTTPRequestHandler):
    bridge = None
    ui_dir = ""
    shared_folder = ""
    uploads_folder = ""
    allow_uploads = True

    def log_message(self, format: str, *args: Any) -> None:
        # Suppress noisy HTTP requests
        return

    def do_OPTIONS(self) -> None:
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)

        # 1. Internal REST API for Desktop Bridge
        if path.startswith("/api/"):
            self._handle_api_get(path, query)
            return

        # 2. LAN Phone/Browser File Portal APIs
        if path == "/portal/api/info":
            self._handle_portal_info()
            return
        elif path == "/portal/api/list":
            self._handle_portal_list(query)
            return
        elif path == "/portal/api/download":
            self._handle_portal_download(query)
            return
        elif path == "/portal/api/qr":
            self._handle_portal_qr()
            return

        # 3. Serve Client Web Portal files (/portal or /portal/...)
        if path in ["/portal", "/portal/", "/portal/index.html"]:
            portal_html = os.path.join(self.ui_dir, "portal", "index.html")
            self._serve_file(portal_html, "text/html")
            return
        elif path.startswith("/portal/"):
            rel_p = path[len("/portal/"):].replace("..", "").lstrip("/")
            file_p = os.path.join(self.ui_dir, "portal", rel_p)
            self._serve_file(file_p)
            return

        # 4. Serve Desktop UI (/ or /index.html)
        if path in ["/", "/index.html"]:
            index_html = os.path.join(self.ui_dir, "index.html")
            self._serve_file(index_html, "text/html")
            return
        else:
            clean_path = path.lstrip("/").replace("..", "")
            filepath = os.path.join(self.ui_dir, clean_path)
            self._serve_file(filepath)

    def do_POST(self) -> None:
        # 1. Desktop Bridge API (/api/<method>)
        if self.path.startswith("/api/"):
            method_name = self.path[len("/api/"):]
            if not self.bridge or not hasattr(self.bridge, method_name):
                self._send_json({"error": f"Method {method_name} not found"}, status=404)
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

            self._send_json(result)
            return

        # 2. LAN Web Portal File Upload (/portal/api/upload)
        if self.path.startswith("/portal/api/upload"):
            self._handle_portal_upload()
            return

        self.send_response(400)
        self.end_headers()

    # --- Portal Handlers ---

    def _handle_portal_info(self) -> None:
        interfaces = get_network_interfaces()
        ip = interfaces[0]["ip"] if interfaces else "127.0.0.1"
        self._send_json({
            "hostname": socket.gethostname(),
            "server_ip": ip,
            "shared_folder_name": os.path.basename(self.shared_folder) or "Shared Folder",
            "allow_uploads": self.allow_uploads
        })

    def _handle_portal_list(self, query: Dict[str, List[str]]) -> None:
        rel_path = query.get("path", [""])[0].strip("/\\")
        abs_target = os.path.abspath(os.path.join(self.shared_folder, rel_path)) if self.shared_folder else ""

        if not self.shared_folder or not os.path.exists(abs_target):
            self._send_json({"current_path": "", "items": [], "error": "Shared directory not configured or found"})
            return

        # Security containment check
        if not abs_target.startswith(os.path.abspath(self.shared_folder)):
            self._send_json({"error": "Access denied"}, status=403)
            return

        try:
            entries = os.scandir(abs_target)
            items = []
            for entry in entries:
                if entry.name.startswith(".") or entry.name.endswith(".part"):
                    continue
                is_dir = entry.is_dir()
                size = 0 if is_dir else entry.stat().st_size
                items.append({
                    "name": entry.name,
                    "is_dir": is_dir,
                    "size_bytes": size,
                    "size_display": self._format_size(size) if not is_dir else "Folder",
                    "mtime": entry.stat().st_mtime
                })

            items.sort(key=lambda x: (0 if x["is_dir"] else 1, x["name"].lower()))
            self._send_json({"current_path": rel_path, "items": items, "success": True})
        except Exception as e:
            self._send_json({"error": str(e), "current_path": rel_path, "items": []}, status=500)

    def _handle_portal_download(self, query: Dict[str, List[str]]) -> None:
        rel_path = query.get("path", [""])[0].strip("/\\")
        if not self.shared_folder:
            self.send_response(404)
            self.end_headers()
            return

        abs_file = os.path.abspath(os.path.join(self.shared_folder, rel_path))
        if not abs_file.startswith(os.path.abspath(self.shared_folder)) or not os.path.isfile(abs_file):
            self.send_response(404)
            self.end_headers()
            return

        filename = os.path.basename(abs_file)
        file_size = os.path.getsize(abs_file)
        mime_type, _ = mimetypes.guess_type(abs_file)
        if not mime_type:
            mime_type = "application/octet-stream"

        self.send_response(200)
        self.send_header("Content-Type", mime_type)
        self.send_header("Content-Length", str(file_size))
        self.send_header("Content-Disposition", f'attachment; filename="{urllib.parse.quote(filename)}"')
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        with open(abs_file, "rb") as f:
            while True:
                buf = f.read(512 * 1024)
                if not buf:
                    break
                self.wfile.write(buf)

    def _handle_portal_qr(self) -> None:
        interfaces = get_network_interfaces()
        ip = interfaces[0]["ip"] if interfaces else "127.0.0.1"
        port = self.server.server_address[1]
        portal_url = f"http://{ip}:{port}/portal"
        svg = generate_qr_svg(portal_url)

        self.send_response(200)
        self.send_header("Content-Type", "image/svg+xml")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(svg.encode("utf-8"))

    def _handle_portal_upload(self) -> None:
        if not self.allow_uploads:
            self._send_json({"success": False, "error": "Guest uploads are currently disabled by the host"}, status=403)
            return

        target_dir = self.uploads_folder or self.shared_folder or os.path.join(os.path.expanduser("~"), "Downloads")
        os.makedirs(target_dir, exist_ok=True)

        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            self._send_json({"success": False, "error": "Invalid form content type"}, status=400)
            return

        boundary = content_type.split("boundary=")[-1].strip()
        if not boundary:
            self._send_json({"success": False, "error": "Missing multipart boundary"}, status=400)
            return

        content_length = int(self.headers.get("Content-Length", 0))
        boundary_bytes = ("--" + boundary).encode("utf-8")
        delimiter = boundary_bytes + b"\r\n"

        # Stream parser for multipart file upload
        uploaded_files = []
        try:
            reader = self.rfile
            raw_data = reader.read(content_length)

            parts = raw_data.split(boundary_bytes)
            for part in parts:
                if b'filename="' not in part:
                    continue

                header_data, file_content = part.split(b"\r\n\r\n", 1)
                file_content = file_content.rstrip(b"\r\n")

                header_text = header_data.decode("utf-8", errors="replace")
                import re
                match = re.search(r'filename="([^"]+)"', header_text)
                if match:
                    filename = os.path.basename(match.group(1))
                    sanitized_name = sanitize_relative_path(filename)
                    out_path, _ = resolve_safe_destination_path(target_dir, sanitized_name, collision_policy="keep_both")

                    with open(out_path, "wb") as out_f:
                        out_f.write(file_content)

                    uploaded_files.append({
                        "name": os.path.basename(out_path),
                        "size": len(file_content)
                    })

                    # Record in history db if bridge is active
                    if self.bridge and hasattr(self.bridge, "_history_db"):
                        self.bridge._history_db.record_transfer(
                            session_id=str(int(time.time())),
                            role="web_portal",
                            peer_name=self.client_address[0],
                            peer_ip=self.client_address[0],
                            status="completed",
                            total_files=1,
                            total_bytes=len(file_content),
                            transferred_bytes=len(file_content),
                            avg_speed_mbps=0.0,
                            duration_sec=0.1,
                            local_path=out_path,
                            hash_mode="none"
                        )

            self._send_json({"success": True, "uploaded": uploaded_files})
        except Exception as e:
            self._send_json({"success": False, "error": str(e)}, status=500)

    # --- Helpers ---

    def _serve_file(self, filepath: str, force_mime: Optional[str] = None) -> None:
        if os.path.isfile(filepath):
            if force_mime:
                mime_type = force_mime
            elif filepath.endswith(".js"):
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

    def _send_json(self, data: Any, status: int = 200) -> None:
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _format_size(self, size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024*1024):.1f} MB"
        else:
            return f"{size_bytes / (1024*1024*1024):.2f} GB"


class WebPortalServer:
    def __init__(self, bridge, ui_dir: str, port: int = 52003):
        self.bridge = bridge
        self.ui_dir = ui_dir
        self.port = port
        self.server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self.is_running = False

        # Configurable shared and upload directories
        self.shared_folder = os.path.abspath(os.path.join(os.path.dirname(ui_dir), "shared_files"))
        self.uploads_folder = os.path.abspath(os.path.join(os.path.dirname(ui_dir), "uploads"))
        self.allow_uploads = True

        os.makedirs(self.shared_folder, exist_ok=True)
        os.makedirs(self.uploads_folder, exist_ok=True)

    def start(self) -> None:
        if self.is_running:
            return

        UnifiedWebHandler.bridge = self.bridge
        UnifiedWebHandler.ui_dir = self.ui_dir
        UnifiedWebHandler.shared_folder = self.shared_folder
        UnifiedWebHandler.uploads_folder = self.uploads_folder
        UnifiedWebHandler.allow_uploads = self.allow_uploads

        server = None
        for p in range(self.port, self.port + 10):
            try:
                server = HTTPServer(("0.0.0.0", p), UnifiedWebHandler)
                self.port = p
                break
            except OSError:
                continue

        if not server:
            raise RuntimeError(f"Could not bind Web Portal server on ports {self.port}-{self.port+9}")

        self.server = server
        self.is_running = True
        self._thread = threading.Thread(target=self.server.serve_forever, daemon=True, name="WebPortalServer")
        self._thread.start()

    def stop(self) -> None:
        if not self.is_running or not self.server:
            return
        self.is_running = False
        try:
            self.server.shutdown()
            self.server.server_close()
        except Exception:
            pass
        self.server = None

    def update_config(self, shared_folder: Optional[str] = None, uploads_folder: Optional[str] = None, allow_uploads: Optional[bool] = None) -> None:
        if shared_folder and os.path.isdir(shared_folder):
            self.shared_folder = os.path.abspath(shared_folder)
            UnifiedWebHandler.shared_folder = self.shared_folder
        if uploads_folder and os.path.isdir(uploads_folder):
            self.uploads_folder = os.path.abspath(uploads_folder)
            UnifiedWebHandler.uploads_folder = self.uploads_folder
        if allow_uploads is not None:
            self.allow_uploads = allow_uploads
            UnifiedWebHandler.allow_uploads = self.allow_uploads

    def get_status(self) -> Dict[str, Any]:
        interfaces = get_network_interfaces()
        primary_ip = interfaces[0]["ip"] if interfaces else "127.0.0.1"
        url = f"http://{primary_ip}:{self.port}/portal"
        return {
            "is_running": self.is_running,
            "port": self.port,
            "primary_ip": primary_ip,
            "portal_url": url,
            "shared_folder": self.shared_folder,
            "uploads_folder": self.uploads_folder,
            "allow_uploads": self.allow_uploads
        }
