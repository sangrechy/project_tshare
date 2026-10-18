"""
T-Share v3 Transfer Engine (Sender)
Streams files in 4 MB blocks with in-flight RAM SHA-256 digests.
Supports crash resumption, rate-limiting governor, and throttled UI telemetry.
"""

import os
import math
import time
import socket
import struct
import hashlib
import random
import threading
from typing import Dict, List, Any, Optional, Callable

from .protocol import (
    MAGIC, DEFAULT_TCP_PORT, BLOCK_SIZE, HEADER_SIZE, BLOCK_HEADER_SIZE,
    MSG_HELLO, MSG_HELLO_ACK, MSG_MANIFEST, MSG_ACCEPT, MSG_REJECT,
    MSG_RESUME_QUERY, MSG_RESUME_BITMAP, MSG_BLOCK, MSG_BLOCK_ACK, MSG_BLOCK_NACK,
    MSG_FILE_DONE, MSG_SESSION_DONE, MSG_CANCEL, MSG_ERROR,
    BLOCK_HEADER_FORMAT, tune_socket, send_packet, send_json, recv_packet, recv_json
)
from .history_db import HistoryDatabase


class TransferEngine:
    def __init__(self, history_db: Optional[HistoryDatabase] = None):
        self.history_db = history_db or HistoryDatabase()
        self._sock: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._cancel_requested = False

        # Session & state
        self.status = "idle"  # idle, connecting, negotiating, streaming, completed, cancelled, error
        self.peer_name = "Unknown"
        self.peer_ip = ""
        self.total_files = 0
        self.current_file_index = 0
        self.current_file_name = ""
        self.total_bytes = 0
        self.transferred_bytes = 0
        self.speed_mbps = 0.0
        self.eta_seconds = 0
        self.error_message = ""
        self.receiver_status_message = ""

        # Resource configuration
        self.rate_limit_mbps = 0.0  # 0 = uncapped

    def is_active(self) -> bool:
        return self.status in ["connecting", "negotiating", "streaming"]

    def cancel(self) -> None:
        """Signals active transfer to cancel gracefully."""
        self._cancel_requested = True
        self.status = "cancelled"
        if self._sock:
            try:
                send_json(self._sock, MSG_CANCEL, 0, {"reason": "User cancelled on sender"})
            except Exception:
                pass
            try:
                self._sock.close()
            except Exception:
                pass

    def start_transfer(
        self,
        target_ip: str,
        target_port: int,
        source_paths: List[str],
        rate_limit_mbps: float = 0.0
    ) -> None:
        """Launches transfer in a background thread."""
        if self.is_active():
            raise RuntimeError("A transfer is already active")

        self.target_ip = target_ip
        self.target_port = target_port
        self.source_paths = source_paths
        self.rate_limit_mbps = rate_limit_mbps
        self._cancel_requested = False

        self._thread = threading.Thread(target=self._run_transfer, daemon=True, name="SenderThread")
        self._thread.start()

    def get_telemetry(self) -> Dict[str, Any]:
        """Provides snapshot of live sender state."""
        return {
            "status": self.status,
            "peer_name": self.peer_name,
            "peer_ip": self.peer_ip,
            "total_files": self.total_files,
            "current_file_index": self.current_file_index,
            "current_file_name": self.current_file_name,
            "total_bytes": self.total_bytes,
            "transferred_bytes": self.transferred_bytes,
            "speed_mbps": round(self.speed_mbps, 2),
            "eta_seconds": int(self.eta_seconds),
            "receiver_status": self.receiver_status_message,
            "error_message": self.error_message
        }

    def _build_manifest(self, source_paths: List[str]) -> Tuple[List[Dict[str, Any]], int]:
        files = []
        file_id_counter = 1
        total_size = 0

        for path in source_paths:
            path = os.path.abspath(path)
            if os.path.isfile(path):
                size = os.path.getsize(path)
                rel_path = os.path.basename(path)
                files.append({
                    "id": file_id_counter,
                    "rel_path": rel_path,
                    "abs_path": path,
                    "size": size,
                    "mtime": os.path.getmtime(path)
                })
                file_id_counter += 1
                total_size += size
            elif os.path.isdir(path):
                root_name = os.path.basename(path)
                for dirpath, _, filenames in os.walk(path):
                    for fname in filenames:
                        full_p = os.path.join(dirpath, fname)
                        rel_inside = os.path.relpath(full_p, path).replace("\\", "/")
                        rel_path = f"{root_name}/{rel_inside}"
                        size = os.path.getsize(full_p)
                        files.append({
                            "id": file_id_counter,
                            "rel_path": rel_path,
                            "abs_path": full_p,
                            "size": size,
                            "mtime": os.path.getmtime(full_p)
                        })
                        file_id_counter += 1
                        total_size += size

        return files, total_size

    def _run_transfer(self) -> None:
        start_time = time.time()
        session_id = random.randint(100000, 999999)
        self.peer_ip = self.target_ip
        self.status = "connecting"
        self.error_message = ""
        self.receiver_status_message = "Connecting to peer..."

        try:
            # 1. Connect TCP socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10.0)
            sock.connect((self.target_ip, self.target_port))
            tune_socket(sock)
            self._sock = sock

            # 2. Handshake HELLO
            self.status = "negotiating"
            send_json(sock, MSG_HELLO, session_id, {
                "version": 3,
                "hostname": socket.gethostname()
            })

            msg_type, _, ack_data = recv_json(sock)
            if msg_type != MSG_HELLO_ACK or not ack_data.get("accepted"):
                raise ConnectionError("Peer rejected connection")

            self.peer_name = ack_data.get("name", "Receiver")
            self.receiver_status_message = f"Connected to {self.peer_name} · Preparing manifest..."

            # 3. Build & Send Manifest
            files, total_size = self._build_manifest(self.source_paths)
            self.total_files = len(files)
            self.total_bytes = total_size
            self.transferred_bytes = 0

            # Send manifest (strip local abs_path before sending)
            clean_files = [
                {"id": f["id"], "rel_path": f["rel_path"], "size": f["size"], "mtime": f["mtime"]}
                for f in files
            ]
            send_json(sock, MSG_MANIFEST, session_id, {
                "session_id": session_id,
                "total_files": self.total_files,
                "total_bytes": self.total_bytes,
                "files": clean_files
            })

            self.receiver_status_message = f"Awaiting peer acceptance..."
            msg_type, _, decision = recv_json(sock)

            if msg_type != MSG_ACCEPT or not decision.get("accepted"):
                reason = decision.get("reason", "Peer declined transfer") if decision else "Declined"
                self.receiver_status_message = f"Transfer declined: {reason}"
                self.status = "rejected"
                return

            self.receiver_status_message = "Receiver accepted · saving to selected destination"
            self.status = "streaming"

            # 4. Stream 4 MB Blocks
            sock.settimeout(30.0)
            last_speed_time = time.time()
            last_speed_bytes = 0

            for idx, file_meta in enumerate(files):
                if self._cancel_requested:
                    break

                self.current_file_index = idx + 1
                self.current_file_name = file_meta["rel_path"]
                file_id = file_meta["id"]
                file_size = file_meta["size"]
                abs_path = file_meta["abs_path"]

                total_blocks = math.ceil(file_size / BLOCK_SIZE) if file_size > 0 else 0

                # Query resume status
                send_json(sock, MSG_RESUME_QUERY, session_id, {"file_id": file_id})
                msg_type, _, resume_data = recv_json(sock)
                verified_blocks = set()
                if msg_type == MSG_RESUME_BITMAP and resume_data:
                    verified_blocks = set(resume_data.get("verified_blocks", []))

                # Stream blocks
                with open(abs_path, "rb") as f:
                    for block_idx in range(total_blocks):
                        if self._cancel_requested:
                            break

                        # Check if block is already verified on receiver
                        block_len = min(BLOCK_SIZE, file_size - (block_idx * BLOCK_SIZE))
                        if block_idx in verified_blocks:
                            self.transferred_bytes += block_len
                            continue

                        # Read block and compute in-memory SHA-256
                        f.seek(block_idx * BLOCK_SIZE)
                        data = f.read(block_len)
                        block_hash = hashlib.sha256(data).digest()

                        # Pack block header
                        block_header = struct.pack(BLOCK_HEADER_FORMAT, file_id, block_idx, len(data), block_hash)
                        send_packet(sock, MSG_BLOCK, session_id, block_header + data)

                        # Await ACK / NACK
                        ack_type, _, ack_payload = recv_packet(sock)
                        if ack_type == MSG_BLOCK_NACK:
                            # Instant retry for failed block
                            send_packet(sock, MSG_BLOCK, session_id, block_header + data)
                            recv_packet(sock)  # Consume retry ACK

                        self.transferred_bytes += len(data)

                        # Rate limiting
                        if self.rate_limit_mbps > 0:
                            target_bytes_sec = self.rate_limit_mbps * 1024 * 1024
                            chunk_duration = len(data) / target_bytes_sec
                            time.sleep(chunk_duration * 0.9)

                        # Speed calculation
                        now = time.time()
                        dt = now - last_speed_time
                        if dt >= 0.5:
                            bytes_diff = self.transferred_bytes - last_speed_bytes
                            self.speed_mbps = (bytes_diff / dt) / (1024 * 1024)
                            rem_bytes = max(0, self.total_bytes - self.transferred_bytes)
                            self.eta_seconds = (rem_bytes / (self.speed_mbps * 1024 * 1024)) if self.speed_mbps > 0 else 0
                            last_speed_time = now
                            last_speed_bytes = self.transferred_bytes

                # File done
                send_json(sock, MSG_FILE_DONE, session_id, {"file_id": file_id})

            # 5. Session Complete
            if not self._cancel_requested:
                send_json(sock, MSG_SESSION_DONE, session_id, {})
                duration = max(0.1, time.time() - start_time)
                avg_speed = (self.transferred_bytes / duration) / (1024 * 1024)

                self.status = "completed"
                self.receiver_status_message = "Transfer completed successfully"

                # Record in history database
                first_src = self.source_paths[0] if self.source_paths else ""
                self.history_db.record_transfer(
                    session_id=str(session_id),
                    role="sender",
                    peer_name=self.peer_name,
                    peer_ip=self.peer_ip,
                    status="completed",
                    total_files=self.total_files,
                    total_bytes=self.total_bytes,
                    transferred_bytes=self.transferred_bytes,
                    avg_speed_mbps=round(avg_speed, 2),
                    duration_sec=round(duration, 1),
                    local_path=first_src
                )
            else:
                self.status = "cancelled"
                self.receiver_status_message = "Transfer cancelled"

        except Exception as e:
            self.status = "error"
            self.error_message = str(e)
            self.receiver_status_message = f"Error: {e}"
        finally:
            if self._sock:
                try:
                    self._sock.close()
                except Exception:
                    pass
                self._sock = None
