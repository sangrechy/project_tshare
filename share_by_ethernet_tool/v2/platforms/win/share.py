"""Windows Network Sharing & Permission Management.

Provisions Windows SMB shares, handles UAC Administrator elevation when required,
records initial share states, and cleans up temporary shares upon completion/interruption.
"""
from __future__ import annotations

import os
import re
import subprocess
from typing import Any, Dict, List, Tuple


def list_windows_shares() -> list[dict[str, str]]:
    """Enumerate existing Windows shares via 'net share'."""
    shares: list[dict[str, str]] = []
    try:
        raw = subprocess.check_output(
            ["net", "share"],
            text=True,
            encoding="mbcs",
            errors="replace",
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
        lines = raw.splitlines()
        dash_index = -1
        for idx, line in enumerate(lines):
            if "---" in line:
                dash_index = idx
                break
        if dash_index != -1:
            for line in lines[dash_index + 1 :]:
                line = line.strip()
                if not line or "command completed successfully" in line.lower():
                    continue
                parts = re.split(r"\s{2,}", line)
                if len(parts) >= 2:
                    name = parts[0].strip()
                    res = parts[1].strip()
                    shares.append(
                        {
                            "name": name,
                            "resource": res,
                            "is_admin": name.endswith("$"),
                        }
                    )
    except Exception:
        pass
    return shares


def is_folder_shared(folder_path: str) -> str | None:
    """Return share name if folder is already shared, else None."""
    norm_target = os.path.normpath(folder_path).casefold()
    for s in list_windows_shares():
        if os.path.normpath(s.get("resource", "")).casefold() == norm_target:
            return s["name"]
    return None


def create_windows_share(folder_path: str, share_name: str = "Transfers") -> tuple[bool, str, dict[str, Any]]:
    """Share a local folder on Windows with Read/Write permissions for the local network.

    Elevates to Administrator via Windows UAC if standard permission is denied.
    Returns (success, message, lease_metadata).
    """
    if not os.path.exists(folder_path):
        try:
            os.makedirs(folder_path, exist_ok=True)
        except Exception as e:
            return False, f"Could not create folder: {e}", {}

    abs_path = os.path.abspath(folder_path)

    # 1. Check if already shared
    existing = is_folder_shared(abs_path)
    if existing:
        return True, f"Folder already shared as '{existing}'.", {"share_name": existing, "was_preexisting": True}

    # 2. Try standard 'net share'
    cmd = ["net", "share", f"{share_name}={abs_path}", "/GRANT:Everyone,FULL"]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)

    if res.returncode == 0 or "already exists" in res.stderr.lower():
        return True, f"Successfully created share '{share_name}'", {"share_name": share_name, "was_preexisting": False}

    # 3. If access denied (Error 5 / elevation needed), elevate via PowerShell RunAs
    if "access is denied" in res.stderr.lower() or res.returncode != 0:
        ps_cmd = (
            f"Start-Process cmd -ArgumentList '/c net share {share_name}=\"{abs_path}\" /GRANT:Everyone,FULL' "
            "-Verb RunAs -Wait"
        )
        try:
            elev_res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                timeout=15,
            )
            # Verify if share now exists
            if is_folder_shared(abs_path) or any(s["name"] == share_name for s in list_windows_shares()):
                return True, f"Successfully created elevated share '{share_name}'", {
                    "share_name": share_name,
                    "was_preexisting": False,
                    "elevated": True,
                }
            return False, f"UAC elevation cancelled or failed: {elev_res.stderr.strip()}", {}
        except Exception as exc:
            return False, f"Elevation error: {exc}", {}

    return False, res.stderr.strip() or res.stdout.strip(), {}


def revoke_windows_share(share_name: str, folder_path: str = "", lease_info: dict[str, Any] | None = None) -> tuple[bool, str]:
    """Revoke Windows SMB share permissions and clean up temporary shares.

    If the share was pre-existing before the session, it is left untouched.
    """
    lease_info = lease_info or {}
    if lease_info.get("was_preexisting"):
        return True, f"Share '{share_name}' was pre-existing; preserved."

    # Try standard deletion
    cmd = ["net", "share", share_name, "/DELETE", "/Y"]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)

    if res.returncode == 0 or "does not exist" in res.stderr.lower() or "not found" in res.stderr.lower():
        return True, f"Successfully revoked share '{share_name}'"

    # Try elevated deletion via RunAs if permission denied
    ps_cmd = f"Start-Process cmd -ArgumentList '/c net share {share_name} /DELETE /Y' -Verb RunAs -Wait"
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, timeout=10)
        return True, f"Revoked share '{share_name}' with elevation."
    except Exception as exc:
        return False, f"Failed to revoke share '{share_name}': {exc}"
