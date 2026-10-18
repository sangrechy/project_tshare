"""
T-Share v3 Peer Discovery Engine
Broadcasts and listens for local peers via UDP on port 52000.
Supports link-local 169.254.x.x direct Ethernet links with auto-pruning.
"""

import socket
import json
import time
import uuid
import threading
from typing import Dict, List, Any
from .protocol import DEFAULT_UDP_PORT, DEFAULT_TCP_PORT
from .hardware_info import get_network_interfaces


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
            # Prune peers not seen in last 6 seconds
            expired = [pid for pid, p in self._peers.items() if now - p.get("last_seen", 0) > 6.0]
            for pid in expired:
                del self._peers[pid]
            return list(self._peers.values())

    def _listen_loop(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
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
                    peer_info = {
                        "id": peer_id,
                        "name": msg.get("name", "Unknown Peer"),
                        "ip": addr[0],
                        "port": msg.get("port", DEFAULT_TCP_PORT),
                        "last_seen": time.time(),
                        "is_direct_ethernet": addr[0].startswith("169.254.")
                    }
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
                payload = json.dumps({
                    "app": "tshare-v3",
                    "id": self.node_id,
                    "name": self.hostname,
                    "port": self.tcp_port
                }).encode('utf-8')

                # Broadcast on standard 255.255.255.255
                try:
                    sock.sendto(payload, ("255.255.255.255", self.broadcast_port))
                except Exception:
                    pass

                # Also broadcast specifically on link-local interface subnets
                interfaces = get_network_interfaces()
                for iface in interfaces:
                    ip = iface.get("ip")
                    if ip and ip.startswith("169.254."):
                        try:
                            # 169.254.255.255 broadcast
                            sock.sendto(payload, ("169.254.255.255", self.broadcast_port))
                        except Exception:
                            pass
            except Exception:
                pass

            # Broadcast every 1.5 seconds
            time.sleep(1.5)

        sock.close()
