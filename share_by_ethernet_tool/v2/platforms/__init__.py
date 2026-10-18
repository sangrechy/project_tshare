"""Platform Subsystem Dispatcher.

Detects current operating system and loads the appropriate platform adapter:
- platforms/win (Windows: Robocopy, Win32 kernel I/O, PowerShell, net share)
- platforms/linux (Linux: rsync, /proc/io, sysfs/ip, Samba usershares)
- platforms/mac (macOS: rsync, scutil/networksetup, sharing CLI)

Also handles the startup recovery sweep to revoke any orphaned temporary shares left
from prior unexpected application termination or crashes.
"""
from __future__ import annotations

import sys
from typing import Any, Optional

from .base import PlatformAdapter
from .lease_manager import (
    clear_share_lease,
    get_active_share_lease,
    record_share_lease,
    startup_cleanup_orphaned_shares,
)

_CURRENT_ADAPTER: PlatformAdapter | None = None


def get_platform_adapter() -> PlatformAdapter:
    """Return singleton platform adapter for current operating system."""
    global _CURRENT_ADAPTER
    if _CURRENT_ADAPTER is not None:
        return _CURRENT_ADAPTER

    plat = sys.platform.lower()
    if plat.startswith("win"):
        from .win import WindowsAdapter
        _CURRENT_ADAPTER = WindowsAdapter()
    elif plat.startswith("linux"):
        from .linux import LinuxAdapter
        _CURRENT_ADAPTER = LinuxAdapter()
    elif plat.startswith("darwin"):
        from .mac import MacAdapter
        _CURRENT_ADAPTER = MacAdapter()
    else:
        # Fallback to linux/posix standard
        from .linux import LinuxAdapter
        _CURRENT_ADAPTER = LinuxAdapter()

    return _CURRENT_ADAPTER


def check_and_cleanup_startup_leases() -> dict[str, Any] | None:
    """Invoked at application startup before anything else to clean up orphaned shares."""
    adapter = get_platform_adapter()
    return startup_cleanup_orphaned_shares(adapter)
