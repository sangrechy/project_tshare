"""Unified Bridge connecting Web UI to Backend Engines.

Exposes high-performance Python methods to JavaScript via PyWebView (window.pywebview.api)
and coordinates Transfer, Verification, Receiver, Network Telemetry, Peer-to-Peer Auto-Discovery,
Direct High-Speed Socket Streaming, and History.

All internal references are strictly private (prefixed with '_') to prevent PyWebView
from reflecting native .NET COM objects and causing recursion/threading exceptions.
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
from typing import Any, Callable, Dict, List, Optional

from . import history_db, network_detector
from .p2p_discovery import get_discovery_engine
from .p2p_transfer import P2PReceiverServer, P2PSenderClient
from .receiver_engine import ReceiverEngine
from .transfer_engine import TransferEngine
from .verify_engine import VerificationEngine


class UnifiedBridge:
    def __init__(
        self,
        transfer_engine: TransferEngine,
        verify_engine: VerificationEngine,
        receiver_engine: ReceiverEngine,
        window_ref: Any = None,
        cleanup_info: Optional[dict[str, Any]] = None,
    ) -> None:
        self._transfer = transfer_engine
        self._verify = verify_engine
        self._receiver = receiver_engine
        self._window = window_ref
        self._cleanup_info = cleanup_info

        # Autonomous Peer-to-Peer & Direct Socket Engines
        self._discovery = get_discovery_engine()
        self._p2p_receiver = P2PReceiverServer()
        self._p2p_receiver.start()  # Autonomously start listening for direct streams
        self._p2p_sender = P2PSenderClient()

    def set_window(self, window_ref: Any) -> None:
        self._window = window_ref

    # ----------------------------------------------------
    # PEER AUTO-DISCOVERY & DIRECT P2P TRANSFER (AUTONOMOUS)
    # ----------------------------------------------------
    def get_discovered_peers(self) -> list[dict[str, Any]]:
        """Return active peers auto-discovered over direct Ethernet or local network."""
        return self._discovery.get_peers()

    def p2p_start_transfer(self, peer_ip: str, source_path: str, peer_port: int = 52100) -> dict[str, Any]:
        """Initiate direct high-speed socket file transfer to peer."""
        ok, msg = self._p2p_sender.start_transfer(peer_ip=peer_ip, source_path=source_path, peer_port=peer_port)
        return {"success": ok, "message": msg}

    def p2p_stop_transfer(self) -> dict[str, Any]:
        """Cancel direct socket file transfer."""
        ok, msg = self._p2p_sender.stop_transfer()
        return {"success": ok, "message": msg}

    def get_p2p_sender_telemetry(self) -> dict[str, Any]:
        """Return live sender telemetry (bytes, speed, ETA, verified file count)."""
        return self._p2p_sender.get_telemetry()

    def get_p2p_receiver_telemetry(self) -> dict[str, Any]:
        """Return live receiver telemetry (inbound bytes, files, speed, status)."""
        return self._p2p_receiver.get_telemetry()

    def p2p_set_receiver_dest(self, folder_path: str) -> dict[str, Any]:
        """Change destination directory for direct incoming socket transfers."""
        self._p2p_receiver.set_dest_dir(folder_path)
        return {"success": True, "dest_dir": self._p2p_receiver.dest_dir}

    # ----------------------------------------------------
    # SYSTEM & HARDWARE OVERVIEW
    # ----------------------------------------------------
    def get_system_overview(self) -> dict[str, Any]:
        """Fetch system info, adapters, drives, and summary stats for Home Dashboard."""
        machine_info = network_detector.get_local_machine_info()
        adapters = network_detector.get_network_adapters()
        drives = network_detector.get_disk_drives()
        shares = network_detector.get_windows_shares()
        stats = history_db.get_stats_summary()
        peers = self._discovery.get_peers()

        transfer_status = self._transfer.get_telemetry()
        verify_status = self._verify.get_status()
        receiver_status = self._receiver.get_status()
        p2p_recv_status = self._p2p_receiver.get_telemetry()
        p2p_send_status = self._p2p_sender.get_telemetry()

        return {
            "machine": machine_info,
            "adapters": adapters,
            "drives": drives,
            "shares": shares,
            "stats": stats,
            "peers": peers,
            "active_transfer": transfer_status,
            "active_verify": verify_status,
            "active_receiver": receiver_status,
            "p2p_receiver": p2p_recv_status,
            "p2p_sender": p2p_send_status,
            "startup_cleanup": self._cleanup_info,
        }

    def test_latency(self, host_or_path: str) -> dict[str, Any]:
        """Test SMB roundtrip TCP latency to target host or UNC path."""
        ms = network_detector.measure_smb_latency(host_or_path)
        return {
            "success": ms is not None,
            "latency_ms": ms,
            "display": f"{ms} ms" if ms is not None else "Offline / Unreachable",
        }

    def browse_folder(self, initial_dir: str = "", title: str = "Select Folder") -> dict[str, Any]:
        """Open native folder selection dialog."""
        selected_path: str | None = None

        # 1. Try PyWebView native dialog if window is available
        if self._window and hasattr(self._window, "create_file_dialog"):
            try:
                import webview
                result = self._window.create_file_dialog(
                    webview.FileDialog.FOLDER,
                    directory=initial_dir if (initial_dir and os.path.exists(initial_dir)) else "",
                )
                if result and len(result) > 0:
                    selected_path = result[0]
            except Exception:
                selected_path = None

        # 2. Fallback to Tkinter folder dialog if PyWebView dialog was cancelled or unavailable
        if not selected_path:
            try:
                import tkinter as tk
                from tkinter import filedialog
                root = tk.Tk()
                root.withdraw()
                root.attributes("-topmost", True)
                selected_path = filedialog.askdirectory(
                    title=title,
                    initialdir=initial_dir if (initial_dir and os.path.exists(initial_dir)) else None,
                )
                root.destroy()
            except Exception:
                selected_path = None

        if selected_path:
            return {"success": True, "path": os.path.normpath(selected_path)}
        return {"success": False, "path": ""}

    def open_folder(self, path: str) -> dict[str, Any]:
        """Open folder in system file manager (Explorer, Finder, or Linux file manager)."""
        clean_path = path.strip().strip('"')
        if not clean_path:
            return {"success": False, "message": "Path is empty."}
        try:
            if os.path.exists(clean_path):
                if hasattr(os, "startfile"):
                    os.startfile(clean_path)
                elif sys.platform == "darwin":
                    subprocess.run(["open", clean_path], check=False)
                else:
                    subprocess.run(["xdg-open", clean_path], check=False)
                return {"success": True, "message": f"Opened {clean_path}"}
            else:
                return {"success": False, "message": f"Path not found: {clean_path}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # ----------------------------------------------------
    # TRANSFER / SENDER METHODS (ROBOCOPY / RSYNC)
    # ----------------------------------------------------
    def start_transfer(self, options: dict[str, Any]) -> dict[str, Any]:
        source = str(options.get("source", ""))
        dest = str(options.get("dest", ""))
        threads = int(options.get("threads", 8))
        restartable = bool(options.get("restartable", True))
        unbuffered = bool(options.get("unbuffered", True))
        exclude_older = bool(options.get("exclude_older", True))
        exclude_system = bool(options.get("exclude_system", True))
        retry_count = int(options.get("retry_count", 2))
        retry_wait = int(options.get("retry_wait", 2))
        auto_verify = bool(options.get("auto_verify", False))

        ok, msg = self._transfer.start_transfer(
            source_path=source,
            dest_path=dest,
            threads=threads,
            restartable=restartable,
            unbuffered=unbuffered,
            exclude_older=exclude_older,
            exclude_system=exclude_system,
            retry_count=retry_count,
            retry_wait=retry_wait,
            auto_verify=auto_verify,
        )
        return {"success": ok, "message": msg}

    def stop_transfer(self) -> dict[str, Any]:
        ok, msg = self._transfer.stop_transfer()
        try:
            from platforms import get_active_share_lease
            lease = get_active_share_lease()
            if lease:
                network_detector.revoke_network_share(lease.get("share_name", "Transfers"), lease.get("folder_path", ""))
        except Exception:
            pass
        return {"success": ok, "message": msg}

    def get_transfer_telemetry(self) -> dict[str, Any]:
        return self._transfer.get_telemetry()

    def scan_source(self) -> dict[str, Any]:
        self._transfer.start_background_scan()
        return {"success": True, "message": "Source scan started."}

    # ----------------------------------------------------
    # RECEIVER METHODS
    # ----------------------------------------------------
    def start_receiver_monitoring(self, folder_path: str) -> dict[str, Any]:
        ok, msg = self._receiver.start_monitoring(folder_path)
        return {"success": ok, "message": msg}

    def stop_receiver_monitoring(self) -> dict[str, Any]:
        self._receiver.stop_monitoring()
        try:
            from platforms import get_active_share_lease
            lease = get_active_share_lease()
            if lease:
                network_detector.revoke_network_share(lease.get("share_name", "Transfers"), lease.get("folder_path", ""))
        except Exception:
            pass
        return {"success": True, "message": "Receiver monitoring stopped."}

    def get_receiver_status(self) -> dict[str, Any]:
        return self._receiver.get_status()

    def create_share(self, folder_path: str, share_name: str) -> dict[str, Any]:
        ok, msg = network_detector.create_network_share(folder_path, share_name)
        return {"success": ok, "message": msg}

    def revoke_share(self, share_name: str = "Transfers", folder_path: str = "") -> dict[str, Any]:
        ok, msg = network_detector.revoke_network_share(share_name, folder_path)
        return {"success": ok, "message": msg}

    # ----------------------------------------------------
    # VERIFICATION METHODS
    # ----------------------------------------------------
    def start_verification(
        self,
        source_path: str,
        dest_path: str = "",
        mode: str = "metadata",
        workers: int = 4,
    ) -> dict[str, Any]:
        ok, msg = self._verify.start_verification(
            source_path=source_path,
            dest_path=dest_path,
            mode=mode,
            workers=workers,
        )
        return {"success": ok, "message": msg}

    def stop_verification(self) -> dict[str, Any]:
        self._verify.stop_verification()
        return {"success": True, "message": "Verification stopped."}

    def get_verifier_status(self) -> dict[str, Any]:
        return self._verify.get_status()

    def export_verification_report(self) -> dict[str, Any]:
        try:
            path = self._verify.export_html_report()
            if os.path.exists(path):
                if hasattr(os, "startfile"):
                    os.startfile(path)
                elif sys.platform == "darwin":
                    subprocess.run(["open", path], check=False)
                else:
                    subprocess.run(["xdg-open", path], check=False)
            return {"success": True, "path": path}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # ----------------------------------------------------
    # HISTORY & LOGS METHODS
    # ----------------------------------------------------
    def get_history(self, limit: int = 100, filter_type: str = "ALL") -> dict[str, Any]:
        records = history_db.get_combined_history(limit=limit, filter_type=filter_type)
        stats = history_db.get_stats_summary()
        return {"success": True, "records": records, "stats": stats}

    def delete_history_entry(self, category: str, record_id: int) -> dict[str, Any]:
        ok = history_db.delete_history_entry(category, int(record_id))
        return {"success": ok}

    def clear_all_history(self) -> dict[str, Any]:
        ok = history_db.clear_all_history()
        return {"success": ok}
