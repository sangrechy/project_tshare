"""
T-Share v3 Diagnostics & Remote Connection Checker Agent
Provides a lightweight HTTP/JSON diagnostic endpoint on port 52005.
Enables bidirectional link verification, hardware status inspection,
firewall audits, and safe remote diagnostic execution over Wi-Fi/LAN.
"""

import os
import sys
import json
import time
import socket
import psutil
import subprocess
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, Optional

DIAG_PORT = 52005


def get_system_diagnostics() -> Dict[str, Any]:
    """Collects comprehensive network, interface, routing, and firewall diagnostics."""
    interfaces = []
    try:
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()

        for name, addr_list in addrs.items():
            stat = stats.get(name)
            is_up = stat.isup if stat else False
            speed = stat.speed if stat and stat.speed > 0 else 0

            lname = name.lower()
            is_wifi = any(w in lname for w in ["wl", "wi-fi", "wifi", "wireless", "802.11"])
            is_eth = any(e in lname for e in ["eth", "en", "ethernet", "lan", "realtek", "intel", "asix"]) and not is_wifi

            ipv4 = []
            ipv6 = []
            mac = ""

            for a in addr_list:
                if a.family == socket.AF_INET and not a.address.startswith("127."):
                    ipv4.append({"ip": a.address, "netmask": a.netmask})
                elif a.family == socket.AF_INET6:
                    ipv6.append(a.address)
                elif a.family == getattr(psutil, "AF_LINK", -1):
                    mac = a.address

            interfaces.append({
                "name": name,
                "type": "wifi" if is_wifi else ("ethernet" if is_eth else "other"),
                "is_up": is_up,
                "speed_mbps": speed,
                "mac": mac,
                "ipv4": ipv4,
                "ipv6": ipv6
            })
    except Exception as e:
        interfaces = [{"error": str(e)}]

    # Routing info
    routes_text = ""
    try:
        if sys.platform == "win32":
            proc = subprocess.run(["route", "print", "-4"], capture_output=True, text=True, timeout=2)
            routes_text = proc.stdout[:2000]
        else:
            proc = subprocess.run(["ip", "route"], capture_output=True, text=True, timeout=2)
            routes_text = proc.stdout.strip()
    except Exception as e:
        routes_text = f"Error querying routes: {e}"

    # Firewall status
    firewall_text = ""
    try:
        if sys.platform.startswith("linux"):
            if subprocess.run(["which", "firewall-cmd"], capture_output=True).returncode == 0:
                proc = subprocess.run(["firewall-cmd", "--list-all"], capture_output=True, text=True, timeout=2)
                firewall_text = proc.stdout.strip()
            elif subprocess.run(["which", "ufw"], capture_output=True).returncode == 0:
                proc = subprocess.run(["ufw", "status"], capture_output=True, text=True, timeout=2)
                firewall_text = proc.stdout.strip()
            else:
                firewall_text = "No standard firewall manager (iptables/nftables in use)"
        elif sys.platform == "win32":
            firewall_text = "Windows Defender Firewall active"
    except Exception as e:
        firewall_text = str(e)

    # Check if T-Share Receiver port (52001) is listening
    receiver_listening = False
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
        res = s.connect_ex(("127.0.0.1", 52001))
        s.close()
        receiver_listening = (res == 0)
    except Exception:
        pass

    return {
        "platform": sys.platform,
        "hostname": socket.gethostname(),
        "time": time.time(),
        "interfaces": interfaces,
        "routes": routes_text,
        "firewall": firewall_text,
        "receiver_listening": receiver_listening,
        "diag_port": DIAG_PORT
    }


class DiagnosticsHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Silent logging to prevent console spam
        pass

    def _send_json(self, status_code: int, data: Dict[str, Any]):
        body = json.dumps(data, indent=2).encode('utf-8')
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ["/api/status", "/status", "/"]:
            diag = get_system_diagnostics()
            self._send_json(200, diag)
        else:
            self._send_json(404, {"error": "Not Found"})

    def do_POST(self):
        path = self.path.split("?")[0]
        content_len = int(self.headers.get("Content-Length", 0))
        post_bytes = self.rfile.read(content_len) if content_len > 0 else b"{}"

        try:
            payload = json.loads(post_bytes.decode('utf-8'))
        except Exception:
            payload = {}

        if path in ["/api/ping", "/ping"]:
            target = payload.get("target", "127.0.0.1")
            count = int(payload.get("count", 2))
            try:
                cmd = ["ping", "-n" if sys.platform == "win32" else "-c", str(count), "-w" if sys.platform == "win32" else "-W", "2000" if sys.platform == "win32" else "2", target]
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                self._send_json(200, {
                    "success": proc.returncode == 0,
                    "target": target,
                    "output": proc.stdout.strip() or proc.stderr.strip()
                })
            except Exception as e:
                self._send_json(500, {"success": False, "error": str(e)})

        elif path in ["/api/check_tcp", "/check_tcp"]:
            host = payload.get("host", "127.0.0.1")
            port = int(payload.get("port", 52001))
            timeout = float(payload.get("timeout", 3.0))
            t0 = time.time()
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(timeout)
                res = s.connect_ex((host, port))
                latency = round((time.time() - t0) * 1000, 2)
                s.close()
                self._send_json(200, {
                    "host": host,
                    "port": port,
                    "open": (res == 0),
                    "code": res,
                    "latency_ms": latency if res == 0 else None
                })
            except Exception as e:
                self._send_json(200, {"host": host, "port": port, "open": False, "error": str(e)})

        elif path in ["/api/exec", "/exec"]:
            # Diagnostic safe command execution
            cmd = payload.get("cmd", "")
            if not cmd:
                self._send_json(400, {"error": "Missing 'cmd' parameter"})
                return

            try:
                # Run command in shell
                proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
                self._send_json(200, {
                    "cmd": cmd,
                    "returncode": proc.returncode,
                    "stdout": proc.stdout.strip(),
                    "stderr": proc.stderr.strip()
                })
            except subprocess.TimeoutExpired:
                self._send_json(504, {"error": "Command timed out (10s limit)"})
            except Exception as e:
                self._send_json(500, {"error": str(e)})

        elif path in ["/api/set_wire_ip", "/set_wire_ip"]:
            from .network_config import configure_direct_ethernet
            pwd = payload.get("password", "")
            res = configure_direct_ethernet(password=pwd)
            self._send_json(200, res)

        else:
            self._send_json(404, {"error": f"Unknown endpoint: {path}"})


class DiagnosticServer:
    def __init__(self, port: int = DIAG_PORT):
        self.port = port
        self.server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def start(self) -> bool:
        """Starts diagnostic HTTP server on 0.0.0.0:DIAG_PORT."""
        if self._running:
            return True
        try:
            self.server = HTTPServer(("0.0.0.0", self.port), DiagnosticsHandler)
            self._running = True
            self._thread = threading.Thread(target=self.server.serve_forever, daemon=True, name="DiagnosticServerThread")
            self._thread.start()
            return True
        except Exception as e:
            print(f"Warning: Could not start diagnostic server on port {self.port}: {e}", file=sys.stderr)
            return False

    def stop(self) -> None:
        """Stops diagnostic server."""
        if self._running and self.server:
            self._running = False
            try:
                self.server.shutdown()
                self.server.server_close()
            except Exception:
                pass


_global_diag_server: Optional[DiagnosticServer] = None

def start_diagnostic_service(port: int = DIAG_PORT) -> bool:
    """Convenience function to start background diagnostic service."""
    global _global_diag_server
    if _global_diag_server is None:
        _global_diag_server = DiagnosticServer(port=port)
    return _global_diag_server.start()

def stop_diagnostic_service() -> None:
    """Convenience function to stop background diagnostic service."""
    global _global_diag_server
    if _global_diag_server:
        _global_diag_server.stop()
        _global_diag_server = None
