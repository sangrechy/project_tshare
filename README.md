# project_tshare

A unified suite of file-sharing and transfer tools providing web-based portals, LAN file browsing, and high-speed direct Ethernet replication with cryptographic verification.

---

## 📱 Cross-Platform Flutter App: `tshare_flutter/` (Linux, Windows, macOS, Android)

The **`tshare_flutter`** folder provides the complete, production-grade Flutter desktop and mobile application implementing the official TShare specification:

* **Fixed 5-Navigation Top Bar:** Instant switching between `HOME`, `FILE SHARING`, `FILE SERVER`, `VERIFY`, and `SETTINGS`.
* **Single-Page 3-State Rotary File Sharing:**
  * **State 1 (Rotary Telephone Dial):** Interactive animated rotating outer ring with fixed stationary labels (`SEND`, `RECEIVE`, `WiFi`, `BLE`, `Ethernet`) and central `SELECT`.
  * **State 2 (Device Connection):** Seamless transition into Manual Connect and UDP multicast Auto Find Devices.
  * **State 3 (Transfer Dashboard):** Real-time dual circular speed & CPU gauges, block progress bar, live terminal logs, in-flight checksum validation, pause/resume.
* **Embedded LAN File Server:** Built-in HTTP portal on port 52003 with dynamic QR code generation for instant mobile browsing, downloading, and uploading.
* **Pairwise SHA-256 Audit (`VERIFY`):** Chunked bit-for-bit cryptographic verification with instant match/mismatch verdict.
* **Settings & Diagnostics:** Persistent download directory, CRC32/SHA-256/Turbo integrity selector, bandwidth governor, and hardware diagnostics.

```bash
cd tshare_flutter
flutter run -d linux    # or windows / macos / android
```

---

## 🚀 Unified Python App: `tshare_app/`

The **`tshare_app`** folder unites the desktop and web portal in Python:

* **Direct Cable (P2P Wire Engine):** Pure raw TCP socket streaming at 60–100+ MB/s line-rate with 4 MB aligned blocks, Wi-Fi assisted wire-locking, and automatic PID-bound network configuration rollback.
* **In-Flight Integrity Toggle:** Choose between `CRC32 Fast Stream` (~1% CPU), `SHA-256 Cryptographic`, or `Disabled / Turbo Raw` (Max wire speed).
* **On-Demand Post-Transfer Verification:** Run full bit-for-bit SHA-256 cryptographic audits anytime after transfer, even if hashing was turned off during the transfer!
* **Built-in LAN Web Portal:** Seamlessly browse, download, and upload files from any smartphone, tablet, or browser over local Wi-Fi with an instant on-screen QR Code.
* **Unified 6-Tab Interface:** `Home`, `Direct Cable`, `LAN Web Portal`, `Verify & Audit`, `History`, `Settings`.

### Quick Launch (`tshare_app`)
```bash
# Linux
cd tshare_app && ./run_linux.sh

# Windows
cd tshare_app && run_win.bat

# macOS
cd tshare_app && ./run_mac.sh

# Browser Mode (Headless / Zero GUI dependencies)
cd tshare_app && python3 app.py --web
```

---

## 🧰 Sub-Tools Overview

The repository provides the following implementations:

| Tool | Core Technology | Primary Use Case |
| :--- | :--- | :--- |
| [**`tshare_flutter/`**](tshare_flutter/) | Dart, Flutter (Cross-platform) | **Full Cross-Platform App** (Linux, Windows, macOS, Android) with rotary telephone dial, embedded LAN server, and SHA-256 audit. |
| [**`tshare_app/`**](tshare_app/) | Python 3, PyWebView, Raw Sockets, SQLite | **Desktop & Web Suite** uniting direct wire transfers, mobile web portal, and dynamic SHA/CRC32 verification. |
| [**`share_by_web_tool/`**](share_by_web_tool/) | Node.js, Express, Multer | Browser-based file sharing portal for uploading, downloading, and managing files across devices. |
| [**`file_server_tool/`**](file_server_tool/) | Node.js, Express | Lightweight read-only LAN file server with automatic IP detection and folder navigation. |
| [**`share_by_ethernet_tool/`**](share_by_ethernet_tool/) | Python, PyWebView, Sockets | High-speed direct Ethernet / LAN sync with kernel I/O telemetry, safe resume, and multi-level verification. |

---

## 📂 Repository Structure

```text
project_tshare/
├── README.md                      # Unified repository guide (this file)
├── .gitignore                     # Root gitignore
├── tshare_app/                    # ⭐ Unified Master Suite (All 3 tools combined)
│   ├── app.py                     # Master desktop entrypoint + browser fallback
│   ├── requirements.txt           # Minimal dependencies (pywebview, psutil)
│   ├── run_linux.sh               # Cross-platform launchers
│   ├── run_mac.sh
│   ├── run_win.bat
│   ├── set_ethernet_ip.sh         # Direct cable network helpers
│   ├── set_ethernet_ip.bat
│   ├── tshare_history.db          # SQLite transfer and audit ledger
│   ├── backend/                   # Protocol, transfer, receiver, portal, discovery, verify
│   ├── ui/                        # Cyberpunk 6-tab desktop dashboard
│   │   └── portal/                # Mobile client web portal
│   └── tests/                     # Automated unit and benchmark suite
├── share_by_web_tool/             # Tool 1: Browser-based Upload & Download Server
│   ├── README.md
│   └── v1/
├── file_server_tool/              # Tool 2: Local Network File Browser & Server
│   ├── README.md
│   ├── v1/
│   └── v2/
└── share_by_ethernet_tool/        # Tool 3: Direct Ethernet / LAN Transfer Suite
    ├── README.md
    ├── v1.zip
    ├── v2.zip
    └── v3/
```

---

## 🔒 Security & Privacy Notes

* All tools operate locally on your private network by default.
* For internet exposure via tunnels (e.g. ngrok), configure proper authentication and rate-limiting.
