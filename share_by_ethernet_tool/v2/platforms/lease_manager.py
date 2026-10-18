"""Persistent Share Lease Journal & Crash-Recovery Cleanup Manager.

Ensures that any temporary network shares created during a transfer session
are reliably revoked when the session ends or immediately upon next application
startup if the application was unexpectedly terminated, crashed, or powered off.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime
from typing import Any, Dict, Optional

LEASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEASE_FILE = os.path.join(LEASE_DIR, "share_lease.json")
FALLBACK_LEASE_FILE = os.path.join(tempfile.gettempdir(), "tshare_share_lease.json")


def _get_active_lease_path() -> str:
    if os.path.exists(LEASE_FILE):
        return LEASE_FILE
    if os.path.exists(FALLBACK_LEASE_FILE):
        return FALLBACK_LEASE_FILE
    return LEASE_FILE


def record_share_lease(
    share_name: str,
    folder_path: str,
    platform_name: str,
    metadata: Optional[dict[str, Any]] = None,
) -> None:
    """Record an active share lease before applying network share permissions."""
    lease_data = {
        "active": True,
        "share_name": share_name,
        "folder_path": os.path.abspath(folder_path),
        "platform": platform_name,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "pid": os.getpid(),
        "metadata": metadata or {},
    }
    for target in (LEASE_FILE, FALLBACK_LEASE_FILE):
        try:
            with open(target, "w", encoding="utf-8") as f:
                json.dump(lease_data, f, indent=2)
            break
        except OSError:
            continue


def get_active_share_lease() -> dict[str, Any] | None:
    """Read the active lease if present."""
    p = _get_active_lease_path()
    if not os.path.exists(p):
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("active"):
            return data
    except Exception:
        pass
    return None


def clear_share_lease() -> None:
    """Remove lease files once share is safely revoked."""
    for p in (LEASE_FILE, FALLBACK_LEASE_FILE):
        try:
            if os.path.exists(p):
                os.remove(p)
        except OSError:
            pass


def startup_cleanup_orphaned_shares(adapter: Any) -> dict[str, Any] | None:
    """Invoked on application boot before any other subsystem loads.

    Detects if an active share was left open from a prior abrupt shutdown/crash
    and immediately revokes the permissions and deletes the share.
    """
    lease = get_active_share_lease()
    if not lease:
        return None

    share_name = lease.get("share_name", "")
    folder_path = lease.get("folder_path", "")
    platform_name = lease.get("platform", "")
    meta = lease.get("metadata", {})

    print(f"[T-Share Safety] Detected orphaned share lease '{share_name}' from prior session ({lease.get('created_at')}).")
    print(f"[T-Share Safety] Initiating immediate startup permission rollback...")

    try:
        ok, msg = adapter.revoke_share(
            share_name=share_name,
            folder_path=folder_path,
            lease_info=meta,
        )
        clear_share_lease()
        print(f"[T-Share Safety] Orphaned share revocation complete: {msg}")
        return {
            "revoked": ok,
            "share_name": share_name,
            "folder_path": folder_path,
            "message": msg,
            "previous_session_time": lease.get("created_at"),
        }
    except Exception as exc:
        print(f"[T-Share Safety] Error revoking orphaned share: {exc}")
        clear_share_lease()
        return {
            "revoked": False,
            "share_name": share_name,
            "folder_path": folder_path,
            "message": str(exc),
        }
