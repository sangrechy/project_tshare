"""
T-Share v3 Standalone Connection Checker & Network Diagnostic Tool
Tests communication between Sender and Receiver over Wi-Fi and direct Ethernet cable.
Inspects adapter link status, IP configurations, route tables, and firewall accessibility.

Usage:
  python diag_tool.py                     # Auto-detect peers and run full bidirectional diagnostic
  python diag_tool.py --target <ip>       # Connect directly to target IP (Wi-Fi or Wire)
  python diag_tool.py --server            # Run diagnostic server in foreground
  python diag_tool.py --exec "<command>"  # Run remote diagnostic command on target
"""

import sys
import json
import time
import socket
import argparse
import urllib.request
import urllib.error
import concurrent.futures

from backend.diagnostics import (
    DIAG_PORT, get_system_diagnostics, start_diagnostic_service, stop_diagnostic_service
)
from backend.hardware_info import get_detailed_adapters


def scan_for_diag_peers(timeout: float = 1.5):
    """Scans local subnets for active T-Share diagnostic servers on port 52005."""
    _, wifi_list, bcasts = get_detailed_adapters()
    candidate_ips = set(["127.0.0.1", "192.168.123.1", "192.168.123.2", "192.168.1.1", "192.168.1.2"])

    # Expand subnets from active interfaces
    for bcast in bcasts:
        parts = bcast.split(".")
        if len(parts) == 4 and parts[3] == "255":
            prefix = f"{parts[0]}.{parts[1]}.{parts[2]}."
            for i in range(1, 255):
                candidate_ips.add(f"{prefix}{i}")

    discovered = []

    def check_ip(ip):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.3)
            res = s.connect_ex((ip, DIAG_PORT))
            s.close()
            if res == 0:
                # Confirm it's T-Share diagnostic endpoint
                req = urllib.request.Request(f"http://{ip}:{DIAG_PORT}/api/status")
                with urllib.request.urlopen(req, timeout=1.0) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode('utf-8'))
                        return ip, data
        except Exception:
            pass
        return None

    print(f"[*] Scanning {len(candidate_ips)} candidates for active T-Share Diagnostic agents (port {DIAG_PORT})...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=80) as ex:
        futures = [ex.submit(check_ip, ip) for ip in candidate_ips]
        for f in concurrent.futures.as_completed(futures):
            res = f.result()
            if res:
                discovered.append(res)

    return discovered


def run_remote_exec(target_ip: str, cmd: str):
    """Executes a diagnostic command on remote machine via HTTP API."""
    url = f"http://target_ip:{DIAG_PORT}/api/exec".replace("target_ip", target_ip)
    payload = json.dumps({"cmd": cmd}).encode('utf-8')
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=12.0) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            print(f"\n--- Output of '{cmd}' on {target_ip} (Exit Code: {data.get('returncode')}) ---")
            if data.get("stdout"):
                print(data["stdout"])
            if data.get("stderr"):
                print("[stderr]:", data["stderr"])
            return data
    except Exception as e:
        print(f"[!] Failed to execute remote command on {target_ip}: {e}")
        return None


def run_full_diagnostic(target_ip: Optional[str] = None):
    print("=" * 66)
    print("  T-Share v3: High-Speed Direct Wire Connection Diagnostic Checker")
    print("=" * 66)

    # 1. Start local diagnostic service so the other peer can query us
    start_diagnostic_service()
    time.sleep(0.1)

    local_diag = get_system_diagnostics()
    print(f"\n[+] Local Node: {local_diag['hostname']} ({local_diag['platform']})")
    for iface in local_diag.get("interfaces", []):
        ips = [x.get("ip") for x in iface.get("ipv4", [])]
        ip_str = ", ".join(ips) if ips else "No IPv4"
        print(f"    - {iface['name']} [{iface['type'].upper()}]: {ip_str} (Carrier: {'UP' if iface['is_up'] else 'DOWN'}, Speed: {iface['speed_mbps']}M, MAC: {iface['mac']})")

    # 2. Locate remote node
    remote_data = None
    remote_ip = target_ip

    if not remote_ip:
        discovered = scan_for_diag_peers()
        # Filter out self
        external_peers = [p for p in discovered if p[1].get("hostname") != local_diag["hostname"]]
        if external_peers:
            remote_ip, remote_data = external_peers[0]
            print(f"\n[+] Found Remote Peer via Auto-Scan: {remote_data.get('hostname')} @ {remote_ip}")
        else:
            print("\n[-] No remote peers responded to auto-scan.")
            print("[*] Trying standard fallback target 192.168.123.2...")
            remote_ip = "192.168.123.2"

    if remote_ip and not remote_data:
        try:
            req = urllib.request.Request(f"http://{remote_ip}:{DIAG_PORT}/api/status")
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                remote_data = json.loads(resp.read().decode('utf-8'))
                print(f"\n[+] Connected to Remote Node: {remote_data.get('hostname')} ({remote_data.get('platform')}) @ {remote_ip}")
        except Exception as e:
            print(f"[-] Could not connect to Diagnostic Agent on {remote_ip}:{DIAG_PORT} ({e})")

    if remote_data:
        print("\n--- Remote Node Interfaces ---")
        for iface in remote_data.get("interfaces", []):
            ips = [x.get("ip") for x in iface.get("ipv4", [])]
            ip_str = ", ".join(ips) if ips else "No IPv4"
            print(f"    - {iface['name']} [{iface['type'].upper()}]: {ip_str} (Carrier: {'UP' if iface['is_up'] else 'DOWN'}, Speed: {iface['speed_mbps']}M, MAC: {iface['mac']})")

        print(f"\n--- Remote Receiver Status ---")
        print(f"    - T-Share Receiver (Port 52001) Listening: {'YES [OK]' if remote_data.get('receiver_listening') else 'NO [NOT RUNNING]'}")
        if remote_data.get("firewall"):
            print(f"    - Firewall Info:\n      " + "\n      ".join(remote_data['firewall'].splitlines()[:6]))

        # 3. Run Bidirectional Link Tests
        print("\n" + "=" * 66)
        print("  BIDIRECTIONAL LINK & ROUTE TESTS")
        print("=" * 66)

        # Test A: Direct Wire Ping from Local to Remote (192.168.123.2)
        wire_target = "192.168.123.2"
        print(f"\n[TEST 1] Local -> Remote Wire Ping ({wire_target})...")
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1.5)
        res = s.connect_ex((wire_target, 52001))
        s.close()
        if res == 0:
            print(f"    -> [SUCCESS] Direct wire TCP port 52001 is REACHABLE! (code: {res})")
        else:
            print(f"    -> [FAILED] Direct wire TCP port 52001 unreachable (code: {res}).")

        # Test B: Ask Remote node to ping Local wire IP (192.168.123.1)
        print(f"\n[TEST 2] Remote -> Local Wire Ping (asking {remote_data['hostname']} to ping 192.168.123.1)...")
        try:
            req = urllib.request.Request(
                f"http://{remote_ip}:{DIAG_PORT}/api/ping",
                data=json.dumps({"target": "192.168.123.1", "count": 2}).encode('utf-8'),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=4.0) as resp:
                pdata = json.loads(resp.read().decode('utf-8'))
                if pdata.get("success"):
                    print(f"    -> [SUCCESS] Remote machine successfully pinged 192.168.123.1!")
                else:
                    print(f"    -> [FAILED] Remote machine could not ping 192.168.123.1:")
                    print(f"       {pdata.get('output', pdata.get('error'))}")
        except Exception as e:
            print(f"    -> [FAILED] Could not run remote ping: {e}")

        # Test C: Ask Remote node to check TCP back to Local node
        print(f"\n[TEST 3] Remote -> Local Receiver Check (Port 52001)...")
        try:
            req = urllib.request.Request(
                f"http://{remote_ip}:{DIAG_PORT}/api/check_tcp",
                data=json.dumps({"host": "192.168.123.1", "port": 52001, "timeout": 2.0}).encode('utf-8'),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                tdata = json.loads(resp.read().decode('utf-8'))
                if tdata.get("open"):
                    print(f"    -> [SUCCESS] Remote machine connected to Local 52001 (Latency: {tdata.get('latency_ms')} ms)!")
                else:
                    print(f"    -> [INFO] Local port 52001 not open from remote (Local is Sender, so this is normal).")
        except Exception as e:
            print(f"    -> [INFO] {e}")

    print("\n" + "=" * 66)
    print("  DIAGNOSTIC SUMMARY & RECOMMENDATIONS")
    print("=" * 66)

    # Check local Ethernet IP
    local_eth = [i for i in local_diag.get("interfaces", []) if i["type"] == "ethernet"]
    has_123_1 = False
    for eth in local_eth:
        for ip_obj in eth.get("ipv4", []):
            if ip_obj.get("ip") == "192.168.123.1":
                has_123_1 = True

    if not has_123_1:
        print("[!] ACTION NEEDED ON WINDOWS:")
        print("    Your local Ethernet adapter does NOT have IP 192.168.123.1.")
        print("    -> Run 'set_ethernet_ip.bat' as Administrator on Windows.")
        print("    -> Or click 'Auto-Setup / Align Wire IP' in the T-Share UI.\n")
    else:
        print("[OK] Windows Ethernet adapter has 192.168.123.1 configured.\n")

    if remote_data:
        rem_eth = [i for i in remote_data.get("interfaces", []) if i["type"] == "ethernet"]
        has_123_2 = False
        for eth in rem_eth:
            for ip_obj in eth.get("ipv4", []):
                if ip_obj.get("ip") == "192.168.123.2":
                    has_123_2 = True

        if not has_123_2:
            print("[!] ACTION NEEDED ON FEDORA:")
            print("    Fedora's Ethernet adapter does NOT have IP 192.168.123.2.")
            print("    -> In T-Share UI on Fedora, click 'Auto-Setup' and enter sudo password.")
            print("    -> Or run: sudo ip addr add 192.168.123.2/24 dev <eth_name>\n")
        else:
            print("[OK] Fedora Ethernet adapter has 192.168.123.2 configured.\n")


def main():
    parser = argparse.ArgumentParser(description="T-Share v3 Connection Checker & Diagnostic Tool")
    parser.add_argument("--server", action="store_true", help="Run diagnostic HTTP server in foreground")
    parser.add_argument("--target", type=str, help="Target peer IP address")
    parser.add_argument("--exec", type=str, help="Run remote diagnostic command on target")
    args = parser.parse_args()

    if args.server:
        print(f"[*] Starting T-Share Diagnostic Agent on 0.0.0.0:{DIAG_PORT}...")
        start_diagnostic_service()
        print("[*] Diagnostic Agent is running. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            stop_diagnostic_service()
            print("\n[*] Stopped.")
            sys.exit(0)

    if args.exec:
        target = args.target or "192.168.123.2"
        run_remote_exec(target, args.exec)
        sys.exit(0)

    run_full_diagnostic(target_ip=args.target)


if __name__ == "__main__":
    main()
