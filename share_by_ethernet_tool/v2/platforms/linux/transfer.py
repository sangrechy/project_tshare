"""Linux Transfer Implementation utilizing rsync and /proc/[pid]/io Telemetry."""
from __future__ import annotations

import os
import subprocess
from typing import Any, Dict, List, Optional, Tuple


def get_process_identity(pid: int) -> tuple[str, int] | None:
    """Read process executable and starttime from /proc/[pid]/stat."""
    stat_file = f"/proc/{pid}/stat"
    if not os.path.exists(stat_file):
        return None
    try:
        with open(stat_file, "r") as f:
            content = f.read().split()
            # Field 2 is (comm), Field 22 is starttime
            comm = content[1].strip("()")
            starttime = int(content[21])
            return comm, starttime
    except Exception:
        return None


def query_process_io_counters(pid: int) -> tuple[int, int] | None:
    """Read true kernel I/O counters from Linux /proc/[pid]/io."""
    io_file = f"/proc/{pid}/io"
    if not os.path.exists(io_file):
        return None
    try:
        r_bytes = 0
        w_bytes = 0
        with open(io_file, "r") as f:
            for line in f:
                if line.startswith("read_bytes:"):
                    r_bytes = int(line.split(":")[1].strip())
                elif line.startswith("write_bytes:"):
                    w_bytes = int(line.split(":")[1].strip())
        return r_bytes, w_bytes
    except Exception:
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
    # Ensure proper trailing slash for directory recursive copy
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
        cmd.append("--update")  # skip files that are newer on receiver
    if exclude_system:
        cmd.extend(["--exclude=.DS_Store", "--exclude=thumbs.db", "--exclude=*.tmp"])

    cmd.extend([src_clean, dst_clean])
    return cmd
