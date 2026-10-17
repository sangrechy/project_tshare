"""Transfer Engine and Process Manager for Robocopy.

Provides dual upload/download speed tracking via Windows kernel IO counters,
network latency measurement, safe resume, unbuffered multi-threaded transfers,
real-time log streaming, speed/ETA metrics, and Windows process identity verification.
"""
from __future__ import annotations

import csv
import ctypes
import json
import os
import queue
import re
import shutil
import socket
import subprocess
import tempfile
import threading
import time
from datetime import datetime
from typing import Callable, Any, Dict, Optional, Tuple, List

DEFAULT_SOURCE = os.environ.get("TSHARE_SOURCE", r"\\192.168.1.X\SharedFolder")
DEFAULT_DEST = os.environ.get("TSHARE_DEST", r"D:\Transfer")
STATE_FILE = os.path.join(tempfile.gettempdir(), "tshare_robocopy_transfer_state.json")
MUTEX_NAME = r"Local\TShare_RobocopyTransferMonitor"


class FILETIME(ctypes.Structure):
    _fields_ = [("low", ctypes.c_uint32), ("high", ctypes.c_uint32)]


class IO_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("ReadOperationCount", ctypes.c_uint64),
        ("WriteOperationCount", ctypes.c_uint64),
        ("OtherOperationCount", ctypes.c_uint64),
        ("ReadTransferCount", ctypes.c_uint64),
        ("WriteTransferCount", ctypes.c_uint64),
        ("OtherTransferCount", ctypes.c_uint64),
    ]


def get_process_identity(pid: int) -> tuple[str, int] | None:
    """Return (executable_path, creation_filetime_stamp) for a running process."""
    kernel = ctypes.windll.kernel32
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    kernel.QueryFullProcessImageNameW.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_wchar_p,
        ctypes.POINTER(ctypes.c_uint32),
    ]
    kernel.GetProcessTimes.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(FILETIME),
        ctypes.POINTER(FILETIME),
        ctypes.POINTER(FILETIME),
        ctypes.POINTER(FILETIME),
    ]
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]

    handle = kernel.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        return None
    try:
        buf = ctypes.create_unicode_buffer(32768)
        size = ctypes.c_uint32(len(buf))
        if not kernel.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            return None
        created, exited, kernel_t, user_t = FILETIME(), FILETIME(), FILETIME(), FILETIME()
        if not kernel.GetProcessTimes(
            handle,
            ctypes.byref(created),
            ctypes.byref(exited),
            ctypes.byref(kernel_t),
            ctypes.byref(user_t),
        ):
            return None
        stamp = (created.high << 32) | created.low
        return buf.value, stamp
    finally:
        kernel.CloseHandle(handle)


def query_process_io_counters(pid: int) -> tuple[int, int] | None:
    """Return (read_bytes, write_bytes) from Windows kernel for the given PID."""
    kernel = ctypes.windll.kernel32
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    kernel.GetProcessIoCounters.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    kernel.GetProcessIoCounters.restype = ctypes.c_int
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]

    # PROCESS_QUERY_INFORMATION (0x0400) or PROCESS_QUERY_LIMITED_INFORMATION (0x1000)
    handle = kernel.OpenProcess(0x0400, False, pid)
    if not handle:
        handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        return None
    try:
        io = IO_COUNTERS()
        if kernel.GetProcessIoCounters(handle, ctypes.byref(io)):
            return io.ReadTransferCount, io.WriteTransferCount
        return None
    finally:
        kernel.CloseHandle(handle)


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
        if identity and os.path.basename(identity[0]).casefold() == "robocopy.exe" and identity[1] == stamp:
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


def check_running_robocopy_processes() -> list[dict[str, Any]]:
    """Query tasklist to find all currently running robocopy.exe processes."""
    found: list[dict[str, Any]] = []
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
    return found


def extract_host_from_path(path_str: str) -> str | None:
    """Extract hostname or IP address from a UNC path (e.g. \\\\192.168.1.X\\Share)."""
    m = re.match(r"^\\\\([^\\]+)", path_str)
    return m.group(1) if m else None


def measure_smb_latency(host: str | None = None, port: int = 445, timeout: float = 1.0) -> float | None:
    """Measure roundtrip TCP connect time to SMB port in milliseconds."""
    if not host:
        return None
    t0 = time.time()
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        s.close()
        return round((time.time() - t0) * 1000.0, 1)
    except Exception:
        return None


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
    """Translate Robocopy bitmask return codes to human readable results."""
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


class TransferEngine:
    def __init__(self, on_event: Optional[Callable[[str, Any], None]] = None) -> None:
        self.on_event = on_event
        self.child: subprocess.Popen | None = None
        self.managed_pid: int | None = None
        self.managed_created: int | None = None
        self.transfer_start_time: float | None = None
        self.source_path = DEFAULT_SOURCE
        self.dest_path = DEFAULT_DEST

        # Telemetry metrics
        self.scan_busy = False
        self.source_total_bytes: int = 0
        self.source_total_files: int = 0
        self.dest_copied_bytes: int = 0
        self.dest_copied_files: int = 0
        self.current_file: str = "Ready"
        self.current_folder: str = os.path.basename(self.source_path.rstrip(r"\/")) or "Source"

        # DUAL SPEED MEASUREMENTS:
        # 1. Source Upload / Read throughput (from network share)
        # 2. Destination Download / Write throughput (to local drive)
        self.source_upload_speed: float = 0.0  # Bytes/sec
        self.dest_download_speed: float = 0.0  # Bytes/sec
        self.last_io_sample: tuple[float, int, int] | None = None  # (time, read_bytes, write_bytes)

        # Network latency
        self.smb_latency_ms: float | None = None
        self._last_latency_check: float = 0.0

        # Sparkline history (last 30 seconds of dual speeds)
        self.speed_history: list[dict[str, float]] = []

        self._lock = threading.Lock()

        # Check existing saved state
        saved = read_saved_state()
        if saved:
            self.managed_pid = int(saved["pid"])
            self.managed_created = int(saved["created"])
            self.source_path = saved.get("source", DEFAULT_SOURCE)
            self.dest_path = saved.get("dest", DEFAULT_DEST)
            self.transfer_start_time = float(saved.get("started_at", time.time()))

    def emit(self, event_type: str, data: Any) -> None:
        if self.on_event:
            try:
                self.on_event(event_type, data)
            except Exception:
                pass

    def _sample_kernel_io_speeds(self) -> None:
        """Sample Windows kernel IO counters to calculate true upload & download speeds."""
        pid = self.managed_pid
        if not pid:
            self.source_upload_speed = 0.0
            self.dest_download_speed = 0.0
            return

        io_data = query_process_io_counters(pid)
        now = time.time()
        if not io_data:
            return

        read_bytes, write_bytes = io_data

        if self.last_io_sample:
            prev_t, prev_r, prev_w = self.last_io_sample
            dt = now - prev_t
            if dt > 0.3:
                up_speed = max(0.0, (read_bytes - prev_r) / dt)
                down_speed = max(0.0, (write_bytes - prev_w) / dt)

                # Smooth with exponential moving average
                self.source_upload_speed = 0.7 * up_speed + 0.3 * self.source_upload_speed
                self.dest_download_speed = 0.7 * down_speed + 0.3 * self.dest_download_speed

                self.last_io_sample = (now, read_bytes, write_bytes)

                # Record sparkline history (keep last 30 samples)
                with self._lock:
                    self.speed_history.append({
                        "t": round(now, 1),
                        "upload": round(self.source_upload_speed / (1024 * 1024), 2),
                        "download": round(self.dest_download_speed / (1024 * 1024), 2),
                    })
                    if len(self.speed_history) > 30:
                        self.speed_history.pop(0)
        else:
            self.last_io_sample = (now, read_bytes, write_bytes)

    def get_system_status(self) -> dict[str, Any]:
        """Fetch connectivity, disk usage, active robocopy processes, and engine state."""
        src_reachable = False
        src_disk = None
        dst_reachable = False
        dst_disk = None

        # Sample IO speeds
        self._sample_kernel_io_speeds()

        # Periodic latency check
        if time.time() - self._last_latency_check > 3.0:
            self._last_latency_check = time.time()
            self.smb_latency_ms = measure_smb_latency(extract_host_from_path(self.source_path))

        try:
            if os.path.exists(self.source_path):
                src_reachable = True
                u = shutil.disk_usage(self.source_path)
                src_disk = {"total": u.total, "used": u.used, "free": u.free}
        except Exception:
            pass

        try:
            if os.path.exists(self.dest_path):
                dst_reachable = True
                u = shutil.disk_usage(self.dest_path)
                dst_disk = {"total": u.total, "used": u.used, "free": u.free}
            else:
                root = os.path.splitdrive(self.dest_path)[0] + "\\"
                if os.path.exists(root):
                    u = shutil.disk_usage(root)
                    dst_disk = {"total": u.total, "used": u.used, "free": u.free}
        except Exception:
            pass

        # Managed process status
        is_managed_running = False
        if self.child and self.child.poll() is None:
            is_managed_running = True
        elif self.managed_pid and read_saved_state():
            is_managed_running = True
        else:
            self.managed_pid = None
            self.managed_created = None
            self.source_upload_speed = 0.0
            self.dest_download_speed = 0.0

        all_procs = check_running_robocopy_processes()
        external_procs = [p for p in all_procs if p["pid"] != self.managed_pid]

        elapsed = 0.0
        if is_managed_running and self.transfer_start_time:
            elapsed = time.time() - self.transfer_start_time

        # Calculate progress percent
        pct = 0.0
        if self.source_total_bytes > 0:
            pct = min(100.0, (self.dest_copied_bytes / self.source_total_bytes) * 100.0)

        # ETA calculation based on destination download/write speed or source upload speed
        effective_speed = max(self.dest_download_speed, self.source_upload_speed)
        eta_seconds = 0
        if is_managed_running and effective_speed > 1024:
            remaining_bytes = max(0, self.source_total_bytes - self.dest_copied_bytes)
            if remaining_bytes > 0:
                eta_seconds = int(remaining_bytes / effective_speed)

        return {
            "source_path": self.source_path,
            "dest_path": self.dest_path,
            "source_reachable": src_reachable,
            "dest_reachable": dst_reachable,
            "source_disk": src_disk,
            "dest_disk": dst_disk,
            "smb_latency_ms": self.smb_latency_ms,
            "is_managed_running": is_managed_running,
            "managed_pid": self.managed_pid,
            "external_processes": external_procs,
            "scan_busy": self.scan_busy,
            "source_total_bytes": self.source_total_bytes,
            "source_total_files": self.source_total_files,
            "dest_copied_bytes": self.dest_copied_bytes,
            "dest_copied_files": self.dest_copied_files,
            "progress_percent": round(pct, 1),
            # SEPARATE DUAL SPEEDS:
            "source_upload_bps": int(self.source_upload_speed),
            "source_upload_formatted": f"{format_bytes(self.source_upload_speed)}/s",
            "dest_download_bps": int(self.dest_download_speed),
            "dest_download_formatted": f"{format_bytes(self.dest_download_speed)}/s",
            "current_file": self.current_file,
            "current_folder": self.current_folder,
            "elapsed_seconds": int(elapsed),
            "elapsed_formatted": format_duration(elapsed),
            "eta_seconds": eta_seconds,
            "eta_formatted": format_duration(eta_seconds) if eta_seconds > 0 else ("Complete" if pct >= 100 else "—"),
            "speed_history": list(self.speed_history),
        }

    def start_background_scan(self, fast_dest_only: bool = False) -> None:
        """Scan folders to obtain file counts and bytes."""
        if self.scan_busy:
            return
        self.scan_busy = True
        self.emit("scan_started", {"fast_dest_only": fast_dest_only})

        def worker() -> None:
            try:
                # 1. Scan Destination first (fast local NVMe/SSD)
                dst_bytes, dst_files, dst_errs = self._scan_directory(self.dest_path, "Destination")
                with self._lock:
                    self.dest_copied_bytes = dst_bytes
                    self.dest_copied_files = dst_files

                self.emit("scan_dest_complete", {
                    "bytes": dst_bytes,
                    "files": dst_files,
                    "errors": dst_errs,
                })

                # 2. Scan Source
                if not fast_dest_only and os.path.exists(self.source_path):
                    src_bytes, src_files, src_errs = self._scan_directory(self.source_path, "Source")
                    with self._lock:
                        self.source_total_bytes = src_bytes
                        self.source_total_files = src_files

                    self.emit("scan_source_complete", {
                        "bytes": src_bytes,
                        "files": src_files,
                        "errors": src_errs,
                    })

                self.emit("log", {
                    "level": "info",
                    "text": f"Scan completed: {format_bytes(self.dest_copied_bytes)} ({self.dest_copied_files:,} files) on D:\\temp. Source total: {format_bytes(self.source_total_bytes)} ({self.source_total_files:,} files)."
                })
            except Exception as e:
                self.emit("log", {"level": "error", "text": f"Scan encountered an error: {e}"})
            finally:
                self.scan_busy = False
                self.emit("scan_finished", {})

        threading.Thread(target=worker, daemon=True).start()

    def _scan_directory(self, root: str, label: str) -> tuple[int, int, int]:
        total_bytes = 0
        total_files = 0
        errors = 0
        last_emit = time.time()

        for current, dirs, files in os.walk(root, onerror=lambda _e: None):
            dirs[:] = [d for d in dirs if d.casefold() not in ("$recycle.bin", "system volume information")]
            for name in files:
                try:
                    fpath = os.path.join(current, name)
                    total_bytes += os.path.getsize(fpath)
                    total_files += 1
                except OSError:
                    errors += 1

            if time.time() - last_emit > 0.8:
                last_emit = time.time()
                self.emit("scan_progress", {
                    "label": label,
                    "files": total_files,
                    "bytes": total_bytes,
                    "bytes_formatted": format_bytes(total_bytes),
                })

        return total_bytes, total_files, errors

    def start_transfer(
        self,
        source: Optional[str] = None,
        dest: Optional[str] = None,
        threads: int = 8,
        restartable: bool = True,
        unbuffered: bool = True,
        exclude_older: bool = True,
        exclude_system: bool = True,
        retry_count: int = 2,
        retry_wait: int = 2,
    ) -> tuple[bool, str]:
        """Launch Robocopy with safe resume and optimal flags."""
        if source:
            self.source_path = source
        if dest:
            self.dest_path = dest

        if self.child and self.child.poll() is None:
            return False, "This monitor is already running a transfer."

        saved = read_saved_state()
        if saved:
            return False, f"A managed Robocopy process is already running (PID {saved['pid']})."

        all_procs = check_running_robocopy_processes()
        if all_procs:
            pids = ", ".join(str(p["pid"]) for p in all_procs)
            return False, f"Another Robocopy process is currently active ({pids})."

        if not os.path.exists(self.source_path):
            return False, f"Source path is unreachable: {self.source_path}"

        try:
            os.makedirs(self.dest_path, exist_ok=True)
        except OSError as e:
            return False, f"Could not create destination directory {self.dest_path}: {e}"

        cmd = ["robocopy.exe", self.source_path, self.dest_path, "/E"]

        if restartable:
            cmd.append("/Z")
        if unbuffered:
            cmd.append("/J")
        if exclude_older:
            cmd.append("/XO")
        if exclude_system:
            cmd.extend(["/XD", "$RECYCLE.BIN", "System Volume Information"])

        cmd.extend([
            "/FFT",
            f"/R:{max(0, retry_count)}",
            f"/W:{max(0, retry_wait)}",
            f"/MT:{max(1, min(128, threads))}",
            "/BYTES",
            "/NP",
            "/TEE",
        ])

        try:
            self.child = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="mbcs",
                errors="replace",
                bufsize=1,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except Exception as exc:
            return False, f"Failed to spawn robocopy.exe: {exc}"

        self.transfer_start_time = time.time()
        self.last_io_sample = None
        self.source_upload_speed = 0.0
        self.dest_download_speed = 0.0
        self.speed_history.clear()

        identity = get_process_identity(self.child.pid)
        if identity and os.path.basename(identity[0]).casefold() == "robocopy.exe":
            self.managed_pid = self.child.pid
            self.managed_created = identity[1]
            write_saved_state({
                "pid": self.managed_pid,
                "created": self.managed_created,
                "source": self.source_path,
                "dest": self.dest_path,
                "started_at": self.transfer_start_time,
                "cmd": " ".join(cmd),
            })

        self.emit("log", {
            "level": "info",
            "text": f"🚀 Started safe resume transfer (PID {self.child.pid}): {' '.join(cmd)}"
        })
        self.emit("transfer_started", {"pid": self.child.pid, "cmd": cmd})

        threading.Thread(target=self._stream_output_reader, args=(self.child,), daemon=True).start()
        return True, "Transfer started successfully."

    def stop_transfer(self) -> tuple[bool, str]:
        """Safely terminate the utility-managed Robocopy process."""
        pid = self.managed_pid
        if not pid:
            saved = read_saved_state()
            if saved:
                pid = int(saved["pid"])

        if not pid:
            return False, "No active transfer process to stop."

        identity = get_process_identity(pid)
        if not identity or os.path.basename(identity[0]).casefold() != "robocopy.exe":
            clear_saved_state()
            self.managed_pid = None
            self.managed_created = None
            return False, f"Process {pid} is no longer running."

        kernel = ctypes.windll.kernel32
        handle = kernel.OpenProcess(0x0001, False, pid)  # PROCESS_TERMINATE
        if not handle:
            return False, f"Could not acquire terminate handle for PID {pid}."

        try:
            kernel.TerminateProcess.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
            kernel.TerminateProcess.restype = ctypes.c_int
            kernel.CloseHandle.argtypes = [ctypes.c_void_p]
            ok = kernel.TerminateProcess(handle, 1)
        finally:
            kernel.CloseHandle(handle)

        clear_saved_state()
        self.managed_pid = None
        self.managed_created = None
        self.child = None
        self.source_upload_speed = 0.0
        self.dest_download_speed = 0.0
        self.current_file = "Stopped"

        if ok:
            self.emit("log", {
                "level": "warning",
                "text": f"🛑 Safely stopped Robocopy process (PID {pid}). All transferred files on D:\\temp are intact and ready for resume."
            })
            self.emit("transfer_stopped", {"pid": pid})
            self.start_background_scan(fast_dest_only=True)
            return True, "Transfer safely stopped. Copied files preserved."
        else:
            return False, "Windows could not terminate the process."

    def _stream_output_reader(self, proc: subprocess.Popen) -> None:
        """Stream stdout from Robocopy in real-time, parse files, bytes, and summary."""
        file_regex = re.compile(r"^\s*(New File|Newer|Older|Same|\*EXTRA File\*)\s+(\d+)\s+(.+)$", re.IGNORECASE)
        dir_regex = re.compile(r"^\s*(New Dir|\*EXTRA Dir\*)\s+(.+)$", re.IGNORECASE)
        error_regex = re.compile(r"ERROR\s+(\d+)", re.IGNORECASE)
        speed_regex = re.compile(r"Speed\s*:\s*([\d,\.]+)\s*(Bytes/sec|MegaBytes/min)", re.IGNORECASE)

        last_telemetry_emit = time.time()

        try:
            assert proc.stdout is not None
            for raw_line in proc.stdout:
                line = raw_line.strip()
                if not line:
                    continue

                # Parse file lines
                match_file = file_regex.match(line)
                if match_file:
                    action = match_file.group(1).strip()
                    size_bytes = int(match_file.group(2))
                    file_path = match_file.group(3).strip()
                    file_name = os.path.basename(file_path)

                    with self._lock:
                        if action.casefold() in ("new file", "newer", "older"):
                            self.dest_copied_bytes += size_bytes
                            self.dest_copied_files += 1
                        self.current_file = file_name

                    self.emit("log", {
                        "level": "file",
                        "text": f"[{action}] {file_name} ({format_bytes(size_bytes)})"
                    })

                elif dir_regex.match(line):
                    m = dir_regex.match(line)
                    dpath = m.group(2).strip()
                    with self._lock:
                        self.current_folder = os.path.basename(dpath)
                    self.emit("log", {
                        "level": "info",
                        "text": f"📁 Folder: {self.current_folder}"
                    })

                elif error_regex.search(line):
                    self.emit("log", {
                        "level": "error",
                        "text": f"⚠️ {line}"
                    })

                elif speed_regex.search(line):
                    self.emit("log", {
                        "level": "info",
                        "text": f"📊 {line}"
                    })

                elif line.startswith("Files :") or line.startswith("Bytes :") or line.startswith("Dirs :"):
                    self.emit("log", {
                        "level": "info",
                        "text": f"📈 {line}"
                    })

                # Telemetry push every 250ms
                if time.time() - last_telemetry_emit > 0.25:
                    last_telemetry_emit = time.time()
                    self.emit("telemetry", self.get_system_status())

            exit_code = proc.wait()
        except Exception as e:
            self.emit("log", {"level": "error", "text": f"Stream reader error: {e}"})
            exit_code = proc.poll() or 16

        clear_saved_state()
        self.managed_pid = None
        self.managed_created = None
        self.child = None
        self.source_upload_speed = 0.0
        self.dest_download_speed = 0.0
        self.current_file = "Finished"

        is_success, friendly_msg = explain_exit_code(exit_code)
        log_level = "success" if is_success else "error"
        self.emit("log", {
            "level": log_level,
            "text": f"🏁 Robocopy ended (Code {exit_code}): {friendly_msg}"
        })
        self.emit("transfer_completed", {
            "exit_code": exit_code,
            "is_success": is_success,
            "message": friendly_msg,
        })
        self.start_background_scan(fast_dest_only=True)
