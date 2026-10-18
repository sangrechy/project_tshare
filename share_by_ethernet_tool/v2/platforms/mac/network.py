"""macOS Network and Hardware Telemetry Detector.

Detects active Ethernet and Wi-Fi interfaces via 'networksetup' and 'ifconfig',
IPv4 addresses, and volume capacities.
"""
from __future__ import annotations

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
        "username": os.environ.get("USER", "user"),
        "primary_ip": primary_ip,
        "os": "macOS (Darwin)",
    }


def get_network_adapters() -> list[dict[str, Any]]:
    adapters: list[dict[str, Any]] = []
    dev_map: dict[str, dict[str, str]] = {}

    # 1. Query hardware ports via networksetup
    try:
        raw = subprocess.check_output(["networksetup", "-listallhardwareports"], text=True, stderr=subprocess.DEVNULL, timeout=4)
        cur_port = ""
        for line in raw.splitlines():
            line = line.strip()
            if line.startswith("Hardware Port:"):
                cur_port = line.split(":", 1)[1].strip()
            elif line.startswith("Device:") and cur_port:
                dev = line.split(":", 1)[1].strip()
                dev_map[dev] = {"port": cur_port}
    except Exception:
        pass

    # 2. Query ifconfig for IP, status, and speed
    try:
        raw_if = subprocess.check_output(["ifconfig"], text=True, stderr=subprocess.DEVNULL, timeout=4)
        current_iface = None
        iface_data: dict[str, Any] = {}

        for line in raw_if.splitlines():
            if re.match(r"^[a-zA-Z0-9]+:", line):
                if current_iface and iface_data:
                    _append_mac_adapter(adapters, current_iface, iface_data, dev_map)
                current_iface = line.split(":")[0].strip()
                iface_data = {"ips": [], "status": "Disconnected", "speed": "N/A", "mac": ""}
            elif current_iface:
                line_s = line.strip()
                if line_s.startswith("inet ") and not line_s.startswith("inet 127."):
                    parts = line_s.split()
                    if len(parts) >= 2:
                        iface_data["ips"].append(parts[1])
                elif "status: active" in line_s:
                    iface_data["status"] = "Up"
                elif line_s.startswith("media:") and "baseT" in line_s:
                    m = re.search(r"(\d+baseT[^\s]*)", line_s)
                    if m:
                        iface_data["speed"] = m.group(1).replace("baseT", " Mbps")
                elif line_s.startswith("ether "):
                    iface_data["mac"] = line_s.split()[1].upper()

        if current_iface and iface_data:
            _append_mac_adapter(adapters, current_iface, iface_data, dev_map)
    except Exception:
        pass

    adapters.sort(key=lambda a: (not a["is_up"], not a["is_ethernet"], a["name"]))
    return adapters


def _append_mac_adapter(adapters: list, name: str, data: dict, dev_map: dict) -> None:
    if name == "lo0":
        return
    desc = dev_map.get(name, {}).get("port", f"macOS Network Interface ({name})")
    is_eth = "ethernet" in desc.lower() or "lan" in desc.lower() or "thunderbolt" in desc.lower()
    adapters.append(
        {
            "name": name,
            "description": desc,
            "status": data["status"],
            "speed": data["speed"],
            "mac": data["mac"],
            "ips": data["ips"],
            "is_ethernet": is_eth,
            "is_up": data["status"] == "Up",
        }
    )


def get_disk_drives() -> list[dict[str, Any]]:
    drives: list[dict[str, Any]] = []
    mounts = ["/"]
    vols = "/Volumes"
    if os.path.exists(vols):
        for v in os.listdir(vols):
            vp = os.path.join(vols, v)
            if os.path.isdir(vp):
                mounts.append(vp)

    for m in mounts:
        try:
            usage = shutil.disk_usage(m)
            pct = round((usage.used / usage.total) * 100, 1) if usage.total > 0 else 0
            drives.append(
                {
                    "drive": os.path.basename(m) or "/",
                    "path": m,
                    "total_bytes": usage.total,
                    "used_bytes": usage.used,
                    "free_bytes": usage.free,
                    "pct_used": pct,
                }
            )
        except (PermissionError, OSError):
            pass

    return drives


def measure_tcp_latency(host_or_path: str, port: int = 445, timeout: float = 1.2) -> float | None:
    if not host_or_path:
        return None
    m = re.match(r"^smb://([^/]+)", host_or_path) or re.match(r"^\\\\([^\\]+)", host_or_path)
    host = m.group(1) if m else host_or_path.strip().strip("\\/")

    t0 = time.time()
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        s.close()
        return round((time.time() - t0) * 1000.0, 1)
    except Exception:
        return None
