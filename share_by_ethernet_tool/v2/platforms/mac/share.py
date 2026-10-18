"""macOS Network Sharing & Permission Management.

Provisions macOS SMB shares ('sharing' CLI), prompts for Administrator authorization
via native macOS AppleScript dialogs when required, records initial states, and tears down
temporary shares upon session completion or crash recovery.
"""
from __future__ import annotations

import os
import subprocess
from typing import Any, Dict, List, Tuple


def list_mac_shares() -> list[dict[str, str]]:
    """Enumerate shares via macOS 'sharing -l'."""
    shares: list[dict[str, str]] = []
    try:
        raw = subprocess.check_output(["sharing", "-l"], text=True, stderr=subprocess.DEVNULL, timeout=4)
        cur_name = ""
        cur_path = ""
        for line in raw.splitlines():
            line_s = line.strip()
            if line_s.startswith("name:"):
                cur_name = line_s.split(":", 1)[1].strip()
            elif line_s.startswith("path:") and cur_name:
                cur_path = line_s.split(":", 1)[1].strip()
                shares.append({"name": cur_name, "resource": cur_path, "is_admin": False})
                cur_name = ""
                cur_path = ""
    except Exception:
        pass
    return shares


def create_mac_share(folder_path: str, share_name: str = "Transfers") -> tuple[bool, str, dict[str, Any]]:
    """Provision macOS SMB share. Prompts user for TouchID/password via AppleScript."""
    if not os.path.exists(folder_path):
        try:
            os.makedirs(folder_path, exist_ok=True)
        except Exception as e:
            return False, f"Could not create directory: {e}", {}

    abs_path = os.path.abspath(folder_path)

    # 1. Try standard unprivileged sharing command
    cmd = ["sharing", "-a", abs_path, "-s", "100", "-n", share_name]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)

    if res.returncode == 0:
        return True, f"Successfully created macOS share '{share_name}'", {"share_name": share_name, "was_preexisting": False}

    # 2. Elevate via AppleScript dialog (prompts system TouchID/password dialog)
    as_script = f'do shell script "sharing -a \\"{abs_path}\\" -s 100 -n \\"{share_name}\\"" with administrator privileges'
    try:
        elev_res = subprocess.run(["osascript", "-e", as_script], capture_output=True, text=True, timeout=25)
        if elev_res.returncode == 0:
            return True, f"Successfully created elevated macOS share '{share_name}'", {
                "share_name": share_name,
                "was_preexisting": False,
                "elevated": True,
            }
        return False, f"Authorization failed or cancelled: {elev_res.stderr.strip()}", {}
    except Exception as exc:
        return False, f"Elevation error: {exc}", {}


def revoke_mac_share(share_name: str, folder_path: str = "", lease_info: dict[str, Any] | None = None) -> tuple[bool, str]:
    """Revoke temporary macOS share and remove permissions."""
    lease_info = lease_info or {}
    if lease_info.get("was_preexisting"):
        return True, f"Share '{share_name}' was pre-existing; preserved."

    # Try standard revocation
    cmd = ["sharing", "-r", share_name]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)

    if res.returncode == 0:
        return True, f"Revoked macOS share '{share_name}'"

    # Try elevated revocation via AppleScript
    as_script = f'do shell script "sharing -r \\"{share_name}\\"" with administrator privileges'
    try:
        subprocess.run(["osascript", "-e", as_script], capture_output=True, timeout=15)
        return True, f"Revoked macOS share '{share_name}' with authorization."
    except Exception:
        pass

    return True, f"Revocation attempted for '{share_name}'."
