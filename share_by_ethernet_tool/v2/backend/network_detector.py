"""Network, Ethernet, and Hardware Telemetry Detector (Cross-Platform).

Delegates platform-specific network adapter detection, disk usage queries,
latency measurements, and elevated share provisioning to the active platform adapter
(Windows, Linux, or macOS) while managing the active share lease lifecycle.
"""
from __future__ import annotations

import os
import socket
from typing import Any, Dict, List, Optional, Tuple

from platforms import (
    clear_share_lease,
    get_active_share_lease,
    get_platform_adapter,
    record_share_lease,
)


def format_bytes(value: int | float | None) -> str:
    """Format byte count into human-readable string (B, KiB, MiB, GiB, TiB)."""
    if value is None or value < 0:
        return "0 B"
    val = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if val < 1024.0 or unit == "TiB":
            return f"{val:.1f} {unit}" if unit != "B" else f"{int(value):,} B"
        val /= 1024.0
    return f"{int(value):,} B"


def get_local_machine_info() -> dict[str, Any]:
    """Retrieve hostname, user, primary IP, and canonical OS."""
    hostname = socket.gethostname()
    try:
        primary_ip = socket.gethostbyname(hostname)
    except Exception:
        primary_ip = "127.0.0.1"

    adapter = get_platform_adapter()
    return {
        "hostname": hostname,
        "username": os.environ.get("USERNAME") or os.environ.get("USER", "User"),
        "primary_ip": primary_ip,
        "os": adapter.get_os_name().capitalize(),
    }


def get_network_adapters() -> list[dict[str, Any]]:
    """Retrieve network adapter status, link speed, and associated IPv4 addresses."""
    adapter = get_platform_adapter()
    return adapter.get_network_adapters()


def get_disk_drives() -> list[dict[str, Any]]:
    """Retrieve drive/volume letters or mount points and their capacities."""
    adapter = get_platform_adapter()
    raw_drives = adapter.get_disk_drives()
    for d in raw_drives:
        if "total_display" not in d:
            d["total_display"] = format_bytes(d.get("total_bytes", 0))
            d["used_display"] = format_bytes(d.get("used_bytes", 0))
            d["free_display"] = format_bytes(d.get("free_bytes", 0))
    return raw_drives


def measure_smb_latency(host_or_path: str, port: int = 445, timeout: float = 1.2) -> float | None:
    """Measure roundtrip TCP connect time to destination in milliseconds."""
    adapter = get_platform_adapter()
    return adapter.measure_latency(host_or_path, port=port, timeout=timeout)


def get_windows_shares() -> list[dict[str, str]]:
    """Enumerate existing network shares on this system."""
    adapter = get_platform_adapter()
    return adapter.list_shares()


def create_network_share(folder_path: str, share_name: str = "Transfers") -> tuple[bool, str]:
    """Provision a temporary network share on this system and record an active lease."""
    adapter = get_platform_adapter()
    ok, msg, lease_meta = adapter.create_share(folder_path, share_name)
    if ok:
        record_share_lease(
            share_name=share_name,
            folder_path=folder_path,
            platform_name=adapter.get_os_name(),
            metadata=lease_meta,
        )
    return ok, msg


def revoke_network_share(share_name: str, folder_path: str = "") -> tuple[bool, str]:
    """Revoke temporary share permissions and wipe lease file."""
    adapter = get_platform_adapter()
    lease = get_active_share_lease()
    meta = lease.get("metadata", {}) if lease else {}
    ok, msg = adapter.revoke_share(share_name, folder_path, meta)
    clear_share_lease()
    return ok, msg
