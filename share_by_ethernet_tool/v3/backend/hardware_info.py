"""
T-Share v3 Hardware Telemetry & Detector
Collects hardware metrics to drive live gauges and resource governor sliders.
"""

import os
import socket
import shutil
import psutil
from typing import Dict, List, Any


def get_network_interfaces() -> List[Dict[str, Any]]:
    """Enumerate network interfaces, detecting link-local Ethernet and LAN IPs."""
    interfaces = []
    try:
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()

        for name, addr_list in addrs.items():
            stat = stats.get(name)
            is_up = stat.isup if stat else True
            speed_mbps = stat.speed if stat and stat.speed > 0 else 1000

            for addr in addr_list:
                if addr.family == socket.AF_INET and not addr.address.startswith("127."):
                    ip = addr.address
                    is_link_local = ip.startswith("169.254.")
                    
                    # Detect if likely Ethernet adapter
                    lname = name.lower()
                    is_ethernet = any(k in lname for k in ["eth", "en", "ethernet", "lan", "realtek", "intel"])

                    interfaces.append({
                        "name": name,
                        "ip": ip,
                        "netmask": addr.netmask,
                        "is_up": is_up,
                        "speed_mbps": speed_mbps,
                        "is_link_local": is_link_local,
                        "is_ethernet": is_ethernet,
                        "priority": 1 if (is_link_local and is_ethernet) else (2 if is_ethernet else 3)
                    })
    except Exception:
        pass

    # Sort so best direct-ethernet adapter is first
    interfaces.sort(key=lambda x: x["priority"])
    return interfaces

def get_detailed_network_info() -> Dict[str, Any]:
    """Returns categorized Wi-Fi and Ethernet connection modules."""
    wifi_entry = None
    eth_entry = None

    try:
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()

        for name, addr_list in addrs.items():
            stat = stats.get(name)
            is_up = stat.isup if stat else True
            speed_mbps = stat.speed if stat and stat.speed > 0 else 1000

            lname = name.lower()
            is_wifi = any(w in lname for w in ["wl", "wi-fi", "wifi", "wireless", "802.11"])
            is_eth = any(e in lname for e in ["eth", "en", "ethernet", "lan", "realtek", "intel"]) and not is_wifi

            ipv4 = ""
            for addr in addr_list:
                if addr.family == socket.AF_INET and not addr.address.startswith("127."):
                    if addr.address.startswith("192.168.123."):
                        ipv4 = addr.address
                        break
                    elif not ipv4:
                        ipv4 = addr.address

            is_direct_wire_ip = bool(ipv4 and (ipv4.startswith("192.168.123.") or ipv4.startswith("169.254.")))
            has_ip = bool(ipv4) if is_wifi else is_direct_wire_ip

            info = {
                "name": name,
                "ip": ipv4,
                "is_up": is_up,
                "speed_mbps": speed_mbps,
                "has_ip": has_ip,
                "display": ipv4 if ipv4 else "Unconfigured"
            }

            if is_wifi and not wifi_entry:
                wifi_entry = info
            elif is_eth and not eth_entry:
                eth_entry = info
    except Exception:
        pass

    return {
        "wifi": wifi_entry,
        "ethernet": eth_entry
    }


def get_primary_ip() -> str:
    """Returns the most appropriate IP address for direct transfer."""
    ifaces = get_network_interfaces()
    if ifaces:
        return ifaces[0]["ip"]
    
    # Fallback using standard socket probe
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def get_disk_space(path: str = ".") -> Dict[str, Any]:
    """Returns free and total disk space in bytes for the volume containing path."""
    try:
        abs_path = os.path.abspath(path)
        total, used, free = shutil.disk_usage(abs_path)
        return {
            "total_bytes": total,
            "used_bytes": used,
            "free_bytes": free,
            "free_gb": round(free / (1024 ** 3), 2),
            "percent_used": round((used / total) * 100, 1)
        }
    except Exception:
        return {"total_bytes": 0, "used_bytes": 0, "free_bytes": 0, "free_gb": 0, "percent_used": 0}


def get_hardware_telemetry(disk_path: str = ".") -> Dict[str, Any]:
    """Comprehensive hardware snapshot for Home tab and Settings sliders."""
    ram = psutil.virtual_memory()
    cpu_percent = psutil.cpu_percent(interval=None)
    cpu_cores = psutil.cpu_count(logical=True) or 4
    disk = get_disk_space(disk_path)
    interfaces = get_network_interfaces()

    return {
        "cpu": {
            "percent": cpu_percent,
            "cores": cpu_cores
        },
        "ram": {
            "total_bytes": ram.total,
            "available_bytes": ram.available,
            "total_gb": round(ram.total / (1024 ** 3), 1),
            "available_gb": round(ram.available / (1024 ** 3), 1),
            "percent_used": ram.percent
        },
        "disk": disk,
        "network": {
            "primary_ip": interfaces[0]["ip"] if interfaces else "127.0.0.1",
            "interfaces": interfaces
        }
    }
