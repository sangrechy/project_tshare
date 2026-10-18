"""Abstract Base Class for Platform-Specific System Adapters.

Defines the contract that Windows, Linux, and macOS platform implementations must fulfill:
- Network interface and link speed discovery
- Storage drive capacity tracking
- High-speed transfer process orchestration (Robocopy / rsync)
- Kernel process I/O speed measurement
- Elevated network share provisioning and permission revocation
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple


class PlatformAdapter(ABC):
    @abstractmethod
    def get_os_name(self) -> str:
        """Return canonical OS name ('windows', 'linux', 'darwin')."""
        pass

    @abstractmethod
    def get_network_adapters(self) -> list[dict[str, Any]]:
        """Discover active network interfaces, link speeds, IPv4 addresses, and MAC."""
        pass

    @abstractmethod
    def get_disk_drives(self) -> list[dict[str, Any]]:
        """Retrieve local drive storage metrics (total, used, free space)."""
        pass

    @abstractmethod
    def measure_latency(self, host_or_path: str, port: int = 445, timeout: float = 1.2) -> float | None:
        """Measure TCP connect latency in milliseconds."""
        pass

    @abstractmethod
    def list_shares(self) -> list[dict[str, str]]:
        """Enumerate active network shares on this system."""
        pass

    @abstractmethod
    def create_share(self, folder_path: str, share_name: str) -> tuple[bool, str, dict[str, Any]]:
        """Provision a network share with elevation/password handling if required.

        Returns (success, message, lease_snapshot_metadata).
        """
        pass

    @abstractmethod
    def revoke_share(self, share_name: str, folder_path: str, lease_info: dict[str, Any]) -> tuple[bool, str]:
        """Revoke temporary share permissions and restore system state."""
        pass

    @abstractmethod
    def build_transfer_command(
        self,
        source: str,
        dest: str,
        threads: int = 8,
        restartable: bool = True,
        unbuffered: bool = True,
        exclude_older: bool = True,
        exclude_system: bool = True,
        retry_count: int = 2,
        retry_wait: int = 2,
    ) -> list[str]:
        """Construct the platform-optimal transfer command (Robocopy on Windows, rsync on Linux/macOS)."""
        pass

    @abstractmethod
    def query_process_io_speed(self, pid: int) -> tuple[int, int] | None:
        """Query kernel I/O counters for the given process PID (read_bytes, write_bytes)."""
        pass

    @abstractmethod
    def get_process_identity(self, pid: int) -> tuple[str, int] | None:
        """Verify process identity (executable_path, creation_timestamp)."""
        pass
