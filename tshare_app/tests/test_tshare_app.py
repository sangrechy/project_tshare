"""
T-Share Unified Test Suite
Verifies:
1. Protocol framing and dynamic integrity checksums (sha256, crc32, none)
2. In-flight streaming under crc32, sha256, and none modes
3. Post-transfer cryptographic SHA-256 audit after transfer with hashing turned off
4. Path security, directory traversal rejection, and collision handling
5. History & verification database persistence
6. Web Portal REST endpoints (info, list, download, QR generation)
"""

import unittest
import sys
import os
import tempfile
import time
import threading
import json
import urllib.request

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.protocol import (
    MAGIC, HEADER_FORMAT, BLOCK_HEADER_FORMAT, HEADER_SIZE, BLOCK_HEADER_SIZE,
    compute_block_checksum, verify_block_checksum
)
from backend.path_security import sanitize_relative_path, resolve_safe_destination_path, SecurityViolation
from backend.history_db import HistoryDatabase
from backend.receiver_engine import ReceiverEngine
from backend.transfer_engine import TransferEngine
from backend.verify_engine import VerifyEngine
from backend.web_portal import WebPortalServer, generate_qr_svg


class TestTShareUnified(unittest.TestCase):

    def test_01_dynamic_integrity_checksums(self):
        sample = b"T-Share high speed block data payload 1234567890"

        # SHA-256
        sha_chk = compute_block_checksum(sample, "sha256")
        self.assertEqual(len(sha_chk), 32)
        self.assertTrue(verify_block_checksum(sample, sha_chk, "sha256"))
        self.assertFalse(verify_block_checksum(sample + b"X", sha_chk, "sha256"))

        # CRC32
        crc_chk = compute_block_checksum(sample, "crc32")
        self.assertEqual(len(crc_chk), 32)
        self.assertTrue(verify_block_checksum(sample, crc_chk, "crc32"))
        self.assertFalse(verify_block_checksum(sample + b"X", crc_chk, "crc32"))

        # None (Turned off)
        none_chk = compute_block_checksum(sample, "none")
        self.assertEqual(none_chk, b'\x00' * 32)
        self.assertTrue(verify_block_checksum(sample, none_chk, "none"))

    def test_02_path_security(self):
        with self.assertRaises(SecurityViolation):
            sanitize_relative_path("../../etc/shadow")
        with self.assertRaises(SecurityViolation):
            sanitize_relative_path("folder/../../escape.txt")

        # DOS reserved name sanitization
        self.assertEqual(sanitize_relative_path("con.txt"), "_safe_con.txt")
        self.assertEqual(sanitize_relative_path("sub/nul.log"), "sub/_safe_nul.log")

    def test_03_end_to_end_wire_streaming_crc32(self):
        with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as dst:
            test_file = os.path.join(src, "wire_test_crc.bin")
            payload = os.urandom(5 * 1024 * 1024)  # 5 MB
            with open(test_file, "wb") as f:
                f.write(payload)

            recv = ReceiverEngine(port=52080)
            recv.start()

            def auto_accept():
                while recv.status != "waiting_user":
                    time.sleep(0.01)
                recv.accept_transfer(dst, "overwrite")

            threading.Thread(target=auto_accept, daemon=True).start()

            sender = TransferEngine()
            sender.start_transfer("127.0.0.1", 52080, [test_file], hash_mode="crc32")
            sender._thread.join(timeout=10)

            st = time.time()
            while recv.status != "completed" and time.time() - st < 5:
                time.sleep(0.02)

            self.assertEqual(sender.status, "completed")
            self.assertEqual(recv.status, "completed")
            recv.stop()

            out_file = os.path.join(dst, "wire_test_crc.bin")
            self.assertTrue(os.path.exists(out_file))
            with open(out_file, "rb") as f:
                self.assertEqual(f.read(), payload)

    def test_04_streaming_with_sha_off_and_later_post_verification(self):
        """
        Critical test: Verifies that when in-flight SHA is turned OFF during transfer ('none'),
        we can run a full cryptographic SHA-256 audit later on disk and confirm bit-for-bit parity!
        """
        with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as dst, tempfile.TemporaryDirectory() as db_dir:
            test_file = os.path.join(src, "fast_raw.bin")
            payload = os.urandom(4 * 1024 * 1024)
            with open(test_file, "wb") as f:
                f.write(payload)

            db_path = os.path.join(db_dir, "test.db")
            db = HistoryDatabase(db_path)

            recv = ReceiverEngine(port=52085, history_db=db)
            recv.start()

            def auto_accept():
                while recv.status != "waiting_user":
                    time.sleep(0.01)
                recv.accept_transfer(dst, "overwrite")

            threading.Thread(target=auto_accept, daemon=True).start()

            # 1. Transfer with hashing turned completely OFF
            sender = TransferEngine(history_db=db)
            sender.start_transfer("127.0.0.1", 52085, [test_file], hash_mode="none")
            sender._thread.join(timeout=10)

            st = time.time()
            while recv.status != "completed" and time.time() - st < 5:
                time.sleep(0.02)

            self.assertEqual(sender.status, "completed")
            self.assertEqual(recv.status, "completed")
            recv.stop()

            # 2. Check history recorded hash_mode = 'none'
            transfers = db.get_transfers()
            self.assertTrue(len(transfers) >= 1)
            latest_session = transfers[0]["session_id"]

            # 3. Perform Post-Transfer Full Cryptographic SHA-256 Audit
            verifier = VerifyEngine(db)
            verifier.start_verification(latest_session, mode="full_crypto")
            verifier._thread.join(timeout=10)

            self.assertEqual(verifier.status, "passed")
            self.assertIn("Cryptographic SHA-256 Audit Passed", verifier.details)

    def test_05_web_portal_endpoints(self):
        with tempfile.TemporaryDirectory() as shared_dir, tempfile.TemporaryDirectory() as uploads_dir:
            # Create a sample file in shared directory
            sample_p = os.path.join(shared_dir, "sample.txt")
            with open(sample_p, "w") as f:
                f.write("Hello from LAN Web Portal!")

            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            ui_dir = os.path.join(base_dir, "ui")

            portal = WebPortalServer(bridge=None, ui_dir=ui_dir, port=52090)
            portal.shared_folder = shared_dir
            portal.uploads_folder = uploads_dir
            portal.start()

            try:
                # 1. Test /portal/api/info
                req = urllib.request.Request("http://127.0.0.1:52090/portal/api/info")
                with urllib.request.urlopen(req) as resp:
                    self.assertEqual(resp.status, 200)
                    data = json.loads(resp.read().decode("utf-8"))
                    self.assertIn("hostname", data)
                    self.assertTrue(data["allow_uploads"])

                # 2. Test /portal/api/list
                req = urllib.request.Request("http://127.0.0.1:52090/portal/api/list")
                with urllib.request.urlopen(req) as resp:
                    self.assertEqual(resp.status, 200)
                    data = json.loads(resp.read().decode("utf-8"))
                    self.assertTrue(data["success"])
                    self.assertEqual(len(data["items"]), 1)
                    self.assertEqual(data["items"][0]["name"], "sample.txt")

                # 3. Test /portal/api/download
                req = urllib.request.Request("http://127.0.0.1:52090/portal/api/download?path=sample.txt")
                with urllib.request.urlopen(req) as resp:
                    self.assertEqual(resp.status, 200)
                    self.assertEqual(resp.read().decode("utf-8"), "Hello from LAN Web Portal!")

                # 4. Test /portal/api/qr
                req = urllib.request.Request("http://127.0.0.1:52090/portal/api/qr")
                with urllib.request.urlopen(req) as resp:
                    self.assertEqual(resp.status, 200)
                    svg_content = resp.read().decode("utf-8")
                    self.assertIn("<svg", svg_content)

            finally:
                portal.stop()

    def test_06_qr_code_svg_generator(self):
        svg = generate_qr_svg("http://192.168.1.100:52003/portal")
        self.assertIn("<svg", svg)
        self.assertIn("Finder Pattern", svg)

    def test_07_verify_two_files_pairwise(self):
        verifier = VerifyEngine()
        with tempfile.TemporaryDirectory() as td:
            f1 = os.path.join(td, "orig.bin")
            f2 = os.path.join(td, "copy.bin")
            f3 = os.path.join(td, "corrupt.bin")

            data = os.urandom(1024 * 1024)
            with open(f1, "wb") as f:
                f.write(data)
            with open(f2, "wb") as f:
                f.write(data)
            with open(f3, "wb") as f:
                f.write(data + b"different")

            # 1. Matching pair
            res_match = verifier.verify_two_files(f1, f2)
            self.assertTrue(res_match["success"])
            self.assertTrue(res_match["match"])
            self.assertEqual(res_match["status"], "MATCH")
            self.assertEqual(res_match["original_hash"], res_match["received_hash"])

            # 2. Mismatching pair
            res_mismatch = verifier.verify_two_files(f1, f3)
            self.assertTrue(res_mismatch["success"])
            self.assertFalse(res_mismatch["match"])
            self.assertEqual(res_mismatch["status"], "MISMATCH")
            self.assertNotEqual(res_mismatch["original_hash"], res_mismatch["received_hash"])

    def test_08_event_logging(self):
        sender = TransferEngine()
        sender.log_event("Testing sender log entry")
        logs = sender.get_logs()
        self.assertTrue(len(logs) >= 2)
        self.assertIn("Testing sender log entry", logs[-1])

        recv = ReceiverEngine(port=52099)
        recv.log_event("Testing receiver log entry")
        r_logs = recv.get_logs()
        self.assertTrue(len(r_logs) >= 2)
        self.assertIn("Testing receiver log entry", r_logs[-1])

    def test_09_bridge_apis(self):
        from backend.bridge import BridgeAPI
        bridge = BridgeAPI()
        with tempfile.TemporaryDirectory() as td:
            # Test default destination saving
            dest_res = bridge.save_default_destination(td)
            self.assertTrue(dest_res["success"])
            self.assertEqual(dest_res["path"], td)

            get_dest = bridge.get_default_destination()
            self.assertEqual(get_dest["path"], td)

            # Test source file management
            f1 = os.path.join(td, "file1.txt")
            f2 = os.path.join(td, "file2.txt")
            with open(f1, "w") as f:
                f.write("A")
            with open(f2, "w") as f:
                f.write("B")

            set_res = bridge.set_source_paths([f1, f2])
            self.assertEqual(set_res["count"], 2)

            rem_res = bridge.remove_source_path(0)
            self.assertEqual(rem_res["count"], 1)

            clear_res = bridge.clear_source_paths()
            self.assertEqual(clear_res["count"], 0)

            # Test logs retrieval
            logs = bridge.get_transfer_logs()
            self.assertIsInstance(logs, list)


if __name__ == "__main__":
    unittest.main()
