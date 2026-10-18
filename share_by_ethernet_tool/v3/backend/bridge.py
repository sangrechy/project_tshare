"""
T-Share v3 PyWebView JavaScript Bridge
Provides safe, decoupled API endpoints for the HTML5 frontend.
Guarantees clean primitive data return to prevent COM reflection loops and UI freezing.
"""

import os
import sys
import subprocess
import webview
from typing import Dict, List, Any, Optional

from .transfer_engine import TransferEngine
from .receiver_engine import ReceiverEngine
from .discovery import PeerDiscovery
from .history_db import HistoryDatabase
from .hardware_info import get_hardware_telemetry, get_network_interfaces, get_detailed_network_info
from .verify_engine import VerifyEngine


class BridgeAPI:
    def __init__(self):
        # All internal engines MUST be strictly private to prevent PyWebView reflection recursion
        self._history_db = HistoryDatabase()
        self._transfer = TransferEngine(history_db=self._history_db)
        self._receiver = ReceiverEngine(history_db=self._history_db)
        self._discovery = PeerDiscovery(tcp_port=self._receiver.port)
        self._verify = VerifyEngine(history_db=self._history_db)
        self._window: Optional[webview.Window] = None

        # Source files selected on Sender
        self._selected_source_paths: List[str] = []

        # User settings
        self._settings = {
            "use_full_resources": True,
            "ram_buffer_mb": 512,
            "cpu_duty_percent": 100,
            "worker_threads": 4,
            "bandwidth_limit_mbps": 0  # 0 = uncapped
        }

        # Check and restore any leftover network state from previous interrupted sessions
        from .network_config import check_and_restore_leftover_backup
        check_and_restore_leftover_backup()

    def set_window(self, window: webview.Window) -> None:
        self._window = window

    def start_background_services(self) -> None:
        """Starts discovery and receiver services."""
        self._receiver.start()
        self._discovery.start()

    def stop_background_services(self) -> None:
        """Stops background engines and ensures temporary network settings revert."""
        self._discovery.stop()
        self._receiver.stop()
        self._transfer.cancel()
        self._verify.cancel()
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
            "can_resume": can_resume
        }

    def get_discovered_peers(self) -> List[Dict[str, Any]]:
        """Returns list of active peers found on direct link / LAN."""
        return self._discovery.get_peers()

    def get_my_network_info(self) -> Dict[str, Any]:
        """Provides detailed Wi-Fi and Ethernet network module information."""
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
        """Cross-platform fallback file picker when native pywebview window is not active."""
        # 1. Tkinter
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

        # 2. Linux zenity
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

            # 3. Linux kdialog
            try:
                cmd = ["kdialog"]
                if title:
                    cmd.extend(["--title", title])
                if folder:
                    cmd.append("--getexistingdirectory")
                elif multiple:
                    cmd.extend(["--getopenfilename", "--multiple"])
                else:
                    cmd.append("--getopenfilename")
                out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
                if out:
                    return out.split() if (multiple and not folder) else [out]
            except Exception:
                pass

        # 4. macOS osascript
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
        """Sender file selection dialog."""
        try:
            if self._window:
                files = self._window.create_file_dialog(webview.OPEN_DIALOG, allow_multiple=True)
            else:
                files = self._pick_paths_fallback(folder=False, multiple=True, title="Select Files to Send")

            if files:
                self._selected_source_paths = list(files)
            return self._summarize_selected_sources()
        except Exception as e:
            return {"error": str(e), "count": 0, "paths": []}

    def select_source_folder(self) -> Dict[str, Any]:
        """Sender folder selection dialog."""
        try:
            if self._window:
                folders = self._window.create_file_dialog(webview.FOLDER_DIALOG)
            else:
                folders = self._pick_paths_fallback(folder=True, multiple=False, title="Select Folder to Send")

            if folders:
                self._selected_source_paths = [folders[0]]
            return self._summarize_selected_sources()
        except Exception as e:
            return {"error": str(e), "count": 0, "paths": []}

    def set_source_paths(self, paths: List[str]) -> Dict[str, Any]:
        """Directly assigns or appends source paths (useful for manual entry and drag & drop)."""
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
        """Receiver destination selection dialog."""
        try:
            if self._window:
                folders = self._window.create_file_dialog(webview.FOLDER_DIALOG)
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
        """Directly sets receiver destination directory from text input."""
        if not path:
            return {"path": self._receiver.active_destination, "success": False, "error": "Empty path provided"}
        clean_p = os.path.abspath(path.strip().strip('"').strip("'"))
        if os.path.isdir(clean_p):
            self._receiver.active_destination = clean_p
            return {"path": clean_p, "success": True}
        return {"path": self._receiver.active_destination, "success": False, "error": f"Directory does not exist: {clean_p}"}

    # ------------------ TRANSFER ACTIONS ------------------

    def start_transfer(self, target_ip: str, target_port: int) -> Dict[str, Any]:
        """Triggered from Send tab to begin transmission."""
        if not self._selected_source_paths:
            return {"success": False, "error": "No source files or folder selected"}

        if self._settings.get("use_full_resources", True):
            rate_limit = 0.0
        else:
            rate_limit = float(self._settings.get("bandwidth_limit_mbps", 0.0))

        try:
            self._transfer.start_transfer(
                target_ip=target_ip.strip(),
                target_port=int(target_port),
                source_paths=self._selected_source_paths,
                rate_limit_mbps=rate_limit
            )
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def accept_transfer(self, destination_dir: str, collision_policy: str = "keep_both") -> Dict[str, Any]:
        """Receiver confirms incoming transfer offer."""
        try:
            self._receiver.accept_transfer(destination_dir, collision_policy)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def reject_transfer(self, reason: str = "Rejected by user") -> Dict[str, Any]:
        """Receiver declines incoming transfer offer."""
        self._receiver.reject_transfer(reason)
        return {"success": True}

    def cancel_active_transfer(self) -> Dict[str, Any]:
        """Emergency stop from Home or Transfer screen."""
        self._transfer.cancel()
        self._receiver.cancel_transfer()
        return {"success": True}

    def resume_transfer(self) -> Dict[str, Any]:
        """Resumes an interrupted or disconnected transfer from Home screen."""
        return self._transfer.resume_transfer()

    def configure_ethernet(self) -> Dict[str, Any]:
        """Triggers native OS privilege elevation popup (Polkit/pkexec or Windows UAC) to auto-configure direct Ethernet."""
        from .network_config import configure_direct_ethernet
        return configure_direct_ethernet()

    def revert_ethernet(self) -> Dict[str, Any]:
        """Manually or automatically reverts temporary Ethernet IP and firewall settings back to normal."""
        from .network_config import revert_direct_ethernet
        return revert_direct_ethernet()

    # ------------------ VERIFICATION & HISTORY ------------------

    def get_history(self) -> List[Dict[str, Any]]:
        """Fetch past transfers from SQLite."""
        return self._history_db.get_transfers(limit=50)

    def get_verify_ledger(self) -> Dict[str, Any]:
        """Fetch dual ledgers for Sender and Receiver."""
        return {
            "sender_sessions": self._history_db.get_sessions_by_role("sender", limit=30),
            "receiver_sessions": self._history_db.get_sessions_by_role("receiver", limit=30)
        }

    def start_verification(self, session_id: str, mode: str) -> Dict[str, Any]:
        """Starts quick parity or full cryptographic audit."""
        try:
            self._verify.start_verification(session_id, mode)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_verify_telemetry(self) -> Dict[str, Any]:
        return self._verify.get_telemetry()

    def open_folder(self, folder_path: str) -> Dict[str, Any]:
        """Opens folder in local system file explorer (Windows Explorer / xdg-open)."""
        abs_p = os.path.abspath(folder_path)
        if not os.path.exists(abs_p):
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
