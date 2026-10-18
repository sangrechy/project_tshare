"""macOS Transfer Implementation utilizing rsync."""
from __future__ import annotations

import os
import subprocess
from typing import Any, Dict, List, Optional, Tuple


def get_process_identity(pid: int) -> tuple[str, int] | None:
    try:
        raw = subprocess.check_output(["ps", "-p", str(pid), "-o", "comm=,lstart="], text=True, stderr=subprocess.DEVNULL)
        parts = raw.strip().split(None, 1)
        if parts:
            comm = parts[0]
            start_str = parts[1] if len(parts) > 1 else ""
            return comm, hash(start_str)
    except Exception:
        pass
    return None


def query_process_io_counters(pid: int) -> tuple[int, int] | None:
    # macOS does not expose /proc/[pid]/io.
    return None


def build_rsync_command(
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
    src_clean = source if source.endswith("/") else source + "/"
    dst_clean = dest if dest.endswith("/") else dest + "/"

    cmd = [
        "rsync",
        "-avh",
        "--progress",
        "--stats",
    ]
    if restartable:
        cmd.extend(["--partial", "--append-verify"])
    if unbuffered:
        cmd.append("--inplace")
    if exclude_older:
        cmd.append("--update")
    if exclude_system:
        cmd.extend(["--exclude=.DS_Store", "--exclude=thumbs.db", "--exclude=*.tmp"])

    cmd.extend([src_clean, dst_clean])
    return cmd
