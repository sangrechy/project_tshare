"""Peer-to-Peer Auto-Discovery over Direct Ethernet & Local Subnet.

Continuously broadcasts and listens for lightweight UDP beacons on port 49555.
Allows two laptops connected via direct Ethernet cable (APIPA 169.254.x.x) or
local network to discover each other in under 1 second without human intervention,
eliminating manual IP entry, DNS/NetBIOS resolution, or Samba/SMB setup.
"""
from __future__ import annotations

import json
import os
import socket
import sys
import threading
import time
from typing import Any, Dict, List, Optional

DISCOVERY_PORT = 49555
BEACON_INTERVAL = 1.2
PEER_TIMEOUT = 4.0
MAGIC_HEADER = "TSHARE_V2"

_DISCOVERY_ENGINE: Optional[PeerDiscoveryEngine] = None
_ENGINE_LOCK = threading.Lock()


class PeerDiscoveryEngine:
    def __init__(self, transfer_port: int = 52100) -> None:
        self.transfer_port = transfer_port
        self.hostname = socket.gethostname()
        self.node_id = f"{self.hostname}_{os.getpid()}_{int(time.time())}"
        self.peers: dict[str, dict[str, Any]] = {}  # peer_id -> dict
        self._lock = threading.Lock()
        self._running = False
        self._broadcast_thread: threading.Thread | None = None
        self._listen_thread: threading.Thread | None = None

    def start(self) -> None:
        """Start discovery broadcaster and listener threads."""
        if self._running:
            return
        self._running = True

        self._listen_thread = threading.Thread(
            target=self._listen_loop, daemon=True, name="TSharePeerDiscoveryListener"
        )
        self._listen_thread.start()

        self._broadcast_thread = threading.Thread(
            target=self._broadcast_loop, daemon=True, name="TSharePeerDiscoveryBroadcaster"
        )
        self._broadcast_thread.start()

    def stop(self) -> None:
        """Stop discovery threads."""
        self._running = False

    def get_peers(self) -> list[dict[str, Any]]:
        """Return list of active discovered peers, pruning timed-out entries."""
        now = time.time()
        active: list[dict[str, Any]] = []
        with self._lock:
            expired = [pid for pid, p in self.peers.items() if now - p["last_seen"] > PEER_TIMEOUT]
            for pid in expired:
                del self.peers[pid]
            for p in self.peers.values():
                active.append(dict(p))
        return sorted(active, key=lambda x: x["hostname"])

    def _listen_loop(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if hasattr(socket, "SO_REUSEPORT") and sys.platform != "win32":
                try:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                except Exception:
                    pass
            sock.bind(("", DISCOVERY_PORT))
            sock.settimeout(1.0)
        except Exception as e:
            # If port bound or blocked, cannot listen
            return

        while self._running:
            try:
                data, addr = sock.recvfrom(2048)
                msg = json.loads(data.decode("utf-8", errors="ignore"))
                if msg.get("magic") != MAGIC_HEADER:
                    continue
                sender_node = msg.get("node_id", "")
                if sender_node == self.node_id:
                    continue  # Ignore self beacons

                peer_ip = addr[0]
                peer_port = int(msg.get("transfer_port", self.transfer_port))
                hostname = str(msg.get("hostname", peer_ip))
                platform_os = str(msg.get("platform", "unknown"))

                with self._lock:
                    self.peers[sender_node] = {
                        "node_id": sender_node,
                        "ip": peer_ip,
                        "port": peer_port,
                        "hostname": hostname,
                        "platform": platform_os,
                        "last_seen": time.time(),
                        "is_direct_ethernet": peer_ip.startswith("169.254."),
                    }
            except (socket.timeout, TimeoutError):
                continue
            except Exception:
                continue

        try:
            sock.close()
        except Exception:
            pass

    def _broadcast_loop(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(0.5)
        except Exception:
            return

        while self._running:
            try:
                payload = json.dumps({
                    "magic": MAGIC_HEADER,
                    "node_id": self.node_id,
                    "hostname": self.hostname,
                    "platform": sys.platform,
                    "transfer_port": self.transfer_port,
                    "time": time.time(),
                }).encode("utf-8")

                # Targets: Limited broadcast, Link-Local directed broadcast, and adapter broadcasts
                targets = ["255.255.255.255", "169.254.255.255"]

                # Try sending to targets
                for target in targets:
                    try:
                        sock.sendto(payload, (target, DISCOVERY_PORT))
                    except Exception:
                        pass

            except Exception:
                pass

            time.sleep(BEACON_INTERVAL)

        try:
            sock.close()
        except Exception:
            pass


def get_discovery_engine(transfer_port: int = 52100) -> PeerDiscoveryEngine:
    global _DISCOVERY_ENGINE
    with _ENGINE_LOCK:
        if _DISCOVERY_ENGINE is None:
            _DISCOVERY_ENGINE = PeerDiscoveryEngine(transfer_port=transfer_port)
            _DISCOVERY_ENGINE.start()
        return _DISCOVERY_ENGINE
