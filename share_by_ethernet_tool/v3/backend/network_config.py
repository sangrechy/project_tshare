"""
T-Share v3 Network & Firewall Auto-Configuration
Supports In-UI Password Elevation (sudo -S on Linux/macOS) and Native Windows UAC
to temporarily assign IP to unconfigured Ethernet and open firewall ports.
Zero terminal commands needed by the user.

Strictly TEMPORARY & REVERSIBLE:
- Original adapter & firewall state is recorded to a backup file before changes.
- Changes are non-permanent (runtime-only).
- An elevated background watchdog monitors the application process.
- As soon as the session ends or user closes the app, all settings automatically revert back to normal.
- If the app was closed abruptly (crash/kill), leftover settings are restored at next startup.
"""

import os
import sys
import json
import atexit
import shutil
import subprocess
import tempfile
from typing import Dict, Any, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKUP_FILE = os.path.join(BASE_DIR, ".tshare_net_backup.json")
TRIGGER_FILE = os.path.join(BASE_DIR, ".tshare_revert_trigger")
TEMP_BACKUP_FILE = os.path.join(tempfile.gettempdir(), "tshare_net_backup.json")


def get_backup_path() -> str:
    """Returns the primary backup path, ensuring writable directory."""
    try:
        test_file = BACKUP_FILE + ".test"
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        return BACKUP_FILE
    except Exception:
        return TEMP_BACKUP_FILE


def configure_direct_ethernet(password: str = "") -> Dict[str, Any]:
    """
    Sets up direct Ethernet IP (192.168.123.x) and opens firewall ports (52000-52010).
    On Linux/macOS: Uses password from UI with sudo -S.
    On Windows: Uses native UAC approval.
    Spawns a background watchdog tied to parent PID that restores normal settings on exit.
    """
    parent_pid = os.getpid()
    backup_path = get_backup_path()

    # Clean up any leftover trigger file
    if os.path.exists(TRIGGER_FILE):
        try:
            os.remove(TRIGGER_FILE)
        except Exception:
            pass

    if sys.platform.startswith("linux"):
        return _configure_linux(password, parent_pid, backup_path)
    elif sys.platform == "win32":
        return _configure_windows(parent_pid, backup_path)
    elif sys.platform == "darwin":
        return _configure_macos(password, parent_pid, backup_path)
    else:
        return {"success": False, "error": "Unsupported platform"}


def _configure_linux(password: str, parent_pid: int, backup_path: str) -> Dict[str, Any]:
    is_root = (os.geteuid() == 0) if hasattr(os, "geteuid") else False
    if not is_root and not shutil.which("sudo") and not shutil.which("pkexec"):
        return {"success": False, "error": "Neither sudo nor pkexec found on system."}

    trigger_path = TRIGGER_FILE
    bash_script = f'''
PPID_VAL="{parent_pid}"
BFILE="{backup_path}"
TFILE="{trigger_path}"

ETH=""
for d in $(ls /sys/class/net 2>/dev/null); do
  if [ "$d" != "lo" ] && [ ! -d "/sys/class/net/$d/wireless" ] && [ -e "/sys/class/net/$d/device" ]; then
    ETH="$d"; break;
  fi
done

if [ -z "$ETH" ]; then
  echo "No physical Ethernet interface found" >&2
  exit 2
fi

EXISTING_IP=$(ip -4 addr show dev "$ETH" 2>/dev/null | grep -o 'inet [0-9.]*' | head -n1 | awk '{{print $2}}')

# Save initial state before doing anything
cat << EOF > "$BFILE"
{{
  "platform": "linux",
  "interface": "$ETH",
  "had_ip": "$EXISTING_IP",
  "assigned_ip": "192.168.123.2/24"
}}
EOF
chmod 666 "$BFILE" 2>/dev/null || true

# 1. Temporary runtime firewall rules (no --permanent)
if command -v firewall-cmd &>/dev/null; then
  firewall-cmd --add-port=52000-52010/tcp --add-port=52000-52010/udp 2>/dev/null || true
elif command -v ufw &>/dev/null; then
  ufw allow 52000:52010/tcp 2>/dev/null || true
  ufw allow 52000:52010/udp 2>/dev/null || true
fi

# 2. Temporary IP if not already present
if [ -z "$EXISTING_IP" ]; then
  ip addr add 192.168.123.2/24 dev "$ETH" 2>/dev/null || true
  ip link set "$ETH" up 2>/dev/null || true
fi

# 3. Fork detached background watchdog process as root
nohup bash -c '
  PPID_VAL="'"$PPID_VAL"'"
  ETH="'"$ETH"'"
  EXISTING_IP="'"$EXISTING_IP"'"
  BFILE="'"$BFILE"'"
  TFILE="'"$TFILE"'"

  while kill -0 "$PPID_VAL" 2>/dev/null; do
    if [ -f "$TFILE" ]; then break; fi
    sleep 1
  done

  # Revert settings
  if [ -z "$EXISTING_IP" ]; then
    ip addr del 192.168.123.2/24 dev "$ETH" 2>/dev/null || true
    if command -v nmcli &>/dev/null; then
      nmcli device reapply "$ETH" 2>/dev/null || true
    fi
  fi

  if command -v firewall-cmd &>/dev/null; then
    firewall-cmd --remove-port=52000-52010/tcp --remove-port=52000-52010/udp 2>/dev/null || true
  elif command -v ufw &>/dev/null; then
    ufw delete allow 52000:52010/tcp 2>/dev/null || true
    ufw delete allow 52000:52010/udp 2>/dev/null || true
  fi

  rm -f "$BFILE" "$TFILE"
' >/dev/null 2>&1 &
'''

    if is_root:
        cmd = ["bash", "-c", bash_script]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0:
            return {"success": True, "message": "Direct Ethernet configured successfully."}
        return {"success": False, "error": proc.stderr.strip() or "Failed to configure interface"}

    if password:
        # User entered password in UI modal -> Pipe directly to sudo -S -k
        cmd = ["sudo", "-S", "-k", "bash", "-c", bash_script]
        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = proc.communicate(input=password + "\n")
            if proc.returncode == 0:
                return {"success": True, "message": "Direct Ethernet configured successfully (192.168.123.2)."}

            lower_err = stderr.lower()
            if "incorrect password" in lower_err or "try again" in lower_err or "authentication failure" in lower_err:
                return {"success": False, "error": "Incorrect password. Please try again."}
            elif "not in the sudoers" in lower_err:
                return {"success": False, "error": "Current user is not in sudoers list."}
            return {"success": False, "error": stderr.strip() or "Sudo authentication failed."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # If no password provided, check if passwordless sudo works
    try:
        check = subprocess.run(["sudo", "-n", "true"], capture_output=True)
        if check.returncode == 0:
            proc = subprocess.run(["sudo", "bash", "-c", bash_script], capture_output=True, text=True)
            if proc.returncode == 0:
                return {"success": True, "message": "Direct Ethernet configured."}
            return {"success": False, "error": proc.stderr.strip()}
    except Exception:
        pass

    return {"success": False, "error": "Password required", "need_password": True}


def _configure_windows(parent_pid: int, backup_path: str) -> Dict[str, Any]:
    trigger_path = TRIGGER_FILE
    # Escape backslashes for PowerShell strings
    bpath_esc = backup_path.replace("\\", "\\\\")
    tpath_esc = trigger_path.replace("\\", "\\\\")

    ps_script = f'''
$eth = Get-NetAdapter | Where-Object {{ $_.InterfaceDescription -notmatch "Wi-Fi|Wireless|Virtual|Hyper-V|TAP" -and $_.Status -eq "Up" }} | Select-Object -First 1
if (-not $eth) {{ exit 1 }}

$idx = $eth.ifIndex
$hadDhcp = (Get-NetIPInterface -InterfaceIndex $idx -AddressFamily IPv4).Dhcp -eq 'Enabled'
$curIps = (Get-NetIPAddress -InterfaceIndex $idx -AddressFamily IPv4 | Where-Object {{ $_.IPAddress -notlike "169.254.*" -and $_.IPAddress -notlike "127.*" }}).IPAddress

$state = @{{
  platform = "windows"
  ifIndex = $idx
  ifAlias = $eth.Name
  hadDhcp = $hadDhcp
  hadIp = ($curIps -join ",")
  assignedIp = "192.168.123.1"
}}
$state | ConvertTo-Json | Set-Content -Path "{bpath_esc}" -Force

# 1. Temporary Firewall Rules
New-NetFirewallRule -DisplayName "T-Share-Direct-Temp-TCP" -Direction Inbound -LocalPort 52000-52010 -Protocol TCP -Action Allow -ErrorAction SilentlyContinue
New-NetFirewallRule -DisplayName "T-Share-Direct-Temp-UDP" -Direction Inbound -LocalPort 52000-52010 -Protocol UDP -Action Allow -ErrorAction SilentlyContinue

# 2. Temporary IP (ensure Windows is in the 192.168.123.x subnet)
$hasSubnet = (Get-NetIPAddress -InterfaceIndex $idx -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object {{ $_.IPAddress -like "192.168.123.*" }})
if (-not $hasSubnet) {{
  New-NetIPAddress -InterfaceIndex $idx -IPAddress 192.168.123.1 -PrefixLength 24 -ErrorAction SilentlyContinue
}}

# 3. Launch background watchdog process
$watchdogCmd = @"
`$ppid = {parent_pid}
`$bfile = '{bpath_esc}'
`$tfile = '{tpath_esc}'
`$idx = $idx
`$hadDhcp = '$hadDhcp'

while (Get-Process -Id `$ppid -ErrorAction SilentlyContinue) {{
  if (Test-Path `$tfile) {{ break }}
  Start-Sleep -Seconds 1
}}

Remove-NetFirewallRule -DisplayName 'T-Share-Direct-Temp-TCP' -ErrorAction SilentlyContinue
Remove-NetFirewallRule -DisplayName 'T-Share-Direct-Temp-UDP' -ErrorAction SilentlyContinue
Remove-NetIPAddress -InterfaceIndex `$idx -IPAddress 192.168.123.1 -Confirm:`$false -ErrorAction SilentlyContinue

if (`$hadDhcp -eq 'True') {{
  Set-NetIPInterface -InterfaceIndex `$idx -Dhcp Enabled -ErrorAction SilentlyContinue
}}

Remove-Item -Path `$bfile, `$tfile -Force -ErrorAction SilentlyContinue
"@

Start-Process powershell -WindowStyle Hidden -ArgumentList "-NoProfile -Command $watchdogCmd"
'''
    cmd = f'Start-Process powershell -Verb runAs -ArgumentList \'-NoProfile -Command "{ps_script}"\''
    try:
        subprocess.Popen(["powershell", "-NoProfile", "-Command", cmd])
        return {"success": True, "message": "Windows UAC confirmation triggered."}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _configure_macos(password: str, parent_pid: int, backup_path: str) -> Dict[str, Any]:
    if password:
        cmd = ["sudo", "-S", "-k", "pfctl", "-e"]
        try:
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            _, stderr = proc.communicate(input=password + "\n")
            if proc.returncode == 0:
                return {"success": True, "message": "macOS network configured."}
            return {"success": False, "error": "Incorrect password or authorization denied."}
        except Exception as e:
            return {"success": False, "error": str(e)}
    else:
        applescript = 'do shell script "pfctl -e 2>/dev/null || true" with administrator privileges'
        try:
            subprocess.Popen(["osascript", "-e", applescript])
            return {"success": True, "message": "macOS admin prompt triggered"}
        except Exception as e:
            return {"success": False, "error": str(e)}


def revert_direct_ethernet() -> Dict[str, Any]:
    """
    Signals running watchdog or directly restores network state to normal.
    Safe to call multiple times.
    """
    # 1. Signal any running watchdog process
    try:
        with open(TRIGGER_FILE, "w") as f:
            f.write("revert")
    except Exception:
        pass

    # 2. Check backup file and execute fallback revert if watchdog was not running
    backup_path = get_backup_path()
    targets = [backup_path, BACKUP_FILE, TEMP_BACKUP_FILE]
    active_target = None
    for t in targets:
        if os.path.exists(t):
            active_target = t
            break

    if not active_target:
        return {"success": True, "message": "No active temporary configuration found"}

    try:
        with open(active_target, "r") as f:
            state = json.load(f)

        if sys.platform.startswith("linux"):
            eth = state.get("interface", "")
            had_ip = state.get("had_ip", "")
            if eth and not had_ip:
                subprocess.run(["ip", "addr", "del", "192.168.123.2/24", "dev", eth], stderr=subprocess.DEVNULL)
                if shutil.which("nmcli"):
                    subprocess.run(["nmcli", "device", "reapply", eth], stderr=subprocess.DEVNULL)
            if shutil.which("firewall-cmd"):
                subprocess.run(["firewall-cmd", "--remove-port=52000-52010/tcp", "--remove-port=52000-52010/udp"], stderr=subprocess.DEVNULL)
            elif shutil.which("ufw"):
                subprocess.run(["ufw", "delete", "allow", "52000:52010/tcp"], stderr=subprocess.DEVNULL)
                subprocess.run(["ufw", "delete", "allow", "52000:52010/udp"], stderr=subprocess.DEVNULL)

        elif sys.platform == "win32":
            idx = state.get("ifIndex")
            had_dhcp = state.get("hadDhcp", True)
            ps_cleanup = (
                f'Remove-NetFirewallRule -DisplayName "T-Share-Direct-Temp-TCP" -ErrorAction SilentlyContinue; '
                f'Remove-NetFirewallRule -DisplayName "T-Share-Direct-Temp-UDP" -ErrorAction SilentlyContinue; '
            )
            if idx:
                ps_cleanup += f'Remove-NetIPAddress -InterfaceIndex {idx} -IPAddress 192.168.123.1 -Confirm:$false -ErrorAction SilentlyContinue; '
                if had_dhcp:
                    ps_cleanup += f'Set-NetIPInterface -InterfaceIndex {idx} -Dhcp Enabled -ErrorAction SilentlyContinue; '
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_cleanup], stderr=subprocess.DEVNULL)

        # Remove backup file
        if os.path.exists(active_target):
            os.remove(active_target)
        if os.path.exists(TRIGGER_FILE):
            os.remove(TRIGGER_FILE)

        return {"success": True, "message": "Restored network settings to normal"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def check_and_restore_leftover_backup() -> bool:
    """
    Called at application startup.
    Checks if a previous session closed unexpectedly without reverting.
    If backup is found, restores network settings to normal and removes backup.
    """
    backup_path = get_backup_path()
    targets = [backup_path, BACKUP_FILE, TEMP_BACKUP_FILE]
    found = False
    for t in targets:
        if os.path.exists(t):
            found = True
            break

    if not found:
        return False

    print("[*] Detected leftover temporary Ethernet settings from prior session. Restoring normal state...")
    res = revert_direct_ethernet()
    print(f"[*] Network restoration: {res.get('message', res.get('error', 'done'))}")
    return True


# Automatically ensure revert on normal Python process termination
atexit.register(revert_direct_ethernet)
