"""
T-Share v3 Receiver Engine
Listens for incoming transfers, stages 4 MB blocks, enforces in-flight SHA-256 integrity,
maintains .tshare_state crash journals, and atomically finalizes files upon verification.
"""

import os
import sys
import math
import time
import socket
import struct
import hashlib
import json
import threading
from typing import Dict, List, Any, Optional, Callable

from .protocol import (
    MAGIC, DEFAULT_TCP_PORT, BLOCK_SIZE, HEADER_FORMAT, HEADER_SIZE, BLOCK_HEADER_FORMAT, BLOCK_HEADER_SIZE,
    MSG_HELLO, MSG_HELLO_ACK, MSG_MANIFEST, MSG_ACCEPT, MSG_REJECT,
    MSG_RESUME_QUERY, MSG_RESUME_BITMAP, MSG_BLOCK, MSG_BLOCK_ACK, MSG_BLOCK_NACK,
    MSG_FILE_DONE, MSG_SESSION_DONE, MSG_CANCEL, MSG_ERROR,
    tune_socket, send_packet, send_json, recv_packet, recv_json, recv_exact
)
from .path_security import sanitize_relative_path, resolve_safe_destination_path, SecurityViolation
from .history_db import HistoryDatabase


class ReceiverEngine:
    def __init__(self, port: int = DEFAULT_TCP_PORT, history_db: Optional[HistoryDatabase] = None):
        self.port = port
        self.history_db = history_db or HistoryDatabase()
        self._server_sock: Optional[socket.socket] = None
        self._client_sock: Optional[socket.socket] = None
        self._running = False
        self._transfer_active = False
        self._cancel_requested = False

        # Session & offer state
        self.current_session_id = 0
        self.pending_offer: Optional[Dict[str, Any]] = None
        self._accept_event = threading.Event()
        self._user_decision: Optional[Dict[str, Any]] = None

        # Telemetry
        self.status = "idle"  # idle, waiting_user, receiving, completed, cancelled, error
        self.peer_name = "Unknown"
        self.peer_ip = ""
        self.total_files = 0
        self.current_file_index = 0
        self.current_file_name = ""
        self.total_bytes = 0
        self.transferred_bytes = 0
        self.speed_mbps = 0.0
        self.eta_seconds = 0
        self.active_destination = ""
        self.error_message = ""

        # Callbacks
        self.on_offer: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_progress: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_status_change: Optional[Callable[[str], None]] = None

    def start(self) -> None:
        """Starts TCP listener daemon."""
        if self._running:
            return
        self._running = True

        for p in range(self.port, self.port + 10):
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                tune_socket(s)
                s.bind(("0.0.0.0", p))
                s.listen(1)
                self._server_sock = s
                self.port = p
                break
            except Exception:
                continue

        if not self._server_sock:
            raise RuntimeError(f"Could not bind receiver socket on ports {self.port}-{self.port+9}")

        threading.Thread(target=self._accept_loop, daemon=True, name="ReceiverAcceptLoop").start()

    def stop(self) -> None:
        """Stops listener and aborts active transfer."""
        self._running = False
        self._cancel_requested = True
        self._accept_event.set()
        if self._client_sock:
            try:
                self._client_sock.close()
            except Exception:
                pass
        if self._server_sock:
            try:
                self._server_sock.close()
            except Exception:
                pass

    def cancel_transfer(self) -> None:
        """Cancels currently active transfer."""
        self._cancel_requested = True
        self.status = "cancelled"
        if self._client_sock:
            try:
                send_json(self._client_sock, MSG_CANCEL, self.current_session_id, {"reason": "User cancelled on receiver"})
            except Exception:
                pass
            try:
                self._client_sock.close()
            except Exception:
                pass

    def accept_transfer(self, destination_dir: str, collision_policy: str = "keep_both") -> None:
        """Called by UI when user clicks Accept with chosen destination directory."""
        self._user_decision = {
            "accepted": True,
            "destination_dir": os.path.abspath(destination_dir),
            "collision_policy": collision_policy
        }
        self.active_destination = os.path.abspath(destination_dir)
        self._accept_event.set()

    def reject_transfer(self, reason: str = "Rejected by user") -> None:
        """Called by UI when user declines incoming transfer."""
        self._user_decision = {
            "accepted": False,
            "reason": reason
        }
        self._accept_event.set()

    def get_telemetry(self) -> Dict[str, Any]:
        """Provides snapshot of live receiver state."""
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
            "active_destination": self.active_destination,
            "error_message": self.error_message,
            "pending_offer": self.pending_offer
        }

    def _accept_loop(self) -> None:
        while self._running:
            try:
                client_sock, addr = self._server_sock.accept()
                tune_socket(client_sock)
                self._client_sock = client_sock
                self.peer_ip = addr[0]
                self._cancel_requested = False

                # Handle session in dedicated worker thread
                t = threading.Thread(target=self._handle_session, args=(client_sock, addr), daemon=True)
                t.start()
                t.join()  # Handle one session at a time
            except Exception:
                if not self._running:
                    break
                time.sleep(0.5)

    def _handle_session(self, sock: socket.socket, addr: tuple) -> None:
        start_time = time.time()
        self._transfer_active = True
        self.status = "connecting"
        self._user_decision = None
        self._accept_event.clear()

        try:
            # 1. Receive MSG_HELLO
            msg_type, session_id, hello_data = recv_json(sock)
            if msg_type != MSG_HELLO:
                send_json(sock, MSG_ERROR, 0, {"error": "Expected MSG_HELLO"})
                return

            self.current_session_id = session_id
            self.peer_name = hello_data.get("hostname", "Unknown")

            # Reply with HELLO_ACK
            send_json(sock, MSG_HELLO_ACK, session_id, {
                "accepted": True,
                "name": socket.gethostname()
            })

            # 2. Receive MSG_MANIFEST
            msg_type, _, manifest = recv_json(sock)
            if msg_type != MSG_MANIFEST:
                send_json(sock, MSG_ERROR, session_id, {"error": "Expected MSG_MANIFEST"})
                return

            self.total_files = manifest.get("total_files", 0)
            self.total_bytes = manifest.get("total_bytes", 0)
            self.transferred_bytes = 0
            files = manifest.get("files", [])

            # Present offer to user & wait for decision
            self.pending_offer = {
                "session_id": session_id,
                "peer_name": self.peer_name,
                "peer_ip": self.peer_ip,
                "total_files": self.total_files,
                "total_bytes": self.total_bytes,
                "root_name": files[0].get("rel_path", "Transfer").split("/")[0] if files else "Transfer"
            }
            self.status = "waiting_user"
            if self.on_offer:
                self.on_offer(self.pending_offer)

            # Block until user accepts or rejects
            self._accept_event.wait()

            if not self._user_decision or not self._user_decision.get("accepted"):
                reason = self._user_decision.get("reason", "Declined by user") if self._user_decision else "Cancelled"
                send_json(sock, MSG_REJECT, session_id, {"reason": reason})
                self.status = "idle"
                self.pending_offer = None
                return

            destination_dir = self._user_decision["destination_dir"]
            collision_policy = self._user_decision["collision_policy"]

            # Reply MSG_ACCEPT without exposing destination path
            send_json(sock, MSG_ACCEPT, session_id, {
                "accepted": True,
                "status": "Ready to receive"
            })

            self.status = "receiving"
            self.pending_offer = None

            # Process file streaming
            speed_samples = []
            last_speed_time = time.time()
            last_speed_bytes = 0

            for idx, file_meta in enumerate(files):
                if self._cancel_requested:
                    break

                self.current_file_index = idx + 1
                raw_rel_path = file_meta["rel_path"]
                file_size = file_meta["size"]
                file_id = file_meta["id"]

                sanitized_rel = sanitize_relative_path(raw_rel_path)
                final_dest_path, should_skip = resolve_safe_destination_path(
                    destination_dir, sanitized_rel, collision_policy
                )

                self.current_file_name = os.path.basename(final_dest_path)
                os.makedirs(os.path.dirname(final_dest_path), exist_ok=True)

                if should_skip:
                    self.transferred_bytes += file_size
                    continue

                # Prepare staging & journal files on the same volume
                staging_path = os.path.join(
                    destination_dir, f".tshare_staging_{session_id}_{file_id}.part"
                )
                state_path = os.path.join(
                    destination_dir, f".tshare_state_{session_id}_{file_id}.json"
                )

                total_blocks = math.ceil(file_size / BLOCK_SIZE) if file_size > 0 else 0
                verified_blocks = set()

                if os.path.exists(staging_path) and os.path.exists(state_path):
                    try:
                        with open(state_path, "r", encoding="utf-8") as sf:
                            saved_state = json.load(sf)
                            if saved_state.get("file_size") == file_size:
                                verified_blocks = set(saved_state.get("verified_blocks", []))
                    except Exception:
                        verified_blocks = set()

                file_handle = open(staging_path, "r+b" if os.path.exists(staging_path) else "wb", buffering=4 * 1024 * 1024)
                if file_size > 0 and not os.path.exists(staging_path):
                    try:
                        file_handle.truncate(file_size)
                    except Exception:
                        pass

                corrupted_blocks = set()
                msg_type = None

                # Continuous streaming block receiver
                while len(verified_blocks) < total_blocks and not self._cancel_requested:
                    header_bytes = recv_exact(sock, HEADER_SIZE)
                    magic, msg_type, s_id, payload_len = struct.unpack(HEADER_FORMAT, header_bytes)

                    if msg_type == MSG_RESUME_QUERY:
                        if payload_len > 0:
                            recv_exact(sock, payload_len)
                        send_json(sock, MSG_RESUME_BITMAP, session_id, {
                            "file_id": file_id,
                            "verified_blocks": list(verified_blocks)
                        })
                        continue

                    if msg_type == MSG_BLOCK:
                        # Read 44-byte block header
                        b_hdr = recv_exact(sock, BLOCK_HEADER_SIZE)
                        b_file_id, block_idx, block_len, expected_hash = struct.unpack(BLOCK_HEADER_FORMAT, b_hdr)

                        # Stream directly from socket into file in 512KB chunks
                        file_handle.seek(block_idx * BLOCK_SIZE)
                        hasher = hashlib.sha256()
                        remaining = block_len
                        while remaining > 0:
                            chunk = sock.recv(min(remaining, 512 * 1024))
                            if not chunk:
                                raise ConnectionError("Connection lost while reading block payload")
                            hasher.update(chunk)
                            file_handle.write(chunk)
                            remaining -= len(chunk)

                        if hasher.digest() == expected_hash:
                            verified_blocks.add(block_idx)
                            corrupted_blocks.discard(block_idx)
                        else:
                            corrupted_blocks.add(block_idx)

                        self.transferred_bytes += block_len

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

                        # Save state journal periodically (every 20 blocks or on last block)
                        if len(verified_blocks) % 20 == 0 or len(verified_blocks) == total_blocks:
                            try:
                                with open(state_path, "w", encoding="utf-8") as sf:
                                    json.dump({
                                        "file_id": file_id,
                                        "file_size": file_size,
                                        "verified_blocks": list(verified_blocks)
                                    }, sf)
                            except Exception:
                                pass

                    elif msg_type == MSG_FILE_DONE:
                        if payload_len > 0:
                            recv_exact(sock, payload_len)
                        break

                    elif msg_type == MSG_CANCEL:
                        self._cancel_requested = True
                        break

                # Flush and close file handle
                file_handle.flush()
                file_handle.close()

                # If file wasn't done yet, read the MSG_FILE_DONE packet
                if not self._cancel_requested:
                    missing = (set(range(total_blocks)) - verified_blocks) | corrupted_blocks
                    if not missing:
                        if msg_type != MSG_FILE_DONE:
                            m_type, _, _ = recv_packet(sock)
                            while m_type != MSG_FILE_DONE and not self._cancel_requested:
                                m_type, _, _ = recv_packet(sock)

                        send_json(sock, MSG_FILE_DONE, session_id, {"status": "ok"})
                        try:
                            os.replace(staging_path, final_dest_path)
                        except OSError:
                            import shutil
                            shutil.copy2(staging_path, final_dest_path)
                            try:
                                os.remove(staging_path)
                            except Exception:
                                pass
                        if os.path.exists(state_path):
                            try:
                                os.remove(state_path)
                            except Exception:
                                pass
                    else:
                        # Selective retransmission loop
                        while missing and not self._cancel_requested:
                            send_json(sock, MSG_FILE_DONE, session_id, {
                                "status": "retry",
                                "missing_blocks": list(missing)
                            })
                            file_handle = open(staging_path, "r+b", buffering=4 * 1024 * 1024)
                            while missing and not self._cancel_requested:
                                h_bytes = recv_exact(sock, HEADER_SIZE)
                                _, m_t, _, p_l = struct.unpack(HEADER_FORMAT, h_bytes)
                                if m_t == MSG_BLOCK:
                                    b_hdr = recv_exact(sock, BLOCK_HEADER_SIZE)
                                    _, b_idx, b_len, exp_h = struct.unpack(BLOCK_HEADER_FORMAT, b_hdr)
                                    file_handle.seek(b_idx * BLOCK_SIZE)
                                    hasher = hashlib.sha256()
                                    rem = b_len
                                    while rem > 0:
                                        c = sock.recv(min(rem, 512 * 1024))
                                        if not c:
                                            raise ConnectionError("Connection lost")
                                        hasher.update(c)
                                        file_handle.write(c)
                                        rem -= len(c)
                                    if hasher.digest() == exp_h:
                                        missing.discard(b_idx)
                                        verified_blocks.add(b_idx)
                                elif m_t == MSG_FILE_DONE:
                                    if p_l > 0:
                                        recv_exact(sock, p_l)
                                    break
                            file_handle.flush()
                            file_handle.close()

                        if not missing:
                            send_json(sock, MSG_FILE_DONE, session_id, {"status": "ok"})
                            try:
                                os.replace(staging_path, final_dest_path)
                            except OSError:
                                import shutil
                                shutil.copy2(staging_path, final_dest_path)
                                try:
                                    os.remove(staging_path)
                                except Exception:
                                    pass
                            if os.path.exists(state_path):
                                try:
                                    os.remove(state_path)
                                except Exception:
                                    pass

            # Receive MSG_SESSION_DONE
            if not self._cancel_requested:
                msg_type, _, _ = recv_packet(sock)
                try:
                    send_packet(sock, MSG_SESSION_DONE, session_id, b'ACK')
                except Exception:
                    pass
                duration = max(0.1, time.time() - start_time)
                avg_speed = (self.transferred_bytes / duration) / (1024 * 1024)

                self.status = "completed"
                self.history_db.record_transfer(
                    session_id=str(session_id),
                    role="receiver",
                    peer_name=self.peer_name,
                    peer_ip=self.peer_ip,
                    status="completed",
                    total_files=self.total_files,
                    total_bytes=self.total_bytes,
                    transferred_bytes=self.transferred_bytes,
                    avg_speed_mbps=round(avg_speed, 2),
                    duration_sec=round(duration, 1),
                    local_path=destination_dir
                )
            else:
                self.status = "cancelled"

        except Exception as e:
            self.status = "error"
            self.error_message = str(e)
        finally:
            self._transfer_active = False
            try:
                sock.close()
            except Exception:
                pass
