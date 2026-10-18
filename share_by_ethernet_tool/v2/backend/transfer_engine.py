"""Transfer Engine and Process Manager for Robocopy with Kernel I/O Telemetry.

Features:
- Windows Robocopy process orchestrator with safe resume (/E /Z /J /XO /FFT).
- Win32 kernel I/O counter sampling (GetProcessIoCounters) for accurate dual-deck speed metrics.
- Process identity validation via FILETIME stamps to prevent PID collisions.
- Dynamic throughput sparkline data buffer.
- Persistent logging to SQLite history database.
"""
from __future__ import annotations

import csv
import json
import os
import queue
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from platforms import get_platform_adapter
from . import history_db

STATE_FILE = os.path.join(tempfile.gettempdir(), "tshare_v2_transfer_state.json")
MUTEX_NAME = r"Local\TShare_V2_TransferMonitor"


def get_process_identity(pid: int) -> tuple[str, int] | None:
    """Return (executable_path, creation_filetime_stamp) for a running process."""
    return get_platform_adapter().get_process_identity(pid)


def query_process_io_counters(pid: int) -> tuple[int, int] | None:
    """Return (read_bytes, write_bytes) from kernel for the given PID."""
    return get_platform_adapter().query_process_io_speed(pid)


def read_saved_state() -> dict[str, Any] | None:
    """Read saved process state from STATE_FILE if the process is still alive and matches."""
    if not os.path.exists(STATE_FILE):
        return None
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        pid = int(data.get("pid", 0))
        stamp = int(data.get("created", 0))
        identity = get_process_identity(pid)
        if identity and (not stamp or identity[1] == stamp):
            exe_name = os.path.basename(identity[0]).casefold()
            if "robocopy" in exe_name or "rsync" in exe_name:
                return data
    except Exception:
        pass
    try:
        os.remove(STATE_FILE)
    except OSError:
        pass
    return None


def write_saved_state(state: dict[str, Any]) -> None:
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except OSError:
        pass


def clear_saved_state() -> None:
    try:
        if os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)
    except OSError:
        pass


def check_running_transfer_processes() -> list[dict[str, Any]]:
    """Query system to find all currently running robocopy or rsync processes."""
    found: list[dict[str, Any]] = []
    if sys.platform.startswith("win"):
        try:
            raw = subprocess.check_output(
                ["tasklist.exe", "/FI", "IMAGENAME eq robocopy.exe", "/FO", "CSV", "/NH"],
                text=True,
                encoding="mbcs",
                errors="replace",
                stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                timeout=6,
            )
            rows = list(csv.reader(raw.splitlines()))
            for row in rows:
                if row and len(row) > 1 and row[0].casefold() == "robocopy.exe":
                    try:
                        pid = int(row[1])
                        found.append({"pid": pid, "session": row[2] if len(row) > 2 else ""})
                    except ValueError:
                        pass
        except Exception:
            pass
    else:
        try:
            raw = subprocess.check_output(["pgrep", "-f", "rsync"], text=True, stderr=subprocess.DEVNULL)
            for line in raw.splitlines():
                line = line.strip()
                if line.isdigit():
                    found.append({"pid": int(line), "session": "posix"})
        except Exception:
            pass
    return found


def extract_host_from_path(path_str: str) -> str | None:
    """Extract hostname or IP address from a UNC or network path."""
    m = re.match(r"^[\\/]{2}([^\\/]+)", path_str)
    return m.group(1) if m else None


def format_bytes(value: int | float | None) -> str:
    if value is None or value < 0:
        return "0 B"
    val = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if val < 1024.0 or unit == "TiB":
            return f"{val:.1f} {unit}" if unit != "B" else f"{int(value):,} B"
        val /= 1024.0
    return f"{int(value):,} B"


def format_duration(seconds: float) -> str:
    seconds = max(0, int(seconds))
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours:02}:{minutes:02}:{secs:02}"


def explain_exit_code(code: int) -> tuple[bool, str]:
    """Translate platform transfer return codes to human readable results."""
    if sys.platform.startswith("win"):
        explanations = {
            0: "No files needed copying (Destination is already 100% up-to-date).",
            1: "All files copied successfully.",
            2: "Extra files present in destination; no source files needed copying.",
            3: "Files copied successfully (extra files exist in destination).",
            4: "Some mismatched files or directories were detected.",
            5: "Some files copied; some mismatched files detected.",
            6: "Extra files and mismatched files exist in destination.",
            7: "Files copied; file mismatches and extra files detected.",
            8: "Failed copies: Several files could not be copied.",
            16: "Fatal error: Robocopy did not copy files (check permissions or syntax).",
        }
        desc = explanations.get(code, f"Robocopy finished with exit code {code}.")
        is_success = code < 8
        return is_success, desc
    else:
        explanations = {
            0: "rsync: All files copied successfully.",
            24: "rsync: Partial transfer due to vanished source files (non-fatal).",
            1: "rsync: Syntax or usage error.",
            2: "rsync: Protocol incompatibility.",
            3: "rsync: Errors selecting input/output files or dirs.",
            4: "rsync: Requested action not supported.",
            5: "rsync: Error starting client-server protocol.",
            10: "rsync: Error in socket I/O.",
            11: "rsync: Error in file I/O.",
            12: "rsync: Error in rsync protocol data stream.",
            13: "rsync: Errors with program diagnostics.",
            14: "rsync: Error in IPC code.",
            20: "rsync: Received SIGUSR1 or SIGINT.",
            21: "rsync: Some error returned by waitpid().",
            22: "rsync: Error allocating core memory buffers.",
            23: "rsync: Partial transfer due to error.",
            25: "rsync: The --max-delete limit was reached.",
            30: "rsync: Timeout in data send/receive.",
            35: "rsync: Timeout waiting for daemon connection.",
        }
        desc = explanations.get(code, f"rsync finished with exit code {code}.")
        is_success = code in (0, 24)
        return is_success, desc


class TransferEngine:
    def __init__(self, on_event: Optional[Callable[[str, Any], None]] = None) -> None:
        self.on_event = on_event
        self.child: subprocess.Popen | None = None
        self.managed_pid: int | None = None
        self.managed_created: int | None = None
        self.transfer_start_time: float | None = None
        self.source_path: str = ""
        self.dest_path: str = ""

        # Scan & Progress metrics
        self.scan_busy = False
        self.source_total_bytes: int = 0
        self.source_total_files: int = 0
        self.dest_copied_bytes: int = 0
        self.dest_copied_files: int = 0
        self.current_file: str = "Ready"
        self.current_folder: str = "Source"

        # Speed telemetry
        self.last_read_bytes: int = 0
        self.last_write_bytes: int = 0
        self.last_sample_time: float = time.time()
        self.current_upload_speed: float = 0.0
        self.current_download_speed: float = 0.0
        self.peak_speed_mbps: float = 0.0

        # Sparkline buffer
        self.speed_history: list[dict[str, Any]] = []
        self.max_history_points = 60

        # ETA metrics
        self.eta_seconds: float = 0.0
        self.smoothed_speed_bps: float = 0.0
        self._speed_window: list[tuple[float, float]] = []

        # Robocopy options
        self.threads = 8
        self.restartable = True
        self.unbuffered = True
        self.exclude_older = True
        self.exclude_system = True
        self.retry_count = 2
        self.retry_wait = 2
        self.auto_verify_on_finish = False

        # Cached reachability and storage metrics (updated in background)
        self.source_reachable = False
        self.dest_reachable = False
        self.source_disk: dict[str, Any] | None = None
        self.dest_disk: dict[str, Any] | None = None
        self._last_disk_sample_time: float = 0.0

        # Logs & Threads
        self.log_queue: queue.Queue[tuple[str, str]] = queue.Queue(maxsize=1000)
        self._reader_thread: threading.Thread | None = None
        self._watcher_thread: threading.Thread | None = None
        self._scan_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._exit_code: int | None = None

        self._check_for_running_instance()

    def emit(self, event_type: str, data: Any) -> None:
        if self.on_event:
            try:
                self.on_event(event_type, data)
            except Exception:
                pass

    def _log(self, level: str, text: str) -> None:
        try:
            self.log_queue.put_nowait((level, text))
        except queue.Full:
            pass
        self.emit("log", {"level": level, "text": text})

    def _check_for_running_instance(self) -> None:
        saved = read_saved_state()
        if saved:
            self.managed_pid = int(saved["pid"])
            self.managed_created = int(saved["created"])
            self.source_path = saved.get("source", "")
            self.dest_path = saved.get("dest", "")
            self.transfer_start_time = float(saved.get("start_time", time.time()))
            self._start_watcher_thread()
            self._log("info", f"Re-attached to active Robocopy process (PID: {self.managed_pid})")

    def start_transfer(
        self,
        source_path: str,
        dest_path: str,
        threads: int = 8,
        restartable: bool = True,
        unbuffered: bool = True,
        exclude_older: bool = True,
        exclude_system: bool = True,
        retry_count: int = 2,
        retry_wait: int = 2,
        auto_verify: bool = False,
    ) -> tuple[bool, str]:
        """Initiate high-speed Robocopy file transfer with process isolation."""
        if self.is_managed_running():
            return False, f"Transfer is already active (PID: {self.managed_pid})."

        source_clean = source_path.strip().strip('"').rstrip("\\/")
        dest_clean = dest_path.strip().strip('"').rstrip("\\/")

        if not source_clean or not dest_clean:
            return False, "Source and Destination paths must not be empty."

        if not os.path.exists(source_clean):
            return False, f"Source path does not exist or is inaccessible: {source_clean}"

        try:
            os.makedirs(dest_clean, exist_ok=True)
        except Exception as e:
            return False, f"Cannot access/create destination folder: {e}"

        self.source_path = source_clean
        self.dest_path = dest_clean
        self.threads = max(1, min(128, threads))
        self.restartable = restartable
        self.unbuffered = unbuffered
        self.exclude_older = exclude_older
        self.exclude_system = exclude_system
        self.retry_count = retry_count
        self.retry_wait = retry_wait
        self.auto_verify_on_finish = auto_verify

        # Reset counters
        self.source_total_bytes = 0
        self.source_total_files = 0
        self.dest_copied_bytes = 0
        self.dest_copied_files = 0
        self.current_upload_speed = 0.0
        self.current_download_speed = 0.0
        self.peak_speed_mbps = 0.0
        self.speed_history.clear()
        self._speed_window.clear()
        self.smoothed_speed_bps = 0.0
        self.eta_seconds = 0.0
        self._exit_code = None

        # Build optimal platform transfer command
        from platforms import get_platform_adapter
        adapter = get_platform_adapter()
        cmd = adapter.build_transfer_command(
            source=self.source_path,
            dest=self.dest_path,
            threads=self.threads,
            restartable=self.restartable,
            unbuffered=self.unbuffered,
            exclude_older=self.exclude_older,
            exclude_system=self.exclude_system,
            retry_count=self.retry_count,
            retry_wait=self.retry_wait,
        )

        self._log("info", f"Executing {adapter.get_os_name().capitalize()} Transfer Process: {' '.join(cmd)}")
        self.transfer_start_time = time.time()
        self._stop_event.clear()

        encoding = "mbcs" if sys.platform.startswith("win") else "utf-8"

        try:
            self.child = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding=encoding,
                errors="replace",
                bufsize=1,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            self.managed_pid = self.child.pid

            # Record creation identity
            identity = get_process_identity(self.managed_pid)
            self.managed_created = identity[1] if identity else 0

            write_saved_state(
                {
                    "pid": self.managed_pid,
                    "created": self.managed_created,
                    "source": self.source_path,
                    "dest": self.dest_path,
                    "start_time": self.transfer_start_time,
                }
            )

            # Start background reader and telemetry
            self._reader_thread = threading.Thread(
                target=self._stream_reader, args=(self.child,), daemon=True, name="TransferStreamReader"
            )
            self._reader_thread.start()

            self._start_watcher_thread()
            self.start_background_scan()

            return True, f"{adapter.get_os_name().capitalize()} transfer started (PID: {self.managed_pid})"

        except Exception as exc:
            self._log("error", f"Failed to launch transfer: {exc}")
            return False, str(exc)

    def stop_transfer(self) -> tuple[bool, str]:
        """Gracefully terminate active transfer process."""
        self._stop_event.set()
        clear_saved_state()

        if self.child and self.child.poll() is None:
            try:
                self.child.terminate()
                self._log("warning", "Termination signal sent to transfer process.")
                time.sleep(0.3)
                if self.child.poll() is None:
                    self.child.kill()
                    self._log("warning", "Transfer process forcefully killed.")
            except Exception as e:
                self._log("error", f"Error stopping child: {e}")

        if self.managed_pid:
            try:
                if sys.platform.startswith("win"):
                    subprocess.run(
                        ["taskkill.exe", "/F", "/PID", str(self.managed_pid)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=3,
                    )
                else:
                    import signal
                    os.kill(self.managed_pid, signal.SIGTERM)
                    time.sleep(0.2)
                    os.kill(self.managed_pid, signal.SIGKILL)
            except Exception:
                pass

        self._record_history("INTERRUPTED", exit_code=-1, notes="Manually stopped by user.")
        self.managed_pid = None
        self.child = None
        return True, "Transfer stopped."

    def is_managed_running(self) -> bool:
        """Check whether managed transfer PID is alive."""
        if not self.managed_pid:
            return False
        if self.child:
            return self.child.poll() is None
        identity = get_process_identity(self.managed_pid)
        if not identity:
            return False
        exe_name = os.path.basename(identity[0]).casefold()
        is_transfer = "robocopy" in exe_name or "rsync" in exe_name
        return is_transfer and (not self.managed_created or identity[1] == self.managed_created)

    def _stream_reader(self, proc: subprocess.Popen) -> None:
        """Parse Robocopy and rsync output in real-time."""
        file_regex = re.compile(r"^\s*([0-9,]+)\s+(.+)$")
        new_file_regex = re.compile(r"^\s*\*?New File\s+([0-9,]+)\s+(.+)$", re.IGNORECASE)
        rsync_progress_regex = re.compile(r"^\s*([0-9,]+)\s+([0-9]+)%\s+([0-9.]+[A-Za-z]+/s)", re.IGNORECASE)

        try:
            for line in iter(proc.stdout.readline, ""):
                line_str = line.strip()
                if not line_str:
                    continue

                m_new = new_file_regex.match(line_str)
                m_plain = file_regex.match(line_str)
                m_rsync = rsync_progress_regex.match(line_str)

                if m_new:
                    size_str = m_new.group(1).replace(",", "")
                    filename = m_new.group(2).strip()
                    try:
                        self.dest_copied_bytes += int(size_str)
                        self.dest_copied_files += 1
                        self.current_file = filename
                    except ValueError:
                        pass
                    self._log("info", f"Copying: {filename} ({format_bytes(int(size_str))})")
                elif m_plain and not line_str.startswith("Total") and not line_str.startswith("Dirs"):
                    size_str = m_plain.group(1).replace(",", "")
                    filename = m_plain.group(2).strip()
                    try:
                        sz = int(size_str)
                        self.dest_copied_bytes += sz
                        self.dest_copied_files += 1
                        self.current_file = filename
                        self._log("info", f"Copied: {filename} ({format_bytes(sz)})")
                    except ValueError:
                        self._log("info", line_str)
                elif m_rsync:
                    copied_str = m_rsync.group(1).replace(",", "")
                    try:
                        self.dest_copied_bytes = int(copied_str)
                    except ValueError:
                        pass
                elif "ERROR" in line_str.upper() or "FAILED" in line_str.upper():
                    self._log("error", line_str)
                else:
                    self._log("info", line_str)

            proc.stdout.close()
            proc.wait()
            self._exit_code = proc.returncode
            self._on_robocopy_exit(self._exit_code)
        except Exception as e:
            self._log("error", f"Stream reader error: {e}")

    def _on_robocopy_exit(self, code: int) -> None:
        clear_saved_state()
        is_success, msg = explain_exit_code(code)
        status_str = "COMPLETED" if is_success else "FAILED"
        os_name = get_platform_adapter().get_os_name().capitalize()
        self._log("info" if is_success else "error", f"{os_name} transfer finished: {msg} (Code: {code})")

        duration = time.time() - (self.transfer_start_time or time.time())
        avg_speed_mbps = (self.dest_copied_bytes / (1024 * 1024)) / max(0.5, duration)

        self._record_history(
            status_str,
            exit_code=code,
            notes=msg,
            avg_speed=avg_speed_mbps,
            peak_speed=self.peak_speed_mbps,
        )

        self.emit(
            "transfer_finished",
            {
                "success": is_success,
                "exit_code": code,
                "message": msg,
                "auto_verify": self.auto_verify_on_finish and is_success,
                "source": self.source_path,
                "dest": self.dest_path,
            },
        )

    def _record_history(
        self,
        status: str,
        exit_code: int = 0,
        notes: str = "",
        avg_speed: float = 0.0,
        peak_speed: float = 0.0,
    ) -> None:
        try:
            duration = time.time() - (self.transfer_start_time or time.time())
            if avg_speed == 0.0 and duration > 0 and self.dest_copied_bytes > 0:
                avg_speed = (self.dest_copied_bytes / (1024 * 1024)) / duration

            history_db.add_transfer_record(
                task_type="SEND",
                source_path=self.source_path,
                dest_path=self.dest_path,
                total_files=self.dest_copied_files or self.source_total_files,
                total_bytes=self.dest_copied_bytes or self.source_total_bytes,
                duration_seconds=duration,
                avg_speed_mbps=avg_speed,
                peak_speed_mbps=peak_speed or self.peak_speed_mbps,
                status=status,
                exit_code=exit_code,
                notes=notes,
            )
        except Exception:
            pass

    def _start_watcher_thread(self) -> None:
        if self._watcher_thread and self._watcher_thread.is_alive():
            return
        self._watcher_thread = threading.Thread(
            target=self._watcher_worker, daemon=True, name="TransferWatcherWorker"
        )
        self._watcher_thread.start()

    def _watcher_worker(self) -> None:
        """Poll kernel IO counters and compute speeds every 800ms."""
        self.last_sample_time = time.time()
        self.last_read_bytes = 0
        self.last_write_bytes = 0

        while self.is_managed_running() and not self._stop_event.is_set():
            time.sleep(0.8)
            now = time.time()
            dt = max(0.1, now - self.last_sample_time)

            if self.managed_pid:
                counters = query_process_io_counters(self.managed_pid)
                if counters:
                    r_bytes, w_bytes = counters
                    if self.last_read_bytes > 0:
                        delta_r = max(0, r_bytes - self.last_read_bytes)
                        delta_w = max(0, w_bytes - self.last_write_bytes)
                        self.current_upload_speed = delta_r / dt
                        self.current_download_speed = delta_w / dt
                    self.last_read_bytes = r_bytes
                    self.last_write_bytes = w_bytes

            # Track peak speed
            speed_mbps = self.current_download_speed / (1024 * 1024)
            if speed_mbps > self.peak_speed_mbps:
                self.peak_speed_mbps = speed_mbps

            # Sparkline history
            self.speed_history.append(
                {
                    "t": round(now - (self.transfer_start_time or now), 1),
                    "upload_mbps": round(self.current_upload_speed / (1024 * 1024), 2),
                    "download_mbps": round(speed_mbps, 2),
                }
            )
            if len(self.speed_history) > self.max_history_points:
                self.speed_history.pop(0)

            # ETA calculation
            self._speed_window.append((now, self.current_download_speed))
            if len(self._speed_window) > 10:
                self._speed_window.pop(0)

            if self._speed_window:
                avg_speed = sum(s for _, s in self._speed_window) / len(self._speed_window)
                self.smoothed_speed_bps = avg_speed
                rem_bytes = max(0, self.source_total_bytes - self.dest_copied_bytes)
                if avg_speed > 1024:
                    self.eta_seconds = rem_bytes / avg_speed
                else:
                    self.eta_seconds = 0.0

            # Periodic background disk capacity check (every 5 seconds)
            self._update_reachability_and_disk()

            self.last_sample_time = now

    def _update_reachability_and_disk(self) -> None:
        """Query disk capacities and path reachability in background without blocking telemetry."""
        now = time.time()
        if self._last_disk_sample_time > 0 and (now - self._last_disk_sample_time < 5.0):
            return
        self._last_disk_sample_time = now

        if self.source_path:
            try:
                self.source_reachable = os.path.exists(self.source_path)
                if self.source_reachable:
                    du = shutil.disk_usage(self.source_path)
                    self.source_disk = {"total": du.total, "used": du.used, "free": du.free}
                else:
                    self.source_disk = None
            except Exception:
                self.source_reachable = False
                self.source_disk = None
        else:
            self.source_reachable = False
            self.source_disk = None

        if self.dest_path:
            try:
                self.dest_reachable = os.path.exists(self.dest_path)
                if self.dest_reachable:
                    du = shutil.disk_usage(self.dest_path)
                    self.dest_disk = {"total": du.total, "used": du.used, "free": du.free}
                else:
                    self.dest_disk = None
            except Exception:
                self.dest_reachable = False
                self.dest_disk = None
        else:
            self.dest_reachable = False
            self.dest_disk = None

    def start_background_scan(self) -> None:
        """Run non-blocking file count & byte calculation on source."""
        if self.scan_busy:
            return
        self._scan_thread = threading.Thread(
            target=self._scan_worker, daemon=True, name="TransferScanWorker"
        )
        self._scan_thread.start()

    def _scan_worker(self) -> None:
        self.scan_busy = True
        try:
            total_b = 0
            total_f = 0
            if os.path.exists(self.source_path):
                for root, _, files in os.walk(self.source_path):
                    for f in files:
                        p = os.path.join(root, f)
                        try:
                            total_b += os.path.getsize(p)
                            total_f += 1
                        except OSError:
                            pass
            self.source_total_bytes = total_b
            self.source_total_files = total_f
        except Exception:
            pass
        finally:
            self.scan_busy = False

    def get_telemetry(self) -> dict[str, Any]:
        """Aggregate all real-time stats for the GUI (Instant 0ms in-memory read)."""
        is_running = self.is_managed_running()
        now = time.time()
        elapsed = (now - self.transfer_start_time) if (is_running and self.transfer_start_time) else 0.0

        pct = 0.0
        if self.source_total_bytes > 0:
            pct = min(100.0, round((self.dest_copied_bytes / self.source_total_bytes) * 100.0, 1))

        # Initial background sample if not yet done
        if self._last_disk_sample_time == 0.0:
            threading.Thread(target=self._update_reachability_and_disk, daemon=True).start()

        dest_mbps = round((self.current_download_speed / (1024 * 1024)), 2)

        return {
            "is_running": is_running,
            "is_managed_running": is_running,
            "managed_pid": self.managed_pid,
            "source_path": self.source_path,
            "dest_path": self.dest_path,
            "source_reachable": self.source_reachable,
            "dest_reachable": self.dest_reachable,
            "source_disk": self.source_disk,
            "dest_disk": self.dest_disk,
            "current_file": self.current_file,
            "current_folder": os.path.basename(self.source_path.rstrip(r"\/")) or "Source",
            "source_total_bytes": self.source_total_bytes,
            "source_total_files": self.source_total_files,
            "dest_copied_bytes": self.dest_copied_bytes,
            "dest_copied_files": self.dest_copied_files,
            "progress_percent": pct,
            "overall_progress_percent": pct,
            "upload_speed_bps": self.current_upload_speed,
            "download_speed_bps": self.current_download_speed,
            "source_upload_bps": self.current_upload_speed,
            "dest_download_bps": self.current_download_speed,
            "source_upload_formatted": format_bytes(self.current_upload_speed) + "/s",
            "dest_download_formatted": format_bytes(self.current_download_speed) + "/s",
            "upload_speed_display": format_bytes(self.current_upload_speed) + "/s",
            "download_speed_display": format_bytes(self.current_download_speed) + "/s",
            "dest_write_speed_mbps": dest_mbps,
            "peak_speed_mbps": round(self.peak_speed_mbps, 2),
            "elapsed_seconds": int(elapsed),
            "elapsed_display": format_duration(elapsed),
            "elapsed_formatted": format_duration(elapsed),
            "eta_seconds": int(self.eta_seconds),
            "eta_display": format_duration(self.eta_seconds) if self.eta_seconds > 0 else "--:--:--",
            "eta_formatted": format_duration(self.eta_seconds) if self.eta_seconds > 0 else "--:--:--",
            "speed_history": self.speed_history,
            "scan_busy": self.scan_busy,
        }
