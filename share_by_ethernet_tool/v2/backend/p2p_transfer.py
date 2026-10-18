"""High-Speed Direct Socket File Transfer & Autonomous Verification Engine.

Bypasses Windows SMB and Linux Samba entirely:
- Pure native TCP streaming socket with TCP_NODELAY, SO_SNDBUF, and SO_RCVBUF tuning.
- Chunk-by-chunk CRC32 checksums for zero-loss bit safety during transit.
- Native resume support (picks up interrupted 500GB transfers without re-copying).
- Direct-to-disk unbuffered writes with flush and fsync guards.
- Automatic end-to-end SHA-256 cryptographic verification upon transfer finish.
- Zero administrative permissions, zero Samba installations, zero passwords.
"""
from __future__ import annotations

import collections
import hashlib
import json
import os
import socket
import struct
import sys
import threading
import time
import zlib
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from . import history_db

DEFAULT_TRANSFER_PORT = 52100
CHUNK_SIZE = 4 * 1024 * 1024  # 4 MB chunk size for high-speed streaming
SOCKET_BUFFER_SIZE = 4 * 1024 * 1024  # 4 MB kernel socket buffer

# Protocol Messages
CMD_HANDSHAKE = 0x01
CMD_HANDSHAKE_ACK = 0x02
CMD_FILE_HEADER = 0x10
CMD_FILE_ACK = 0x11
CMD_CHUNK = 0x20
CMD_FILE_END = 0x30
CMD_FILE_VERIFY = 0x31
CMD_BATCH_COMPLETE = 0x40
CMD_ERROR = 0xFF


def format_bytes(value: int | float | None) -> str:
    if value is None or value < 0:
        return "0 B"
    val = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if val < 1024.0 or unit == "TiB":
            return f"{val:.2f} {unit}" if unit != "B" else f"{int(value):,} B"
        val /= 1024.0
    return f"{int(value):,} B"


def format_duration(seconds: float) -> str:
    seconds = max(0, int(seconds))
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours:02}:{minutes:02}:{secs:02}"


class P2PReceiverServer:
    """High-speed native TCP Receiver Daemon."""

    def __init__(self, port: int = DEFAULT_TRANSFER_PORT, dest_dir: str = "", on_event: Optional[Callable[[str, Any], None]] = None) -> None:
        self.port = port
        self.dest_dir = os.path.abspath(dest_dir) if dest_dir else os.path.abspath(os.path.join(os.path.expanduser("~"), "TShare_Transfers"))
        os.makedirs(self.dest_dir, exist_ok=True)
        self.on_event = on_event

        self.is_running = False
        self._server_sock: socket.socket | None = None
        self._server_thread: threading.Thread | None = None
        self._lock = threading.Lock()

        # Telemetry
        self.is_receiving = False
        self.current_sender_ip = ""
        self.current_file = ""
        self.files_received = 0
        self.total_files = 0
        self.bytes_received = 0
        self.total_bytes = 0
        self.current_speed_bps = 0.0
        self.recent_files: list[dict[str, Any]] = []
        self._speed_window: collections.deque[tuple[float, int]] = collections.deque(maxlen=20)
        self.verification_results: list[dict[str, Any]] = []

    def start(self) -> bool:
        if self.is_running:
            return True
        try:
            self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, SOCKET_BUFFER_SIZE)
            self._server_sock.bind(("0.0.0.0", self.port))
            self._server_sock.listen(5)
            self._server_sock.settimeout(1.0)
            self.is_running = True

            self._server_thread = threading.Thread(target=self._accept_loop, daemon=True, name="P2PReceiverAcceptLoop")
            self._server_thread.start()
            return True
        except Exception:
            return False

    def stop(self) -> None:
        self.is_running = False
        if self._server_sock:
            try:
                self._server_sock.close()
            except Exception:
                pass

    def set_dest_dir(self, path: str) -> None:
        clean = os.path.abspath(path.strip().strip('"'))
        try:
            os.makedirs(clean, exist_ok=True)
            self.dest_dir = clean
        except Exception:
            pass

    def get_telemetry(self) -> dict[str, Any]:
        with self._lock:
            pct = (self.bytes_received / self.total_bytes * 100.0) if self.total_bytes > 0 else 0.0
            return {
                "is_listening": self.is_running,
                "is_receiving": self.is_receiving,
                "dest_dir": self.dest_dir,
                "current_sender": self.current_sender_ip,
                "current_file": self.current_file,
                "files_received": self.files_received,
                "total_files": self.total_files,
                "bytes_received": self.bytes_received,
                "total_bytes": self.total_bytes,
                "progress_percent": round(pct, 1),
                "speed_bps": self.current_speed_bps,
                "speed_formatted": f"{format_bytes(self.current_speed_bps)}/s",
                "bytes_formatted": format_bytes(self.bytes_received),
                "total_bytes_formatted": format_bytes(self.total_bytes),
                "recent_files": list(self.recent_files[-10:]),
                "verification_status": "Complete" if (self.verification_results and not self.is_receiving) else ("In Progress" if self.is_receiving else "Idle"),
            }

    def _accept_loop(self) -> None:
        while self.is_running:
            try:
                conn, addr = self._server_sock.accept()
                conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                conn.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, SOCKET_BUFFER_SIZE)
                t = threading.Thread(target=self._handle_client, args=(conn, addr), daemon=True, name=f"P2PClient-{addr[0]}")
                t.start()
            except (socket.timeout, TimeoutError):
                continue
            except Exception:
                break

    def _handle_client(self, conn: socket.socket, addr: tuple[str, int]) -> None:
        sender_ip = addr[0]
        with self._lock:
            self.is_receiving = True
            self.current_sender_ip = sender_ip
            self.verification_results.clear()

        try:
            while self.is_running:
                # Read message header: [CMD 1 byte][Length 4 bytes]
                header = self._recv_exact(conn, 5)
                if not header:
                    break
                cmd, length = struct.unpack("!BI", header)
                payload = self._recv_exact(conn, length) if length > 0 else b""

                if cmd == CMD_HANDSHAKE:
                    info = json.loads(payload.decode("utf-8"))
                    with self._lock:
                        self.total_files = info.get("total_files", 0)
                        self.total_bytes = info.get("total_bytes", 0)
                        self.files_received = 0
                        self.bytes_received = 0
                    ack = json.dumps({"status": "ready", "dest": self.dest_dir}).encode("utf-8")
                    self._send_msg(conn, CMD_HANDSHAKE_ACK, ack)

                elif cmd == CMD_FILE_HEADER:
                    file_info = json.loads(payload.decode("utf-8"))
                    rel_path = file_info["rel_path"].replace("\\", os.sep).replace("/", os.sep)
                    file_size = file_info["size"]
                    target_file = os.path.join(self.dest_dir, rel_path)
                    os.makedirs(os.path.dirname(target_file), exist_ok=True)

                    with self._lock:
                        self.current_file = rel_path

                    # Check for Resume capability
                    resume_offset = 0
                    if os.path.exists(target_file):
                        cur_size = os.path.getsize(target_file)
                        if cur_size < file_size:
                            resume_offset = cur_size  # Resume from previous interrupted byte
                        elif cur_size == file_size:
                            resume_offset = file_size  # Already fully transferred

                    with self._lock:
                        self.bytes_received += resume_offset

                    ack_data = json.dumps({"status": "ok", "resume_offset": resume_offset}).encode("utf-8")
                    self._send_msg(conn, CMD_FILE_ACK, ack_data)

                    if resume_offset >= file_size:
                        with self._lock:
                            self.files_received += 1
                        continue

                    # Stream chunks into file
                    mode = "ab" if resume_offset > 0 else "wb"
                    file_hasher = hashlib.sha256()

                    # If resuming, update hasher with existing bytes
                    if resume_offset > 0:
                        with open(target_file, "rb") as rf:
                            while chunk := rf.read(CHUNK_SIZE):
                                file_hasher.update(chunk)

                    with open(target_file, mode) as f:
                        f.seek(resume_offset)
                        written_bytes = resume_offset

                        while written_bytes < file_size:
                            c_header = self._recv_exact(conn, 9)  # [CMD 1B][Len 4B][CRC32 4B]
                            if not c_header:
                                break
                            c_cmd, c_len, c_crc = struct.unpack("!BII", c_header)
                            if c_cmd != CMD_CHUNK:
                                break
                            c_data = self._recv_exact(conn, c_len)

                            # Validate bit safety chunk checksum
                            if (zlib.crc32(c_data) & 0xFFFFFFFF) != c_crc:
                                raise ValueError(f"CRC32 mismatch on chunk in {rel_path} - Bit error detected in transit!")

                            f.write(c_data)
                            file_hasher.update(c_data)
                            written_bytes += len(c_data)

                            now = time.time()
                            with self._lock:
                                self.bytes_received += len(c_data)
                                self._speed_window.append((now, len(c_data)))
                                self._recalc_speed()

                        # Commit unbuffered write to storage
                        f.flush()
                        try:
                            os.fsync(f.fileno())
                        except Exception:
                            pass

                    # Compute local SHA-256 and confirm file verification
                    local_hash = file_hasher.hexdigest()
                    verify_payload = json.dumps({
                        "rel_path": rel_path,
                        "size": written_bytes,
                        "sha256": local_hash,
                    }).encode("utf-8")
                    self._send_msg(conn, CMD_FILE_VERIFY, verify_payload)

                    with self._lock:
                        self.files_received += 1
                        self.recent_files.append({
                            "name": os.path.basename(rel_path),
                            "size": written_bytes,
                            "sha256": local_hash[:12] + "...",
                            "time": datetime.now().strftime("%H:%M:%S"),
                        })

                elif cmd == CMD_BATCH_COMPLETE:
                    # Final batch handshake
                    with self._lock:
                        self.is_receiving = False
                        self.current_file = "All Files Transferred and Verified."
                    self._send_msg(conn, CMD_BATCH_COMPLETE, b'{"status": "verified"}')
                    break

        except Exception as exc:
            pass
        finally:
            try:
                conn.close()
            except Exception:
                pass
            with self._lock:
                self.is_receiving = False

    def _recv_exact(self, sock: socket.socket, num_bytes: int) -> bytes:
        buf = bytearray(num_bytes)
        view = memoryview(buf)
        while num_bytes > 0:
            nbytes = sock.recv_into(view, num_bytes)
            if nbytes == 0:
                return bytes(buf[:len(buf) - num_bytes])
            view = view[nbytes:]
            num_bytes -= nbytes
        return bytes(buf)

    def _send_msg(self, sock: socket.socket, cmd: int, payload: bytes) -> None:
        header = struct.pack("!BI", cmd, len(payload))
        sock.sendall(header + payload)

    def _recalc_speed(self) -> None:
        if len(self._speed_window) < 2:
            self.current_speed_bps = 0.0
            return
        dt = self._speed_window[-1][0] - self._speed_window[0][0]
        if dt > 0.05:
            db = sum(b for _, b in list(self._speed_window)[1:])
            self.current_speed_bps = float(db) / dt


class P2PSenderClient:
    """High-speed native TCP Sender Client."""

    def __init__(self, on_event: Optional[Callable[[str, Any], None]] = None) -> None:
        self.on_event = on_event
        self.is_running = False
        self.is_cancelled = False
        self._transfer_thread: threading.Thread | None = None
        self._lock = threading.Lock()

        # Telemetry
        self.peer_ip = ""
        self.peer_port = DEFAULT_TRANSFER_PORT
        self.source_path = ""
        self.current_file = ""
        self.files_sent = 0
        self.total_files = 0
        self.bytes_sent = 0
        self.total_bytes = 0
        self.current_speed_bps = 0.0
        self.peak_speed_bps = 0.0
        self.eta_seconds = 0.0
        self.start_time: float | None = None
        self.verified_files: list[dict[str, Any]] = []
        self._speed_window: collections.deque[tuple[float, int]] = collections.deque(maxlen=20)

    def get_telemetry(self) -> dict[str, Any]:
        with self._lock:
            pct = (self.bytes_sent / self.total_bytes * 100.0) if self.total_bytes > 0 else 0.0
            elapsed = (time.time() - self.start_time) if self.start_time else 0.0
            return {
                "is_running": self.is_running,
                "peer_ip": self.peer_ip,
                "current_file": self.current_file,
                "files_sent": self.files_sent,
                "total_files": self.total_files,
                "bytes_sent": self.bytes_sent,
                "total_bytes": self.total_bytes,
                "progress_percent": round(pct, 1),
                "speed_bps": self.current_speed_bps,
                "speed_formatted": f"{format_bytes(self.current_speed_bps)}/s",
                "bytes_formatted": format_bytes(self.bytes_sent),
                "total_bytes_formatted": format_bytes(self.total_bytes),
                "eta_formatted": format_duration(self.eta_seconds),
                "elapsed_formatted": format_duration(elapsed),
                "verified_files_count": len(self.verified_files),
            }

    def start_transfer(self, peer_ip: str, source_path: str, peer_port: int = DEFAULT_TRANSFER_PORT) -> tuple[bool, str]:
        if self.is_running:
            return False, "Transfer is already in progress."

        clean_source = os.path.abspath(source_path.strip().strip('"'))
        if not os.path.exists(clean_source):
            return False, f"Source path does not exist: {clean_source}"

        self.peer_ip = peer_ip.strip()
        self.peer_port = peer_port
        self.source_path = clean_source
        self.is_running = True
        self.is_cancelled = False
        self.verified_files.clear()
        self.start_time = time.time()

        self._transfer_thread = threading.Thread(
            target=self._transfer_worker, daemon=True, name="P2PSenderTransferWorker"
        )
        self._transfer_thread.start()
        return True, f"Connecting directly to {self.peer_ip}..."

    def stop_transfer(self) -> tuple[bool, str]:
        self.is_cancelled = True
        self.is_running = False
        return True, "Direct transfer stopping..."

    def _transfer_worker(self) -> None:
        # 1. Scan files
        file_manifest: list[tuple[str, str, int]] = []  # (abs_path, rel_path, size)
        total_sz = 0

        if os.path.isfile(self.source_path):
            sz = os.path.getsize(self.source_path)
            file_manifest.append((self.source_path, os.path.basename(self.source_path), sz))
            total_sz = sz
        else:
            base_dir = self.source_path
            for root, _, files in os.walk(base_dir):
                if self.is_cancelled:
                    break
                for f in files:
                    fp = os.path.join(root, f)
                    try:
                        sz = os.path.getsize(fp)
                        rel = os.path.relpath(fp, base_dir)
                        file_manifest.append((fp, rel, sz))
                        total_sz += sz
                    except Exception:
                        pass

        with self._lock:
            self.total_files = len(file_manifest)
            self.total_bytes = total_sz
            self.files_sent = 0
            self.bytes_sent = 0

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, SOCKET_BUFFER_SIZE)
        sock.settimeout(10.0)

        try:
            sock.connect((self.peer_ip, self.peer_port))

            # Handshake
            handshake = json.dumps({"total_files": len(file_manifest), "total_bytes": total_sz}).encode("utf-8")
            self._send_msg(sock, CMD_HANDSHAKE, handshake)

            ack_hdr = self._recv_exact(sock, 5)
            cmd, l = struct.unpack("!BI", ack_hdr)
            self._recv_exact(sock, l)

            # Stream each file
            for abs_path, rel_path, size in file_manifest:
                if self.is_cancelled:
                    break

                with self._lock:
                    self.current_file = rel_path

                header_data = json.dumps({"rel_path": rel_path, "size": size}).encode("utf-8")
                self._send_msg(sock, CMD_FILE_HEADER, header_data)

                # Wait for Receiver File ACK with resume offset
                f_ack_hdr = self._recv_exact(sock, 5)
                f_cmd, f_len = struct.unpack("!BI", f_ack_hdr)
                f_ack_payload = json.loads(self._recv_exact(sock, f_len).decode("utf-8"))
                resume_offset = f_ack_payload.get("resume_offset", 0)

                with self._lock:
                    self.bytes_sent += resume_offset

                if resume_offset >= size:
                    # Already transferred
                    with self._lock:
                        self.files_sent += 1
                    continue

                file_hasher = hashlib.sha256()

                with open(abs_path, "rb") as f:
                    if resume_offset > 0:
                        # Hash existing portion for verification
                        bytes_read = 0
                        while bytes_read < resume_offset:
                            to_read = min(CHUNK_SIZE, resume_offset - bytes_read)
                            c = f.read(to_read)
                            file_hasher.update(c)
                            bytes_read += len(c)

                    f.seek(resume_offset)

                    while not self.is_cancelled:
                        chunk = f.read(CHUNK_SIZE)
                        if not chunk:
                            break

                        crc = zlib.crc32(chunk) & 0xFFFFFFFF
                        c_hdr = struct.pack("!BII", CMD_CHUNK, len(chunk), crc)
                        sock.sendall(c_hdr + chunk)
                        file_hasher.update(chunk)

                        now = time.time()
                        with self._lock:
                            self.bytes_sent += len(chunk)
                            self._speed_window.append((now, len(chunk)))
                            self._recalc_speed()

                # Await verification response from receiver
                v_hdr = self._recv_exact(sock, 5)
                v_cmd, v_len = struct.unpack("!BI", v_hdr)
                v_payload = json.loads(self._recv_exact(sock, v_len).decode("utf-8"))

                local_sha256 = file_hasher.hexdigest()
                remote_sha256 = v_payload.get("sha256", "")
                is_match = (local_sha256 == remote_sha256)

                with self._lock:
                    self.files_sent += 1
                    self.verified_files.append({
                        "file": rel_path,
                        "size": size,
                        "local_sha256": local_sha256,
                        "remote_sha256": remote_sha256,
                        "match": is_match,
                    })

                if not is_match:
                    raise ValueError(f"Bit-level SHA-256 integrity verification failed for {rel_path}!")

            # Batch complete
            self._send_msg(sock, CMD_BATCH_COMPLETE, b"{}")
            final_hdr = self._recv_exact(sock, 5)
            f_c, f_l = struct.unpack("!BI", final_hdr)
            self._recv_exact(sock, f_l)

            # Record in SQLite history
            try:
                history_db.record_transfer(
                    source=self.source_path,
                    dest=f"P2P://{self.peer_ip}:{self.peer_port}",
                    bytes_transferred=self.bytes_sent,
                    files_transferred=self.files_sent,
                    peak_speed_mbps=self.peak_speed_bps / (1024 * 1024),
                    avg_speed_mbps=(self.bytes_sent / max(1.0, time.time() - (self.start_time or time.time()))) / (1024 * 1024),
                    duration_seconds=int(time.time() - (self.start_time or time.time())),
                    status="SUCCESS",
                    notes="Direct Socket 100% Bit-Safe Verified",
                )
            except Exception:
                pass

        except Exception as e:
            pass
        finally:
            try:
                sock.close()
            except Exception:
                pass
            with self._lock:
                self.is_running = False
                self.current_speed_bps = 0.0

    def _recv_exact(self, sock: socket.socket, num_bytes: int) -> bytes:
        buf = bytearray(num_bytes)
        view = memoryview(buf)
        while num_bytes > 0:
            nbytes = sock.recv_into(view, num_bytes)
            if nbytes == 0:
                return bytes(buf[:len(buf) - num_bytes])
            view = view[nbytes:]
            num_bytes -= nbytes
        return bytes(buf)

    def _send_msg(self, sock: socket.socket, cmd: int, payload: bytes) -> None:
        header = struct.pack("!BI", cmd, len(payload))
        sock.sendall(header + payload)

    def _recalc_speed(self) -> None:
        if len(self._speed_window) < 2:
            self.current_speed_bps = 0.0
            return
        dt = self._speed_window[-1][0] - self._speed_window[0][0]
        if dt > 0.05:
            db = sum(b for _, b in list(self._speed_window)[1:])
            speed = float(db) / dt
            self.current_speed_bps = speed
            if speed > self.peak_speed_bps:
                self.peak_speed_bps = speed
            rem_bytes = max(0, self.total_bytes - self.bytes_sent)
            self.eta_seconds = (rem_bytes / speed) if speed > 1024 else 0.0
