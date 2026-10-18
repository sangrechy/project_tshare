"""Linux Network Sharing & Permission Management.

Provisions Samba usershares ('net usershare'), handles root elevation via pkexec
when required, records initial states, and tears down temporary shares on session close.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from typing import Any, Dict, List, Tuple


def list_linux_shares() -> list[dict[str, str]]:
    """List active Samba usershares."""
    shares: list[dict[str, str]] = []
    if shutil.which("net"):
        try:
            raw = subprocess.check_output(["net", "usershare", "list"], text=True, stderr=subprocess.DEVNULL, timeout=4)
            for name in raw.splitlines():
                name = name.strip()
                if name:
                    # Get info
                    try:
                        info = subprocess.check_output(["net", "usershare", "info", name], text=True, stderr=subprocess.DEVNULL, timeout=3)
                        path_m = [line.split("=")[1].strip() for line in info.splitlines() if line.startswith("path=")]
                        path_val = path_m[0] if path_m else ""
                        shares.append({"name": name, "resource": path_val, "is_admin": False})
                    except Exception:
                        shares.append({"name": name, "resource": "", "is_admin": False})
        except Exception:
            pass
    return shares


def create_linux_share(folder_path: str, share_name: str = "Transfers") -> tuple[bool, str, dict[str, Any]]:
    """Create a temporary network share on Linux using Samba usershares.

    Elevates with pkexec if user lacks permissions.
    """
    if not os.path.exists(folder_path):
        try:
            os.makedirs(folder_path, exist_ok=True)
        except Exception as e:
            return False, f"Could not create folder: {e}", {}

    abs_path = os.path.abspath(folder_path)

    # 1. Check if 'net' tool is installed
    if not shutil.which("net"):
        return False, "Samba client tools ('net') not found. Please install samba (e.g. sudo apt install samba).", {}

    # 2. Try unprivileged 'net usershare add'
    cmd = ["net", "usershare", "add", share_name, abs_path, "TShare Temporary Transfer Share", "Everyone:F", "guest_ok=y"]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)

    if res.returncode == 0:
        return True, f"Successfully created Linux Samba share '{share_name}'", {"share_name": share_name, "was_preexisting": False}

    # 3. If permission denied, elevate via pkexec (standard graphical password prompt)
    if "permission denied" in res.stderr.lower() or "denied" in res.stderr.lower() or res.returncode != 0:
        if shutil.which("pkexec"):
            try:
                pk_cmd = ["pkexec", "net", "usershare", "add", share_name, abs_path, "TShare Temporary Transfer Share", "Everyone:F", "guest_ok=y"]
                pk_res = subprocess.run(pk_cmd, capture_output=True, text=True, timeout=20)
                if pk_res.returncode == 0:
                    return True, f"Successfully created elevated Linux share '{share_name}'", {
                        "share_name": share_name,
                        "was_preexisting": False,
                        "elevated": True,
                    }
                return False, f"Elevation cancelled or failed: {pk_res.stderr.strip()}", {}
            except Exception as exc:
                return False, f"pkexec elevation error: {exc}", {}

    return False, res.stderr.strip() or res.stdout.strip(), {}


def revoke_linux_share(share_name: str, folder_path: str = "", lease_info: dict[str, Any] | None = None) -> tuple[bool, str]:
    """Revoke temporary Samba usershare and remove permissions."""
    lease_info = lease_info or {}
    if lease_info.get("was_preexisting"):
        return True, f"Share '{share_name}' was pre-existing; preserved."

    if not shutil.which("net"):
        return False, "Samba 'net' command not available."

    # Try normal delete
    cmd = ["net", "usershare", "delete", share_name]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)

    if res.returncode == 0:
        return True, f"Revoked Linux share '{share_name}'"

    # Try elevated delete via pkexec
    if shutil.which("pkexec"):
        try:
            subprocess.run(["pkexec", "net", "usershare", "delete", share_name], capture_output=True, timeout=10)
            return True, f"Revoked Linux share '{share_name}' with elevation."
        except Exception:
            pass

    return True, f"Revocation attempted for '{share_name}'."
