"""macOS Platform Adapter implementation."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from ..base import PlatformAdapter
from .network import get_machine_info, get_network_adapters, get_disk_drives, measure_tcp_latency
from .share import list_mac_shares, create_mac_share, revoke_mac_share
from .transfer import build_rsync_command, query_process_io_counters, get_process_identity


class MacAdapter(PlatformAdapter):
    def get_os_name(self) -> str:
        return "darwin"

    def get_network_adapters(self) -> list[dict[str, Any]]:
        return get_network_adapters()

    def get_disk_drives(self) -> list[dict[str, Any]]:
        return get_disk_drives()

    def measure_latency(self, host_or_path: str, port: int = 445, timeout: float = 1.2) -> float | None:
        return measure_tcp_latency(host_or_path, port=port, timeout=timeout)

    def list_shares(self) -> list[dict[str, str]]:
        return list_mac_shares()

    def create_share(self, folder_path: str, share_name: str) -> tuple[bool, str, dict[str, Any]]:
        return create_mac_share(folder_path, share_name)

    def revoke_share(self, share_name: str, folder_path: str, lease_info: dict[str, Any]) -> tuple[bool, str]:
        return revoke_mac_share(share_name, folder_path, lease_info)

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
        return build_rsync_command(
            source=source,
            dest=dest,
            threads=threads,
            restartable=restartable,
            unbuffered=unbuffered,
            exclude_older=exclude_older,
            exclude_system=exclude_system,
            retry_count=retry_count,
            retry_wait=retry_wait,
        )

    def query_process_io_speed(self, pid: int) -> tuple[int, int] | None:
        return query_process_io_counters(pid)

    def get_process_identity(self, pid: int) -> tuple[str, int] | None:
        return get_process_identity(pid)
