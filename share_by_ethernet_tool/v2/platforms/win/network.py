"""Windows Network and Hardware Telemetry Detector.

Detects active Ethernet and Wi-Fi adapters via PowerShell, link speeds, IPv4 addresses,
drive storage capacities, and SMB roundtrip latency.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import socket
import subprocess
import time
from typing import Any, Dict, List, Optional


def get_machine_info() -> dict[str, Any]:
    hostname = socket.gethostname()
    try:
        primary_ip = socket.gethostbyname(hostname)
    except Exception:
        primary_ip = "127.0.0.1"

    return {
        "hostname": hostname,
        "username": os.environ.get("USERNAME", "User"),
        "primary_ip": primary_ip,
        "os": "Windows (NT)",
    }


def get_network_adapters() -> list[dict[str, Any]]:
    adapters: list[dict[str, Any]] = []
    ip_map: dict[str, list[str]] = {}

    # 1. Query IPv4 addresses
    try:
        res_ips = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-NetIPAddress -AddressFamily IPv4 | Select-Object InterfaceAlias, IPAddress, PrefixLength | ConvertTo-Json -Compress",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if res_ips.stdout.strip():
            data = json.loads(res_ips.stdout.strip())
            if isinstance(data, dict):
                data = [data]
            for item in data:
                alias = item.get("InterfaceAlias", "")
                ip = item.get("IPAddress", "")
                if alias and ip and not ip.startswith("127."):
                    if alias not in ip_map:
                        ip_map[alias] = []
                    ip_map[alias].append(ip)
    except Exception:
        pass

    # 2. Query Net Adapters
    try:
        res = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-NetAdapter | Select-Object Name, InterfaceDescription, Status, LinkSpeed, MacAddress | ConvertTo-Json -Compress",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if res.stdout.strip():
            data = json.loads(res.stdout.strip())
            if isinstance(data, dict):
                data = [data]
            for item in data:
                name = item.get("Name", "")
                desc = item.get("InterfaceDescription", "")
                status = item.get("Status", "Unknown")
                speed = item.get("LinkSpeed", "N/A")
                mac = item.get("MacAddress", "")
                ips = ip_map.get(name, [])

                is_wifi = any(w in name.lower() or w in desc.lower() for w in ("wi-fi", "wifi", "wireless", "wlan", "802.11", "bluetooth"))
                is_ethernet = (not is_wifi) and any(
                    e in name.lower() or e in desc.lower()
                    for e in ("ethernet", "lan", "gigabit", "2.5g", "10g", "pcie", "realtek", "intel")
                )

                adapters.append(
                    {
                        "name": name,
                        "description": desc,
                        "status": status,
                        "speed": speed,
                        "mac": mac,
                        "ips": ips,
                        "is_ethernet": is_ethernet,
                        "is_up": status.lower() == "up",
                    }
                )
    except Exception:
        pass

    adapters.sort(key=lambda a: (not a["is_up"], not a["is_ethernet"], a["name"]))
    return adapters


def get_disk_drives() -> list[dict[str, Any]]:
    drives: list[dict[str, Any]] = []
    try:
        drive_list = os.listdrives() if hasattr(os, "listdrives") else ["C:\\", "D:\\"]
        for d in drive_list:
            if os.path.exists(d):
                try:
                    usage = shutil.disk_usage(d)
                    total = usage.total
                    used = usage.used
                    free = usage.free
                    pct = round((used / total) * 100, 1) if total > 0 else 0
                    drives.append(
                        {
                            "drive": d.rstrip("\\"),
                            "path": d,
                            "total_bytes": total,
                            "used_bytes": used,
                            "free_bytes": free,
                            "pct_used": pct,
                        }
                    )
                except (PermissionError, OSError):
                    pass
    except Exception:
        pass
    return drives


def measure_smb_latency(host_or_path: str, port: int = 445, timeout: float = 1.2) -> float | None:
    if not host_or_path:
        return None
    m = re.match(r"^\\\\([^\\]+)", host_or_path)
    host = m.group(1) if m else host_or_path.strip().strip("\\")

    t0 = time.time()
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        s.close()
        return round((time.time() - t0) * 1000.0, 1)
    except Exception:
        return None
