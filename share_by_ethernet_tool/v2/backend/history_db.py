"""Persistent SQLite Database Manager for Transfer and Verification History.

Records every transfer and verification session, calculates summary statistics,
and supports search, filtering, and deletion.
"""
from __future__ import annotations

import os
import sqlite3
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

DB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(DB_DIR, "tshare_history.db")
_LOCK = threading.Lock()


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize database tables if they do not exist."""
    with _LOCK:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS transfers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    task_type TEXT NOT NULL DEFAULT 'SEND',
                    source_path TEXT NOT NULL,
                    dest_path TEXT NOT NULL,
                    total_files INTEGER DEFAULT 0,
                    total_bytes INTEGER DEFAULT 0,
                    duration_seconds REAL DEFAULT 0.0,
                    avg_speed_mbps REAL DEFAULT 0.0,
                    peak_speed_mbps REAL DEFAULT 0.0,
                    status TEXT NOT NULL,
                    exit_code INTEGER DEFAULT 0,
                    notes TEXT DEFAULT ''
                );
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS verifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    source_path TEXT NOT NULL,
                    dest_path TEXT NOT NULL,
                    total_files INTEGER DEFAULT 0,
                    total_bytes INTEGER DEFAULT 0,
                    matched_count INTEGER DEFAULT 0,
                    mismatch_count INTEGER DEFAULT 0,
                    missing_count INTEGER DEFAULT 0,
                    extra_count INTEGER DEFAULT 0,
                    duration_seconds REAL DEFAULT 0.0,
                    hash_speed_mbps REAL DEFAULT 0.0,
                    status TEXT NOT NULL,
                    certificate_path TEXT DEFAULT '',
                    notes TEXT DEFAULT ''
                );
                """
            )
            conn.commit()
        finally:
            conn.close()


def add_transfer_record(
    task_type: str,
    source_path: str,
    dest_path: str,
    total_files: int,
    total_bytes: int,
    duration_seconds: float,
    avg_speed_mbps: float,
    peak_speed_mbps: float,
    status: str,
    exit_code: int = 0,
    notes: str = "",
) -> int:
    """Insert a new transfer session record into database."""
    init_db()
    with _LOCK:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                """
                INSERT INTO transfers (
                    timestamp, task_type, source_path, dest_path,
                    total_files, total_bytes, duration_seconds,
                    avg_speed_mbps, peak_speed_mbps, status, exit_code, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    now,
                    task_type,
                    source_path,
                    dest_path,
                    total_files,
                    total_bytes,
                    round(duration_seconds, 2),
                    round(avg_speed_mbps, 2),
                    round(peak_speed_mbps, 2),
                    status,
                    exit_code,
                    notes,
                ),
            )
            conn.commit()
            return cursor.lastrowid or 0
        finally:
            conn.close()


def add_verification_record(
    mode: str,
    source_path: str,
    dest_path: str,
    total_files: int,
    total_bytes: int,
    matched_count: int,
    mismatch_count: int,
    missing_count: int,
    extra_count: int,
    duration_seconds: float,
    hash_speed_mbps: float,
    status: str,
    certificate_path: str = "",
    notes: str = "",
) -> int:
    """Insert a new verification audit record into database."""
    init_db()
    with _LOCK:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                """
                INSERT INTO verifications (
                    timestamp, mode, source_path, dest_path,
                    total_files, total_bytes, matched_count, mismatch_count,
                    missing_count, extra_count, duration_seconds,
                    hash_speed_mbps, status, certificate_path, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    now,
                    mode,
                    source_path,
                    dest_path,
                    total_files,
                    total_bytes,
                    matched_count,
                    mismatch_count,
                    missing_count,
                    extra_count,
                    round(duration_seconds, 2),
                    round(hash_speed_mbps, 2),
                    status,
                    certificate_path,
                    notes,
                ),
            )
            conn.commit()
            return cursor.lastrowid or 0
        finally:
            conn.close()


def get_combined_history(limit: int = 100, filter_type: str = "ALL") -> list[dict[str, Any]]:
    """Retrieve history records combining transfers and verifications sorted chronologically."""
    init_db()
    records: list[dict[str, Any]] = []
    with _LOCK:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            if filter_type in ("ALL", "TRANSFER", "SEND", "RECEIVE"):
                cursor.execute(
                    "SELECT * FROM transfers ORDER BY id DESC LIMIT ?", (limit,)
                )
                for row in cursor.fetchall():
                    d = dict(row)
                    d["category"] = "TRANSFER"
                    records.append(d)

            if filter_type in ("ALL", "VERIFY"):
                cursor.execute(
                    "SELECT * FROM verifications ORDER BY id DESC LIMIT ?", (limit,)
                )
                for row in cursor.fetchall():
                    d = dict(row)
                    d["category"] = "VERIFY"
                    d["task_type"] = f"VERIFY ({d.get('mode', '').upper()})"
                    records.append(d)

            # Sort by timestamp descending
            records.sort(key=lambda x: str(x.get("timestamp", "")), reverse=True)
            return records[:limit]
        finally:
            conn.close()


def delete_history_entry(category: str, record_id: int) -> bool:
    """Delete a single history entry by category ('TRANSFER' or 'VERIFY') and ID."""
    init_db()
    table = "transfers" if category.upper() == "TRANSFER" else "verifications"
    with _LOCK:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM {table} WHERE id = ?", (record_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()


def clear_all_history() -> bool:
    """Clear all records from both transfers and verifications tables."""
    init_db()
    with _LOCK:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM transfers")
            cursor.execute("DELETE FROM verifications")
            conn.commit()
            cursor.execute("VACUUM")
            return True
        finally:
            conn.close()


def get_stats_summary() -> dict[str, Any]:
    """Calculate aggregate statistics for Home Dashboard."""
    init_db()
    with _LOCK:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    COUNT(*) as total_transfers,
                    COALESCE(SUM(total_bytes), 0) as total_bytes_transferred,
                    COALESCE(SUM(total_files), 0) as total_files_transferred,
                    COALESCE(MAX(peak_speed_mbps), 0) as max_speed_mbps
                FROM transfers WHERE status = 'COMPLETED'
                """
            )
            t_row = cursor.fetchone()

            cursor.execute(
                """
                SELECT
                    COUNT(*) as total_audits,
                    COALESCE(SUM(matched_count), 0) as total_verified_files,
                    COALESCE(SUM(mismatch_count), 0) as total_mismatches
                FROM verifications
                """
            )
            v_row = cursor.fetchone()

            return {
                "total_transfers": t_row["total_transfers"] if t_row else 0,
                "total_bytes_transferred": t_row["total_bytes_transferred"] if t_row else 0,
                "total_files_transferred": t_row["total_files_transferred"] if t_row else 0,
                "max_speed_mbps": round(t_row["max_speed_mbps"], 2) if t_row else 0.0,
                "total_audits": v_row["total_audits"] if v_row else 0,
                "total_verified_files": v_row["total_verified_files"] if v_row else 0,
                "total_mismatches": v_row["total_mismatches"] if v_row else 0,
            }
        finally:
            conn.close()
