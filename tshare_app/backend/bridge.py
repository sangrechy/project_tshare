"""
T-Share Unified JavaScript Bridge API
Provides safe, decoupled API endpoints for the HTML5 frontend.
Guarantees clean primitive data return to prevent COM reflection loops and UI freezing.
"""

import os
import sys
import subprocess
from typing import Dict, List, Any, Optional

from .transfer_engine import TransferEngine
from .receiver_engine import ReceiverEngine
from .discovery import PeerDiscovery
from .history_db import HistoryDatabase
from .hardware_info import get_hardware_telemetry, get_network_interfaces, get_detailed_network_info
from .verify_engine import VerifyEngine
from .web_portal import WebPortalServer, generate_qr_svg


class BridgeAPI:
    def __init__(self, ui_dir: Optional[str] = None):
        self._history_db = HistoryDatabase()
        self._transfer = TransferEngine(history_db=self._history_db)
        self._receiver = ReceiverEngine(history_db=self._history_db)
        self._discovery = PeerDiscovery(tcp_port=self._receiver.port)
        self._verify = VerifyEngine(history_db=self._history_db)

        # Resolve UI directory
        if not ui_dir:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ui_dir = os.path.join(base_dir, "ui")
        self._ui_dir = ui_dir

        # Initialize LAN Web Portal & File Server
        self._portal = WebPortalServer(bridge=self, ui_dir=self._ui_dir, port=52003)

        self._window = None
        self._selected_source_paths: List[str] = []

        # User settings
        self._settings = {
            "use_full_resources": True,
            "default_hash_mode": "crc32",  # 'crc32', 'sha256', 'none'
            "ram_buffer_mb": 512,
            "cpu_duty_percent": 100,
            "worker_threads": 4,
            "bandwidth_limit_mbps": 0,
            "auto_start_portal": True
        }

        # Check and restore any leftover network state from prior interrupted sessions
        from .network_config import check_and_restore_leftover_backup
        check_and_restore_leftover_backup()

    def set_window(self, window) -> None:
        self._window = window

    def start_background_services(self) -> None:
        """Starts discovery, receiver, and web portal services."""
        self._receiver.start()
        self._discovery.start()
        if self._settings.get("auto_start_portal", True):
            try:
                self._portal.start()
            except Exception as e:
                print(f"[!] Web Portal start warning: {e}")

    def stop_background_services(self) -> None:
        """Stops background engines and ensures temporary network settings revert."""
        self._discovery.stop()
        self._receiver.stop()
        self._transfer.cancel()
        self._verify.cancel()
        self._portal.stop()
        from .network_config import revert_direct_ethernet
        revert_direct_ethernet()

    # ------------------ TELEMETRY & STATUS ------------------

    def get_dashboard_telemetry(self) -> Dict[str, Any]:
        """Consolidated telemetry for Home and Status dials."""
        active_role = "none"
        active_data = {}

        can_resume = (
            self._transfer.status in ["error", "cancelled"] and
            bool(getattr(self._transfer, "target_ip", None)) and
            bool(getattr(self._transfer, "source_paths", None))
        )

        if self._transfer.is_active() or self._transfer.status in ["completed", "rejected", "error", "cancelled"]:
            active_role = "sender"
            active_data = self._transfer.get_telemetry()
        elif self._receiver.status in ["waiting_user", "receiving", "completed", "error", "cancelled"]:
            active_role = "receiver"
            active_data = self._receiver.get_telemetry()

        return {
            "hardware": get_hardware_telemetry(
                self._receiver.active_destination or "."
            ),
            "active_role": active_role,
            "transfer": active_data,
            "can_resume": can_resume,
            "wire_alignment": self._discovery.get_subnet_alignment_status(),
            "web_portal": self._portal.get_status()
        }

    def get_discovered_peers(self) -> List[Dict[str, Any]]:
        return self._discovery.get_peers()

    def get_wire_alignment_status(self) -> Optional[Dict[str, Any]]:
        return self._discovery.get_subnet_alignment_status()

    def get_my_network_info(self) -> Dict[str, Any]:
        details = get_detailed_network_info()
        ifaces = get_network_interfaces()
        primary_ip = ifaces[0]["ip"] if ifaces else "127.0.0.1"
        port = self._receiver.port

        wifi_obj = details.get("wifi")
        eth_obj = details.get("ethernet")

        wifi_addr = f"{wifi_obj['ip']}:{port}" if (wifi_obj and wifi_obj.get("has_ip")) else "Disconnected"
        eth_addr = f"{eth_obj['ip']}:{port}" if (eth_obj and eth_obj.get("has_ip")) else ("Unconfigured (Click Setup)" if eth_obj else "No Cable Detected")

        return {
            "primary_ip": primary_ip,
            "port": port,
            "display_address": f"{primary_ip}:{port}",
            "wifi": {
                "available": bool(wifi_obj),
                "name": wifi_obj["name"] if wifi_obj else "Wi-Fi",
                "ip": wifi_obj["ip"] if wifi_obj else "",
                "address": wifi_addr,
                "has_ip": wifi_obj["has_ip"] if wifi_obj else False
            },
            "ethernet": {
                "available": bool(eth_obj),
                "name": eth_obj["name"] if eth_obj else "Ethernet",
                "ip": eth_obj["ip"] if eth_obj else "",
                "address": eth_addr,
                "has_ip": eth_obj["has_ip"] if eth_obj else False,
                "needs_setup": bool(eth_obj and not eth_obj.get("has_ip"))
            }
        }

    # ------------------ FILE & FOLDER PICKERS ------------------

    def _pick_paths_fallback(self, folder: bool = False, multiple: bool = True, title: str = "") -> List[str]:
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.wm_attributes('-topmost', 1)
            if folder:
                res = filedialog.askdirectory(title=title or "Select Folder")
                root.destroy()
                return [res] if res else []
            else:
                res = filedialog.askopenfilenames(title=title or "Select Files")
                root.destroy()
                return list(res) if res else []
        except Exception:
            pass

        if sys.platform.startswith("linux"):
            try:
                cmd = ["zenity", "--file-selection"]
                if title:
                    cmd.extend(["--title", title])
                if folder:
                    cmd.append("--directory")
                elif multiple:
                    cmd.extend(["--multiple", "--separator=|"])
                out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
                if out:
                    return out.split("|") if (multiple and not folder) else [out]
            except Exception:
                pass

        if sys.platform == "darwin":
            try:
                if folder:
                    script = 'choose folder with prompt "Select Folder"'
                    cmd = ["osascript", "-e", f'POSIX path of ({script})']
                elif multiple:
                    script = 'choose file with prompt "Select Files" with multiple selections allowed'
                    cmd = ["osascript", "-e", f'set f to {script}', "-e", 'repeat with i in f', "-e", 'log POSIX path of i', "-e", 'end repeat']
                else:
                    script = 'choose file with prompt "Select File"'
                    cmd = ["osascript", "-e", f'POSIX path of ({script})']
                out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
                if out:
                    return [line.strip() for line in out.splitlines() if line.strip()]
            except Exception:
                pass

        return []

    def select_source_files(self) -> Dict[str, Any]:
        try:
            if self._window and hasattr(self._window, 'create_file_dialog'):
                import webview
                dialog_type = getattr(getattr(webview, 'FileDialog', None), 'OPEN', getattr(webview, 'OPEN_DIALOG', 10))
                files = self._window.create_file_dialog(dialog_type, allow_multiple=True)
            else:
                files = self._pick_paths_fallback(folder=False, multiple=True, title="Select Files to Send")

            if files:
                self._selected_source_paths = list(files)
            return self._summarize_selected_sources()
        except Exception as e:
            return {"error": str(e), "count": 0, "paths": []}

    def select_source_folder(self) -> Dict[str, Any]:
        try:
            if self._window and hasattr(self._window, 'create_file_dialog'):
                import webview
                dialog_type = getattr(getattr(webview, 'FileDialog', None), 'FOLDER', getattr(webview, 'FOLDER_DIALOG', 20))
                folders = self._window.create_file_dialog(dialog_type)
            else:
                folders = self._pick_paths_fallback(folder=True, multiple=False, title="Select Folder to Send")

            if folders:
                self._selected_source_paths = [folders[0]]
            return self._summarize_selected_sources()
        except Exception as e:
            return {"error": str(e), "count": 0, "paths": []}

    def set_source_paths(self, paths: List[str]) -> Dict[str, Any]:
        valid_paths = []
        for p in paths:
            if not p:
                continue
            clean_p = os.path.abspath(p.strip().strip('"').strip("'"))
            if os.path.exists(clean_p):
                valid_paths.append(clean_p)

        if valid_paths:
            self._selected_source_paths = valid_paths
        return self._summarize_selected_sources()

    def _summarize_selected_sources(self) -> Dict[str, Any]:
        total_size = 0
        total_count = 0
        for p in self._selected_source_paths:
            if os.path.isfile(p):
                total_size += os.path.getsize(p)
                total_count += 1
            elif os.path.isdir(p):
                for root, _, fnames in os.walk(p):
                    total_count += len(fnames)
                    for f in fnames:
                        total_size += os.path.getsize(os.path.join(root, f))
        return {
            "count": total_count,
            "total_bytes": total_size,
            "total_mb": round(total_size / (1024 * 1024), 2),
            "paths": self._selected_source_paths
        }

    def select_destination_folder(self) -> Dict[str, Any]:
        try:
            if self._window and hasattr(self._window, 'create_file_dialog'):
                import webview
                dialog_type = getattr(getattr(webview, 'FileDialog', None), 'FOLDER', getattr(webview, 'FOLDER_DIALOG', 20))
                folders = self._window.create_file_dialog(dialog_type)
            else:
                folders = self._pick_paths_fallback(folder=True, multiple=False, title="Select Destination Folder")

            if folders:
                chosen = os.path.abspath(folders[0])
                self._receiver.active_destination = chosen
                return {"path": chosen, "success": True}
            return {"path": self._receiver.active_destination, "success": True}
        except Exception as e:
            return {"error": str(e), "path": self._receiver.active_destination, "success": False}

    def set_destination_path(self, path: str) -> Dict[str, Any]:
        if not path:
            return {"path": self._receiver.active_destination, "success": False, "error": "Empty path provided"}
        clean_p = os.path.abspath(path.strip().strip('"').strip("'"))
        if os.path.isdir(clean_p):
            self._receiver.active_destination = clean_p
            return {"path": clean_p, "success": True}
        return {"path": self._receiver.active_destination, "success": False, "error": f"Directory does not exist: {clean_p}"}

    # ------------------ TRANSFER ACTIONS ------------------

    def start_transfer(self, target_ip: str, target_port: int, hash_mode: str = "crc32") -> Dict[str, Any]:
        """Triggered from Send tab to begin wire transmission with dynamic integrity mode."""
        if not self._selected_source_paths:
            return {"success": False, "error": "No source files or folder selected"}

        if self._settings.get("use_full_resources", True):
            rate_limit = 0.0
        else:
            rate_limit = float(self._settings.get("bandwidth_limit_mbps", 0.0))

        # Use passed hash_mode or default setting
        effective_hash = hash_mode if hash_mode in ["sha256", "crc32", "none"] else self._settings.get("default_hash_mode", "crc32")

        try:
            self._transfer.start_transfer(
                target_ip=target_ip.strip(),
                target_port=int(target_port),
                source_paths=self._selected_source_paths,
                hash_mode=effective_hash,
                rate_limit_mbps=rate_limit
            )
            return {"success": True, "hash_mode": effective_hash}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def accept_transfer(self, destination_dir: str, collision_policy: str = "keep_both") -> Dict[str, Any]:
        try:
            self._receiver.accept_transfer(destination_dir, collision_policy)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def reject_transfer(self, reason: str = "Rejected by user") -> Dict[str, Any]:
        self._receiver.reject_transfer(reason)
        return {"success": True}

    def cancel_active_transfer(self) -> Dict[str, Any]:
        self._transfer.cancel()
        self._receiver.cancel_transfer()
        return {"success": True}

    def resume_transfer(self) -> Dict[str, Any]:
        return self._transfer.resume_transfer()

    def get_system_platform(self) -> str:
        return sys.platform

    def configure_ethernet(self, password: str = "") -> Dict[str, Any]:
        from .network_config import configure_direct_ethernet
        return configure_direct_ethernet(password)

    def revert_ethernet(self) -> Dict[str, Any]:
        from .network_config import revert_direct_ethernet
        return revert_direct_ethernet()

    # ------------------ WEB PORTAL ACTIONS ------------------

    def get_web_portal_status(self) -> Dict[str, Any]:
        return self._portal.get_status()

    def toggle_web_portal(self, start: bool) -> Dict[str, Any]:
        try:
            if start:
                self._portal.start()
            else:
                self._portal.stop()
            return {"success": True, "status": self._portal.get_status()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def select_portal_shared_folder(self) -> Dict[str, Any]:
        try:
            folders = self._pick_paths_fallback(folder=True, multiple=False, title="Select LAN Shared Folder")
            if folders:
                self._portal.update_config(shared_folder=folders[0])
            return {"success": True, "folder": self._portal.shared_folder}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def select_portal_uploads_folder(self) -> Dict[str, Any]:
        try:
            folders = self._pick_paths_fallback(folder=True, multiple=False, title="Select LAN Uploads Destination")
            if folders:
                self._portal.update_config(uploads_folder=folders[0])
            return {"success": True, "folder": self._portal.uploads_folder}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def set_portal_allow_uploads(self, allow: bool) -> Dict[str, Any]:
        self._portal.update_config(allow_uploads=bool(allow))
        return {"success": True, "allow_uploads": self._portal.allow_uploads}

    def get_portal_qr_svg(self) -> str:
        status = self._portal.get_status()
        return generate_qr_svg(status["portal_url"])

    # ------------------ VERIFICATION & HISTORY ------------------

    def get_history(self) -> List[Dict[str, Any]]:
        return self._history_db.get_transfers(limit=50)

    def get_verify_ledger(self) -> Dict[str, Any]:
        return {
            "sender_sessions": self._history_db.get_sessions_by_role("sender", limit=30),
            "receiver_sessions": self._history_db.get_sessions_by_role("receiver", limit=30),
            "portal_sessions": self._history_db.get_sessions_by_role("web_portal", limit=30)
        }

    def start_verification(self, session_id: str, mode: str = "full_crypto") -> Dict[str, Any]:
        """Audits a session with either Quick Parity or Full Cryptographic SHA-256."""
        try:
            self._verify.start_verification(session_id, mode)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_verify_telemetry(self) -> Dict[str, Any]:
        return self._verify.get_telemetry()

    def open_folder(self, folder_path: str) -> Dict[str, Any]:
        abs_p = os.path.abspath(folder_path)
        if not os.path.exists(abs_p):
            # If path was a file, try opening its directory
            parent = os.path.dirname(abs_p)
            if os.path.exists(parent):
                abs_p = parent
            else:
                return {"success": False, "error": f"Path not found: {abs_p}"}

        try:
            if sys.platform == "win32":
                os.startfile(abs_p)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", abs_p])
            else:
                subprocess.Popen(["xdg-open", abs_p])
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ------------------ SETTINGS ------------------

    def get_settings(self) -> Dict[str, Any]:
        return self._settings

    def save_settings(self, new_settings: Dict[str, Any]) -> Dict[str, Any]:
        self._settings.update(new_settings)
        return {"success": True, "settings": self._settings}
