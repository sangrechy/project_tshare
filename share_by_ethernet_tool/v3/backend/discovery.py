"""
T-Share v3 Peer Discovery Engine
Broadcasts and listens for local peers via UDP on port 52002.
Supports:
- Wi-Fi Assisted Direct Wire Discovery: Discovers peers across Wi-Fi LAN and exchanges
  direct Ethernet hardware details (Wire IP, MAC, IPv6 link-local).
- Connection Wire-Locking: Locks file transfer target exclusively to the physical
  Ethernet cable so 0 bytes transfer over Wi-Fi and the session survives turning off Wi-Fi.
- Subnet Auto-Alignment Detection: Proactively identifies when remote peer is on direct wire
  (e.g. 192.168.123.2) while local Ethernet needs 192.168.123.1.
"""

import socket
import json
import time
import uuid
import threading
from typing import Dict, List, Any, Optional
from .protocol import DEFAULT_UDP_PORT, DEFAULT_TCP_PORT
from .hardware_info import get_detailed_adapters


class PeerDiscovery:
    def __init__(self, tcp_port: int = DEFAULT_TCP_PORT, broadcast_port: int = DEFAULT_UDP_PORT):
        self.tcp_port = tcp_port
        self.broadcast_port = broadcast_port
        self.node_id = str(uuid.uuid4())[:8]
        self.hostname = socket.gethostname()
        self._running = False
        self._peers: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._broadcast_thread: Optional[threading.Thread] = None
        self._listen_thread: Optional[threading.Thread] = None
        self._known_unicast_targets: set = set(["192.168.123.1", "192.168.123.2"])

    def start(self) -> None:
        """Starts peer broadcaster and listener threads."""
        if self._running:
            return
        self._running = True

        self._listen_thread = threading.Thread(target=self._listen_loop, daemon=True, name="DiscoveryListener")
        self._listen_thread.start()

        self._broadcast_thread = threading.Thread(target=self._broadcast_loop, daemon=True, name="DiscoveryBroadcaster")
        self._broadcast_thread.start()

    def stop(self) -> None:
        """Stops discovery service."""
        self._running = False

    def get_peers(self) -> List[Dict[str, Any]]:
        """Returns list of currently active, non-expired peers."""
        now = time.time()
        with self._lock:
            # Prune peers not seen in last 8 seconds
            expired = [pid for pid, p in self._peers.items() if now - p.get("last_seen", 0) > 8.0]
            for pid in expired:
                del self._peers[pid]
            return list(self._peers.values())

    def get_subnet_alignment_status(self) -> Optional[Dict[str, Any]]:
        """
        Detects if a discovered peer is waiting on direct wire (192.168.123.x)
        while the local Ethernet adapter needs IP configuration (192.168.123.1).
        """
        active_peers = self.get_peers()
        wire_peer = next((p for p in active_peers if p.get("wire_ip", "").startswith("192.168.123.")), None)
        if not wire_peer:
            return None

        remote_wire_ip = wire_peer["wire_ip"]
        eths, _, _ = get_detailed_adapters()
        if not eths:
            return None

        local_eth = eths[0]
        local_ip = local_eth.get("ip", "")
        if not local_ip.startswith("192.168.123."):
            return {
                "mismatch": True,
                "remote_wire_ip": remote_wire_ip,
                "remote_name": wire_peer.get("name", "Peer"),
                "local_eth_name": local_eth.get("name", "Ethernet"),
                "local_eth_ip": local_ip or "Unconfigured",
                "suggested_local_ip": "192.168.123.1" if remote_wire_ip == "192.168.123.2" else "192.168.123.2"
            }
        return None

    def _listen_loop(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, 'SO_REUSEPORT'):
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except Exception:
                pass
        try:
            sock.bind(("0.0.0.0", self.broadcast_port))
        except Exception:
            sock.close()
            return

        sock.settimeout(1.0)
        while self._running:
            try:
                data, addr = sock.recvfrom(4096)
                msg = json.loads(data.decode('utf-8'))

                # Check magic identifier and ensure not self
                if msg.get("app") == "tshare-v3" and msg.get("id") != self.node_id:
                    peer_id = msg.get("id")
                    sender_ip = addr[0]
                    eth_info = msg.get("ethernet", {})
                    wifi_info = msg.get("wifi", {})

                    wire_ip = eth_info.get("ip", "")
                    wire_mac = eth_info.get("mac", "")
                    wire_ipv6 = eth_info.get("ipv6_ll", "")

                    is_wire_source = sender_ip.startswith("192.168.123.") or sender_ip.startswith("169.254.")
                    is_wifi_source = not is_wire_source

                    # WIRE-LOCK LOGIC:
                    # If peer advertised a physical direct wire IP (e.g. 192.168.123.2),
                    # LOCK the primary connection target to the wire IP so 0 bytes travel over Wi-Fi!
                    if wire_ip:
                        target_ip = wire_ip
                        is_direct = True
                        is_wifi_assisted = is_wifi_source
                        medium = "wire_locked" if is_wifi_source else "ethernet"
                    elif wire_ipv6:
                        target_ip = wire_ipv6
                        is_direct = True
                        is_wifi_assisted = is_wifi_source
                        medium = "wire_locked"
                    elif is_wire_source:
                        target_ip = sender_ip
                        is_direct = True
                        is_wifi_assisted = False
                        medium = "ethernet"
                    else:
                        target_ip = sender_ip
                        is_direct = False
                        is_wifi_assisted = False
                        medium = "wifi"

                    peer_info = {
                        "id": peer_id,
                        "name": msg.get("name", "Unknown Peer"),
                        "ip": target_ip,
                        "wire_ip": wire_ip or (sender_ip if is_wire_source else ""),
                        "wire_mac": wire_mac,
                        "wire_ipv6": wire_ipv6,
                        "wifi_ip": wifi_info.get("ip", sender_ip if is_wifi_source else ""),
                        "port": msg.get("port", DEFAULT_TCP_PORT),
                        "last_seen": time.time(),
                        "is_direct_ethernet": is_direct,
                        "is_wifi_assisted": is_wifi_assisted,
                        "wire_locked": bool(wire_ip or wire_ipv6),
                        "medium": medium
                    }

                    # Track IP for direct unicast probes
                    if sender_ip and sender_ip not in self._known_unicast_targets:
                        self._known_unicast_targets.add(sender_ip)
                    if wire_ip and wire_ip not in self._known_unicast_targets:
                        self._known_unicast_targets.add(wire_ip)

                    with self._lock:
                        self._peers[peer_id] = peer_info

            except (socket.timeout, json.JSONDecodeError, UnicodeDecodeError):
                continue
            except Exception:
                if not self._running:
                    break
        sock.close()

    def _broadcast_loop(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(0.2)

        while self._running:
            try:
                eth_list, wifi_list, bcasts = get_detailed_adapters()
                primary_eth = eth_list[0] if eth_list else {}
                primary_wifi = wifi_list[0] if wifi_list else {}

                payload = json.dumps({
                    "app": "tshare-v3",
                    "id": self.node_id,
                    "name": self.hostname,
                    "port": self.tcp_port,
                    "wifi_assisted": True,
                    "ethernet": {
                        "name": primary_eth.get("name", ""),
                        "ip": primary_eth.get("ip", ""),
                        "mac": primary_eth.get("mac", ""),
                        "ipv6_ll": primary_eth.get("ipv6_ll", ""),
                        "is_up": primary_eth.get("is_up", False),
                        "speed_mbps": primary_eth.get("speed_mbps", 1000)
                    },
                    "wifi": {
                        "name": primary_wifi.get("name", ""),
                        "ip": primary_wifi.get("ip", ""),
                        "mac": primary_wifi.get("mac", "")
                    }
                }).encode('utf-8')

                # 1. Broadcast to all subnet broadcasts (Wi-Fi, Ethernet, Link-local, Global)
                for bcast_ip in bcasts:
                    try:
                        sock.sendto(payload, (bcast_ip, self.broadcast_port))
                    except Exception:
                        pass

                # 2. Directed unicast to wire IPs and discovered peers
                for target_ip in list(self._known_unicast_targets):
                    try:
                        sock.sendto(payload, (target_ip, self.broadcast_port))
                    except Exception:
                        pass

            except Exception:
                pass

            # Broadcast every 1.5 seconds
            time.sleep(1.5)

        sock.close()
