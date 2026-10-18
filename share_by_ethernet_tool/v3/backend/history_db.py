"""
T-Share v3 History & Audit Database
Stores local transfer ledgers and cryptographic audit logs using SQLite.
"""

import sqlite3
import os
import json
import time
from typing import List, Dict, Any, Optional

DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "tshare_history_v3.db")


class HistoryDatabase:
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = os.path.abspath(db_path)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS transfers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL, -- 'sender' or 'receiver'
                    peer_name TEXT,
                    peer_ip TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT NOT NULL, -- 'completed', 'cancelled', 'failed'
                    total_files INTEGER DEFAULT 0,
                    total_bytes INTEGER DEFAULT 0,
                    transferred_bytes INTEGER DEFAULT 0,
                    avg_speed_mbps REAL DEFAULT 0.0,
                    duration_sec REAL DEFAULT 0.0,
                    local_path TEXT,
                    manifest_digest TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS verifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    mode TEXT NOT NULL, -- 'quick_parity' or 'full_crypto'
                    status TEXT NOT NULL, -- 'passed', 'mismatch', 'error'
                    files_checked INTEGER DEFAULT 0,
                    bytes_checked INTEGER DEFAULT 0,
                    duration_sec REAL DEFAULT 0.0,
                    read_speed_mbps REAL DEFAULT 0.0,
                    details TEXT
                )
            """)
            conn.commit()

    def record_transfer(
        self,
        session_id: str,
        role: str,
        peer_name: str,
        peer_ip: str,
        status: str,
        total_files: int,
        total_bytes: int,
        transferred_bytes: int,
        avg_speed_mbps: float,
        duration_sec: float,
        local_path: str,
        manifest_digest: str = ""
    ) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO transfers (
                    session_id, role, peer_name, peer_ip, status,
                    total_files, total_bytes, transferred_bytes,
                    avg_speed_mbps, duration_sec, local_path, manifest_digest
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(session_id), role, peer_name, peer_ip, status,
                total_files, total_bytes, transferred_bytes,
                avg_speed_mbps, duration_sec, local_path, manifest_digest
            ))
            conn.commit()
            return cursor.lastrowid

    def record_verification(
        self,
        session_id: str,
        mode: str,
        status: str,
        files_checked: int,
        bytes_checked: int,
        duration_sec: float,
        read_speed_mbps: float,
        details: str = ""
    ) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO verifications (
                    session_id, mode, status, files_checked, bytes_checked,
                    duration_sec, read_speed_mbps, details
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(session_id), mode, status, files_checked, bytes_checked,
                duration_sec, read_speed_mbps, details
            ))
            conn.commit()
            return cursor.lastrowid

    def get_transfers(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM transfers ORDER BY id DESC LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def get_sessions_by_role(self, role: str, limit: int = 50) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM transfers WHERE role = ? ORDER BY id DESC LIMIT ?
            """, (role, limit))
            return [dict(row) for row in cursor.fetchall()]

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM transfers WHERE session_id = ? ORDER BY id DESC LIMIT 1
            """, (str(session_id),))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_verifications_for_session(self, session_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM verifications WHERE session_id = ? ORDER BY id DESC
            """, (str(session_id),))
            return [dict(row) for row in cursor.fetchall()]
