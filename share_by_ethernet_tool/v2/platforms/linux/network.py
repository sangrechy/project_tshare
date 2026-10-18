"""Linux Network and Hardware Telemetry Detector.

Detects active Ethernet and Wi-Fi interfaces via /sys/class/net and 'ip',
link speeds via ethtool/sysfs, IPv4 addresses, and partition capacities.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import socket
import subprocess
import threading
import time
from typing import Any, Dict, List, Optional

_LOCK = threading.Lock()
_CACHED_MACHINE_INFO: dict[str, Any] | None = None
_CACHED_ADAPTERS: list[dict[str, Any]] = []
_ADAPTERS_TIMESTAMP: float = 0.0
_CACHED_DRIVES: list[dict[str, Any]] = []
_DRIVES_TIMESTAMP: float = 0.0


def get_machine_info() -> dict[str, Any]:
    global _CACHED_MACHINE_INFO
    with _LOCK:
        if _CACHED_MACHINE_INFO is not None:
            return _CACHED_MACHINE_INFO

    hostname = socket.gethostname()
    try:
        primary_ip = socket.gethostbyname(hostname)
    except Exception:
        primary_ip = "127.0.0.1"

    info = {
        "hostname": hostname,
        "username": os.environ.get("USER", "user"),
        "primary_ip": primary_ip,
        "os": "Linux",
    }
    with _LOCK:
        _CACHED_MACHINE_INFO = info
    return info


def get_network_adapters() -> list[dict[str, Any]]:
    global _CACHED_ADAPTERS, _ADAPTERS_TIMESTAMP
    now = time.time()
    with _LOCK:
        if _CACHED_ADAPTERS and (now - _ADAPTERS_TIMESTAMP < 15.0):
            return list(_CACHED_ADAPTERS)

    adapters: list[dict[str, Any]] = []
    ip_map: dict[str, list[str]] = {}

    # Query IP addresses via 'ip -j addr'
    try:
        res = subprocess.run(["ip", "-j", "addr"], capture_output=True, text=True, timeout=3)
        if res.returncode == 0 and res.stdout.strip():
            data = json.loads(res.stdout.strip())
            for iface in data:
                ifname = iface.get("ifname", "")
                addrs = []
                for addr_info in iface.get("addr_info", []):
                    if addr_info.get("family") == "inet":
                        ip = addr_info.get("local")
                        if ip and not ip.startswith("127."):
                            addrs.append(ip)
                if addrs:
                    ip_map[ifname] = addrs
    except Exception:
        pass

    # Read sysfs /sys/class/net
    net_path = "/sys/class/net"
    if os.path.exists(net_path):
        for iface in os.listdir(net_path):
            if iface == "lo":
                continue
            iface_dir = os.path.join(net_path, iface)

            # Check operstate
            status = "Disconnected"
            try:
                with open(os.path.join(iface_dir, "operstate"), "r") as f:
                    st = f.read().strip().lower()
                    if st in ("up", "unknown"):
                        status = "Up"
            except Exception:
                pass

            # Check speed
            speed = "N/A"
            try:
                with open(os.path.join(iface_dir, "speed"), "r") as f:
                    s_val = int(f.read().strip())
                    if s_val > 0:
                        speed = f"{s_val} Mbps"
            except Exception:
                pass

            # Check MAC
            mac = ""
            try:
                with open(os.path.join(iface_dir, "address"), "r") as f:
                    mac = f.read().strip().upper()
            except Exception:
                pass

            is_wifi = iface.startswith("wl") or os.path.exists(os.path.join(iface_dir, "wireless"))
            is_eth = iface.startswith("en") or iface.startswith("eth") or (not is_wifi)

            adapters.append(
                {
                    "name": iface,
                    "description": f"Linux {'Ethernet' if is_eth else 'Wireless'} Interface ({iface})",
                    "status": status,
                    "speed": speed,
                    "mac": mac,
                    "ips": ip_map.get(iface, []),
                    "is_ethernet": is_eth and not is_wifi,
                    "is_up": status == "Up",
                }
            )

    adapters.sort(key=lambda a: (not a["is_up"], not a["is_ethernet"], a["name"]))
    with _LOCK:
        _CACHED_ADAPTERS = adapters
        _ADAPTERS_TIMESTAMP = now
        return list(_CACHED_ADAPTERS)


def get_disk_drives() -> list[dict[str, Any]]:
    global _CACHED_DRIVES, _DRIVES_TIMESTAMP
    now = time.time()
    with _LOCK:
        if _CACHED_DRIVES and (now - _DRIVES_TIMESTAMP < 6.0):
            return list(_CACHED_DRIVES)

    drives: list[dict[str, Any]] = []
    checked_mounts = set()

    # Read /proc/mounts to find real disks
    mount_points = ["/"]
    if os.path.exists("/proc/mounts"):
        try:
            with open("/proc/mounts", "r") as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2 and parts[0].startswith("/dev/"):
                        mp = parts[1]
                        if not mp.startswith(("/snap", "/boot", "/var/lib/docker")):
                            mount_points.append(mp)
        except Exception:
            pass

    for mp in mount_points:
        if mp in checked_mounts or not os.path.exists(mp):
            continue
        checked_mounts.add(mp)
        try:
            usage = shutil.disk_usage(mp)
            pct = round((usage.used / usage.total) * 100, 1) if usage.total > 0 else 0
            drives.append(
                {
                    "drive": mp,
                    "path": mp,
                    "total_bytes": usage.total,
                    "used_bytes": usage.used,
                    "free_bytes": usage.free,
                    "pct_used": pct,
                }
            )
        except (PermissionError, OSError):
            pass

    with _LOCK:
        _CACHED_DRIVES = drives
        _DRIVES_TIMESTAMP = now
        return list(_CACHED_DRIVES)


def measure_tcp_latency(host_or_path: str, port: int = 445, timeout: float = 1.2) -> float | None:
    if not host_or_path:
        return None
    m = re.match(r"^\\\\([^\\]+)", host_or_path) or re.match(r"^//([^/]+)", host_or_path)
    host = m.group(1) if m else host_or_path.strip().strip("\\/")

    t0 = time.time()
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        s.close()
        return round((time.time() - t0) * 1000.0, 1)
    except Exception:
        return None
