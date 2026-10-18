"""Windows Transfer Implementation utilizing Robocopy and Kernel I/O Counters.

Provides unbuffered high-speed copying, safe resume (/Z /J /MT /XO),
and direct sampling of Windows kernel process I/O counters (GetProcessIoCounters).
"""
from __future__ import annotations

import ctypes
import os
import subprocess
from typing import Any, Dict, List, Optional, Tuple


class FILETIME(ctypes.Structure):
    _fields_ = [("low", ctypes.c_uint32), ("high", ctypes.c_uint32)]


class IO_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("ReadOperationCount", ctypes.c_uint64),
        ("WriteOperationCount", ctypes.c_uint64),
        ("OtherOperationCount", ctypes.c_uint64),
        ("ReadTransferCount", ctypes.c_uint64),
        ("WriteTransferCount", ctypes.c_uint64),
        ("OtherTransferCount", ctypes.c_uint64),
    ]


def get_process_identity(pid: int) -> tuple[str, int] | None:
    kernel = ctypes.windll.kernel32
    handle = kernel.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        return None
    try:
        buf = ctypes.create_unicode_buffer(32768)
        size = ctypes.c_uint32(len(buf))
        if not kernel.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            return None
        created, exited, kernel_t, user_t = FILETIME(), FILETIME(), FILETIME(), FILETIME()
        if not kernel.GetProcessTimes(handle, ctypes.byref(created), ctypes.byref(exited), ctypes.byref(kernel_t), ctypes.byref(user_t)):
            return None
        stamp = (created.high << 32) | created.low
        return buf.value, stamp
    finally:
        kernel.CloseHandle(handle)


def query_process_io_counters(pid: int) -> tuple[int, int] | None:
    kernel = ctypes.windll.kernel32
    handle = kernel.OpenProcess(0x0400, False, pid)
    if not handle:
        handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        return None
    try:
        io = IO_COUNTERS()
        if kernel.GetProcessIoCounters(handle, ctypes.byref(io)):
            return io.ReadTransferCount, io.WriteTransferCount
        return None
    finally:
        kernel.CloseHandle(handle)


def build_robocopy_command(
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
    cmd = [
        "robocopy.exe",
        source,
        dest,
        "/E",
        f"/MT:{max(1, min(128, threads))}",
        f"/R:{retry_count}",
        f"/W:{retry_wait}",
        "/NP",
        "/BYTES",
        "/NDL",
        "/FFT",
    ]
    if restartable:
        cmd.append("/Z")
    if unbuffered:
        cmd.append("/J")
    if exclude_older:
        cmd.append("/XO")
    if exclude_system:
        cmd.extend(["/XF", "thumbs.db", "desktop.ini", "*.tmp", "/XD", "$RECYCLE.BIN", "System Volume Information"])

    return cmd
