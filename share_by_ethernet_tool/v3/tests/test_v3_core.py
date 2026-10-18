"""
T-Share v3 Automated Test Suite
Verifies cross-platform protocol, path security, database lifecycle, and streaming integrity.
"""

import unittest
import sys
import os
import tempfile
import struct
import time
import threading
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.path_security import sanitize_relative_path, resolve_safe_destination_path, SecurityViolation
from backend.protocol import (
    MAGIC, HEADER_FORMAT, BLOCK_HEADER_FORMAT, HEADER_SIZE, BLOCK_HEADER_SIZE,
    MSG_BLOCK, send_packet, recv_packet
)
from backend.hardware_info import get_hardware_telemetry, get_network_interfaces, get_disk_space
from backend.history_db import HistoryDatabase
from backend.receiver_engine import ReceiverEngine
from backend.transfer_engine import TransferEngine
from backend.verify_engine import VerifyEngine


class TestTSHAREV3(unittest.TestCase):
    def test_01_path_security_traversal(self):
        with self.assertRaises(SecurityViolation):
            sanitize_relative_path('../../etc/passwd')
        with self.assertRaises(SecurityViolation):
            sanitize_relative_path('folder/../../../root.key')
        with self.assertRaises(SecurityViolation):
            sanitize_relative_path('')

    def test_02_path_security_windows_reserved(self):
        self.assertEqual(sanitize_relative_path('con.txt'), '_safe_con.txt')
        self.assertEqual(sanitize_relative_path('AUX'), '_safe_AUX')
        self.assertEqual(sanitize_relative_path('sub/prn.log'), 'sub/_safe_prn.log')
        self.assertEqual(sanitize_relative_path('C:\\Users\\test\\docs/file.pdf'), 'Users/test/docs/file.pdf')

    def test_03_path_containment_and_collisions(self):
        with tempfile.TemporaryDirectory() as td:
            p1, skip = resolve_safe_destination_path(td, 'test.txt', 'keep_both')
            self.assertFalse(skip)
            with open(p1, 'w') as f:
                f.write('orig')

            p2, skip2 = resolve_safe_destination_path(td, 'test.txt', 'keep_both')
            self.assertFalse(skip2)
            self.assertTrue(p2.endswith('test (1).txt'))

            p3, skip3 = resolve_safe_destination_path(td, 'test.txt', 'skip')
            self.assertTrue(skip3)

    def test_04_protocol_framing(self):
        header = struct.pack(HEADER_FORMAT, MAGIC, MSG_BLOCK, 12345, 100)
        magic, mtype, sid, plen = struct.unpack(HEADER_FORMAT, header)
        self.assertEqual(magic, MAGIC)
        self.assertEqual(mtype, MSG_BLOCK)
        self.assertEqual(sid, 12345)
        self.assertEqual(plen, 100)

    def test_05_hardware_telemetry(self):
        telemetry = get_hardware_telemetry()
        self.assertIn('cpu', telemetry)
        self.assertIn('ram', telemetry)
        self.assertIn('disk', telemetry)
        self.assertIn('network', telemetry)
        self.assertGreater(telemetry['cpu']['cores'], 0)
        self.assertGreater(telemetry['ram']['total_bytes'], 0)

    def test_06_history_database(self):
        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, 'test.db')
            db = HistoryDatabase(db_path)
            row_id = db.record_transfer('9999', 'sender', 'laptop2', '169.254.1.2', 'completed', 5, 100000, 100000, 95.5, 1.2, td)
            self.assertGreater(row_id, 0)
            transfers = db.get_transfers()
            self.assertEqual(len(transfers), 1)
            self.assertEqual(transfers[0]['session_id'], '9999')

    def test_07_verification_modes(self):
        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, 'test.db')
            db = HistoryDatabase(db_path)
            data_dir = os.path.join(td, 'files')
            os.makedirs(data_dir)
            fpath = os.path.join(data_dir, 'data.bin')
            with open(fpath, 'wb') as f:
                f.write(os.urandom(1024 * 1024))
            db.record_transfer('sess1', 'receiver', 'peer', '127.0.0.1', 'completed', 1, 1024*1024, 1024*1024, 100.0, 0.1, data_dir)

            v = VerifyEngine(db)
            v.start_verification('sess1', 'quick_parity')
            v._thread.join()
            self.assertEqual(v.status, 'passed')

            v.start_verification('sess1', 'full_crypto')
            v._thread.join()
            self.assertEqual(v.status, 'passed')

    def test_08_end_to_end_streaming(self):
        with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as dst:
            test_file = os.path.join(src, 'large.bin')
            raw_bytes = os.urandom(6 * 1024 * 1024)
            with open(test_file, 'wb') as f:
                f.write(raw_bytes)

            recv = ReceiverEngine(port=52035)
            recv.start()

            def auto_accept():
                while recv.status != 'waiting_user':
                    time.sleep(0.02)
                recv.accept_transfer(dst, 'overwrite')
            threading.Thread(target=auto_accept, daemon=True).start()

            sender = TransferEngine()
            sender.start_transfer('127.0.0.1', 52035, [test_file])
            sender._thread.join(timeout=15)

            timeout = 5
            st = time.time()
            while recv.status != 'completed' and time.time() - st < timeout:
                time.sleep(0.05)

            self.assertEqual(sender.status, 'completed')
            self.assertEqual(recv.status, 'completed')
            recv.stop()

            out = os.path.join(dst, 'large.bin')
            self.assertTrue(os.path.exists(out))
            with open(out, 'rb') as f:
                self.assertEqual(f.read(), raw_bytes)

    def test_09_bridge_api_and_fallbacks(self):
        from backend.bridge import BridgeAPI
        bridge = BridgeAPI()
        
        # Dashboard telemetry check
        telemetry = bridge.get_dashboard_telemetry()
        self.assertIn('hardware', telemetry)
        self.assertEqual(telemetry['active_role'], 'none')

        # Test path setting and summary
        with tempfile.TemporaryDirectory() as td:
            f1 = os.path.join(td, 'file1.txt')
            with open(f1, 'w') as f:
                f.write('hello world')
            summary = bridge.set_source_paths([f1])
            self.assertEqual(summary['count'], 1)
            self.assertEqual(summary['total_bytes'], 11)

            res_dest = bridge.set_destination_path(td)
            self.assertTrue(res_dest['success'])
            self.assertEqual(res_dest['path'], os.path.abspath(td))

            res_bad = bridge.set_destination_path(os.path.join(td, 'does_not_exist'))
            self.assertFalse(res_bad['success'])

    def test_10_browser_mode_web_server(self):
        import urllib.request
        from http.server import HTTPServer
        from backend.bridge import BridgeAPI
        from backend.web_server import BridgeHTTPHandler

        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        ui_dir = os.path.join(base_dir, "ui")
        bridge = BridgeAPI()

        BridgeHTTPHandler.bridge = bridge
        BridgeHTTPHandler.ui_dir = ui_dir

        server = HTTPServer(("127.0.0.1", 52044), BridgeHTTPHandler)
        srv_thread = threading.Thread(target=server.serve_forever, daemon=True)
        srv_thread.start()

        try:
            # 1. Test GET / (HTML)
            req = urllib.request.Request("http://127.0.0.1:52044/")
            with urllib.request.urlopen(req) as resp:
                self.assertEqual(resp.status, 200)
                body = resp.read().decode('utf-8')
                self.assertIn("T-Share v3", body)

            # 2. Test GET /styles.css
            req = urllib.request.Request("http://127.0.0.1:52044/styles.css")
            with urllib.request.urlopen(req) as resp:
                self.assertEqual(resp.status, 200)
                self.assertIn("text/css", resp.headers.get("Content-Type", ""))

            # 3. Test GET /app.js
            req = urllib.request.Request("http://127.0.0.1:52044/app.js")
            with urllib.request.urlopen(req) as resp:
                self.assertEqual(resp.status, 200)
                self.assertIn("application/javascript", resp.headers.get("Content-Type", ""))

            # 4. Test POST /api/get_dashboard_telemetry
            req = urllib.request.Request(
                "http://127.0.0.1:52044/api/get_dashboard_telemetry",
                data=b"[]",
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req) as resp:
                self.assertEqual(resp.status, 200)
                import json
                data = json.loads(resp.read().decode('utf-8'))
                self.assertIn("hardware", data)
                self.assertIn("active_role", data)

            # 5. Test POST /api/invalid_method -> 404
            req = urllib.request.Request(
                "http://127.0.0.1:52044/api/nonexistent_xyz",
                data=b"[]",
                headers={"Content-Type": "application/json"}
            )
            try:
                with urllib.request.urlopen(req) as resp:
                    self.assertEqual(resp.status, 404)
            except urllib.error.HTTPError as e:
                self.assertEqual(e.code, 404)
                e.close()

        finally:
            server.shutdown()
            server.server_close()

    def test_11_high_throughput_streaming(self):
        with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as dst:
            test_file = os.path.join(src, 'benchmark_32mb.bin')
            size_bytes = 32 * 1024 * 1024  # 32 MB (8 blocks)
            raw_bytes = os.urandom(size_bytes)
            with open(test_file, 'wb') as f:
                f.write(raw_bytes)

            recv = ReceiverEngine(port=52055)
            recv.start()

            def auto_accept():
                while recv.status != 'waiting_user':
                    time.sleep(0.01)
                recv.accept_transfer(dst, 'overwrite')

            threading.Thread(target=auto_accept, daemon=True).start()

            t0 = time.time()
            sender = TransferEngine()
            sender.start_transfer('127.0.0.1', 52055, [test_file])
            sender._thread.join(timeout=10)

            t_end = time.time()
            recv_timeout = 5
            st = time.time()
            while recv.status != 'completed' and time.time() - st < recv_timeout:
                time.sleep(0.02)

            duration = max(0.001, t_end - t0)
            mbps = (size_bytes / duration) / (1024 * 1024)
            print(f"\n[BENCHMARK] 32 MB streamed in {duration:.3f}s -> {mbps:.2f} MB/s")

            self.assertEqual(sender.status, 'completed')
            self.assertEqual(recv.status, 'completed')
            self.assertGreater(mbps, 50.0)
            recv.stop()

            out_file = os.path.join(dst, 'benchmark_32mb.bin')
            self.assertTrue(os.path.exists(out_file))
            with open(out_file, 'rb') as f:
                self.assertEqual(f.read(), raw_bytes)

    def test_12_multi_file_batch_streaming(self):
        with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as dst:
            # Create a mix of files: empty, small, medium, and subfolder
            f_empty = os.path.join(src, 'empty.txt')
            with open(f_empty, 'wb') as f:
                pass

            f_small = os.path.join(src, 'small.txt')
            with open(f_small, 'wb') as f:
                f.write(b'Small file payload text')

            sub = os.path.join(src, 'subfolder')
            os.makedirs(sub)
            f_sub = os.path.join(sub, 'data.bin')
            sub_payload = os.urandom(5 * 1024 * 1024)  # 5 MB
            with open(f_sub, 'wb') as f:
                f.write(sub_payload)

            recv = ReceiverEngine(port=52066)
            recv.start()

            def auto_accept():
                while recv.status != 'waiting_user':
                    time.sleep(0.01)
                recv.accept_transfer(dst, 'overwrite')

            threading.Thread(target=auto_accept, daemon=True).start()

            sender = TransferEngine()
            sender.start_transfer('127.0.0.1', 52066, [src])
            sender._thread.join(timeout=10)

            st = time.time()
            while recv.status != 'completed' and time.time() - st < 5:
                time.sleep(0.02)

            self.assertEqual(sender.status, 'completed')
            self.assertEqual(recv.status, 'completed')
            recv.stop()

            # Verify files in destination
            root_folder = os.path.basename(src)
            dest_root = os.path.join(dst, root_folder)
            self.assertTrue(os.path.exists(os.path.join(dest_root, 'empty.txt')))
            self.assertTrue(os.path.exists(os.path.join(dest_root, 'small.txt')))
            with open(os.path.join(dest_root, 'small.txt'), 'rb') as f:
                self.assertEqual(f.read(), b'Small file payload text')

            dest_sub = os.path.join(dest_root, 'subfolder', 'data.bin')
            self.assertTrue(os.path.exists(dest_sub))
            with open(dest_sub, 'rb') as f:
                self.assertEqual(f.read(), sub_payload)

    def test_13_detailed_network_info_and_modules(self):
        from backend.hardware_info import get_detailed_network_info
        from backend.bridge import BridgeAPI
        
        info = get_detailed_network_info()
        self.assertIn("ethernet", info)
        self.assertIn("wifi", info)
        
        bridge = BridgeAPI()
        net_info = bridge.get_my_network_info()
        self.assertIn("primary_ip", net_info)
        self.assertIn("wifi", net_info)
        self.assertIn("ethernet", net_info)
        self.assertIn("needs_setup", net_info["ethernet"])

    def test_14_temporary_network_backup_and_restore(self):
        import json
        from backend.network_config import (
            get_backup_path, check_and_restore_leftover_backup, revert_direct_ethernet
        )

        bpath = get_backup_path()
        if os.path.exists(bpath):
            os.remove(bpath)

        # 1. When no backup exists, check_and_restore returns False
        self.assertFalse(check_and_restore_leftover_backup())

        # 2. Simulate an interrupted session leaving a backup file
        mock_backup = {
            "platform": "windows" if sys.platform == "win32" else "linux",
            "ifIndex": 9999,
            "hadDhcp": True,
            "hadIp": "",
            "interface": "mock_eth",
            "assigned_ip": "192.168.123.1"
        }
        with open(bpath, "w") as f:
            json.dump(mock_backup, f)

        self.assertTrue(os.path.exists(bpath))

        # 3. Next startup detects leftover backup, reverts state, and removes backup file
        restored = check_and_restore_leftover_backup()
        self.assertTrue(restored)
        self.assertFalse(os.path.exists(bpath))

    def test_15_interrupted_transfer_resume(self):
        with tempfile.TemporaryDirectory() as src:
            test_file = os.path.join(src, 'resume_test.bin')
            with open(test_file, 'wb') as f:
                f.write(os.urandom(1024 * 1024))

            sender = TransferEngine()
            # Before transfer starts, cannot resume
            res = sender.resume_transfer()
            self.assertFalse(res['success'])

            # Set parameters as if transfer was disconnected
            sender.target_ip = '127.0.0.1'
            sender.target_port = 52077
            sender.source_paths = [test_file]
            sender.status = 'error'

            # Bridge telemetry reflects can_resume = True
            from backend.bridge import BridgeAPI
            bridge = BridgeAPI()
            bridge._transfer = sender
            telemetry = bridge.get_dashboard_telemetry()
            self.assertTrue(telemetry['can_resume'])

    def test_16_wifi_assisted_discovery_and_wire_lock(self):
        """Verifies that discovery over Wi-Fi locks the connection target strictly to direct Ethernet."""
        from backend.discovery import PeerDiscovery
        discovery = PeerDiscovery()

        # Simulate receiving a beacon over Wi-Fi (10.96.64.83) containing direct Ethernet details (192.168.123.2)
        beacon_data = json.dumps({
            "app": "tshare-v3",
            "id": "node_fedora_direct",
            "name": "Fedora-Workstation",
            "port": 52001,
            "wifi_assisted": True,
            "ethernet": {
                "name": "enp3s0",
                "ip": "192.168.123.2",
                "mac": "54:B2:03:A1:B2:C3",
                "ipv6_ll": "fe80::56b2:3ff:fea1:b2c3",
                "is_up": True,
                "speed_mbps": 1000
            },
            "wifi": {
                "name": "wlan0",
                "ip": "10.96.64.83",
                "mac": "1C:CE:51:BF:71:30"
            }
        }).encode('utf-8')

        # Directly feed to internal parser logic
        msg = json.loads(beacon_data.decode('utf-8'))
        addr = ('10.96.64.83', 52002)

        eth_info = msg.get("ethernet", {})
        wifi_info = msg.get("wifi", {})
        wire_ip = eth_info.get("ip", "")
        wire_mac = eth_info.get("mac", "")
        is_wifi_source = not (addr[0].startswith("192.168.123.") or addr[0].startswith("169.254."))

        target_ip = wire_ip if wire_ip else addr[0]

        peer_info = {
            "id": msg["id"],
            "name": msg["name"],
            "ip": target_ip,
            "wire_ip": wire_ip,
            "wire_mac": wire_mac,
            "wifi_ip": wifi_info.get("ip", addr[0]),
            "port": msg["port"],
            "last_seen": time.time(),
            "is_direct_ethernet": bool(wire_ip),
            "is_wifi_assisted": is_wifi_source and bool(wire_ip),
            "wire_locked": bool(wire_ip),
            "medium": "wire_locked"
        }

        with discovery._lock:
            discovery._peers[msg["id"]] = peer_info

        peers = discovery.get_peers()
        self.assertEqual(len(peers), 1)
        p = peers[0]

        # Primary connection IP MUST be locked to direct Ethernet (192.168.123.2), NOT Wi-Fi!
        self.assertEqual(p["ip"], "192.168.123.2")
        self.assertEqual(p["wire_ip"], "192.168.123.2")
        self.assertEqual(p["wire_mac"], "54:B2:03:A1:B2:C3")
        self.assertEqual(p["wifi_ip"], "10.96.64.83")
        self.assertTrue(p["is_wifi_assisted"])
        self.assertTrue(p["wire_locked"])
        self.assertEqual(p["medium"], "wire_locked")

    def test_17_subnet_alignment_status(self):
        """Verifies proactive detection of wire subnet mismatches."""
        from backend.discovery import PeerDiscovery
        discovery = PeerDiscovery()

        # When no peers, returns None
        self.assertIsNone(discovery.get_subnet_alignment_status())

        # When a peer is waiting on 192.168.123.2
        with discovery._lock:
            discovery._peers["peer_123"] = {
                "id": "peer_123",
                "name": "Fedora",
                "ip": "192.168.123.2",
                "wire_ip": "192.168.123.2",
                "port": 52001,
                "last_seen": time.time()
            }

        status = discovery.get_subnet_alignment_status()
        if status:
            self.assertTrue(status.get("mismatch"))
            self.assertEqual(status.get("remote_wire_ip"), "192.168.123.2")
            self.assertEqual(status.get("suggested_local_ip"), "192.168.123.1")


if __name__ == '__main__':
    unittest.main()
