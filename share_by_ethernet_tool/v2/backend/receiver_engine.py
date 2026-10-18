"""Receiver Engine for Monitoring Incoming Files & Network Share Assist.

Watches the target incoming folder in real-time, calculates inbound write throughput,
tracks new incoming files, and provides network share helpers for Windows.
"""
from __future__ import annotations

import os
import threading
import time
from typing import Any, Callable, Dict, List, Optional


class ReceiverEngine:
    def __init__(self, on_event: Optional[Callable[[str, Any], None]] = None) -> None:
        self.on_event = on_event
        self.target_folder: str = ""
        self.is_monitoring = False
        self._monitor_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

        # Telemetry
        self.total_files = 0
        self.total_bytes = 0
        self.inbound_speed_bps = 0.0
        self.peak_speed_bps = 0.0
        self.recent_files: list[dict[str, Any]] = []
        self._last_snapshot: dict[str, int] = {}  # filepath -> size
        self._last_check_time: float = 0.0

    def emit(self, event_type: str, data: Any) -> None:
        if self.on_event:
            try:
                self.on_event(event_type, data)
            except Exception:
                pass

    def start_monitoring(self, folder_path: str) -> tuple[bool, str]:
        """Start background directory watcher on the incoming folder."""
        if not os.path.exists(folder_path):
            try:
                os.makedirs(folder_path, exist_ok=True)
            except Exception as e:
                return False, f"Could not create folder: {e}"

        self.target_folder = os.path.abspath(folder_path)
        self.is_monitoring = True
        self._stop_event.clear()
        self.inbound_speed_bps = 0.0
        self.peak_speed_bps = 0.0

        if self._monitor_thread and self._monitor_thread.is_alive():
            return True, "Monitoring already running."

        self._monitor_thread = threading.Thread(
            target=self._monitor_worker, daemon=True, name="ReceiverWatcherThread"
        )
        self._monitor_thread.start()
        return True, f"Started monitoring {self.target_folder}"

    def stop_monitoring(self) -> None:
        """Stop background watcher."""
        self._stop_event.set()
        self.is_monitoring = False

    def _monitor_worker(self) -> None:
        self._last_check_time = time.time()
        prev_bytes = 0

        while not self._stop_event.is_set():
            time.sleep(1.0)
            if not os.path.exists(self.target_folder):
                continue

            current_files_count = 0
            current_bytes_total = 0
            current_snapshot: dict[str, int] = {}
            file_entries: list[tuple[float, str, int]] = []  # (mtime, rel_path, size)

            try:
                for root, _, files in os.walk(self.target_folder):
                    for f in files:
                        full_path = os.path.join(root, f)
                        try:
                            st = os.stat(full_path)
                            size = st.st_size
                            mtime = st.st_mtime
                            current_files_count += 1
                            current_bytes_total += size
                            current_snapshot[full_path] = size
                            rel_path = os.path.relpath(full_path, self.target_folder)
                            file_entries.append((mtime, rel_path, size))
                        except (OSError, PermissionError):
                            continue
            except Exception:
                pass

            now = time.time()
            delta_t = max(0.1, now - self._last_check_time)
            delta_bytes = max(0, current_bytes_total - prev_bytes)

            self.inbound_speed_bps = delta_bytes / delta_t
            if self.inbound_speed_bps > self.peak_speed_bps:
                self.peak_speed_bps = self.inbound_speed_bps

            self.total_files = current_files_count
            self.total_bytes = current_bytes_total
            prev_bytes = current_bytes_total
            self._last_check_time = now

            # Sort files by most recently modified
            file_entries.sort(key=lambda x: x[0], reverse=True)
            self.recent_files = [
                {
                    "path": entry[1],
                    "size": entry[2],
                    "mtime": entry[0],
                }
                for entry in file_entries[:15]
            ]

            payload = {
                "folder": self.target_folder,
                "is_monitoring": self.is_monitoring,
                "total_files": self.total_files,
                "total_bytes": self.total_bytes,
                "inbound_speed_bps": self.inbound_speed_bps,
                "peak_speed_bps": self.peak_speed_bps,
                "recent_files": self.recent_files,
            }
            self.emit("receiver_update", payload)

    def get_status(self) -> dict[str, Any]:
        return {
            "folder": self.target_folder,
            "is_monitoring": self.is_monitoring,
            "total_files": self.total_files,
            "total_bytes": self.total_bytes,
            "inbound_speed_bps": self.inbound_speed_bps,
            "peak_speed_bps": self.peak_speed_bps,
            "recent_files": self.recent_files,
        }
