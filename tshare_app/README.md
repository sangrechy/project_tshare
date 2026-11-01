# ⚡ T-Share Unified Suite (`tshare_app`)

A high-performance, cross-platform file transfer and LAN sharing suite uniting direct gigabit cable transfers, mobile browser portals, and flexible cryptographic verification.

---

## 🌟 Highlights

1. **Direct Cable High-Speed Transfer (Wire Engine):**
   - Pure raw TCP streaming with aligned 4 MB chunks (**60–100+ MB/s** wire saturation).
   - Zero Samba/SMB dependencies, zero OpenSSL certificate overhead.
   - **Configurable In-Flight Integrity Verification:**
     - `CRC32 Fast Stream` (Hardware-accelerated error check via Python standard library `zlib.crc32`, ~1% CPU).
     - `SHA-256 Full Cryptographic` (In-flight bit-for-bit mathematical validation).
     - `Disabled / Turbo Raw` (Max physical wire throughput, zero hashing overhead during transfer).
   - **Post-Transfer Cryptographic Audit:** Audit any past session with full SHA-256 verification directly from disk whenever you want, even if hashing was turned off during the transfer!
   - Automatic block-level crash resumption via `.tshare_state` journals.
   - Wi-Fi assisted peer discovery + Ethernet wire-locking (`192.168.123.x`).

2. **Built-in LAN Web Portal & File Server:**
   - **Zero Node.js dependency:** Runs on pure Python standard library HTTP server.
   - **Browse & Download:** Explore shared host directories recursively with breadcrumbs, search, and instant downloads.
   - **Upload from Phones & Laptops:** Drag-and-drop multipart upload stream directly from any mobile or desktop web browser.
   - **Scannable QR Code:** Desktop screen displays an SVG QR Code for instant smartphone connection without typing URLs.

3. **Unified Desktop Interface:**
   - Cyberpunk / Dark Neumorphic 6-tab dashboard (`Home`, `Direct Cable`, `Web Portal`, `Verify`, `History`, `Settings`).
   - Runs in native PyWebView window or falls back automatically to zero-dependency Web Browser Mode.

---

## 🚀 Quick Start

### Linux
```bash
cd tshare_app
chmod +x run_linux.sh
./run_linux.sh
```

### Windows
Double-click `run_win.bat` or run in Command Prompt:
```cmd
cd tshare_app
run_win.bat
```

### macOS
```bash
cd tshare_app
chmod +x run_mac.sh
./run_mac.sh
```

### Browser Mode (No GUI libraries needed)
```bash
python3 app.py --web
```
Access the desktop app at `http://localhost:52003` and the mobile portal at `http://<your-ip>:52003/portal`.

---

## 🔒 Verification Workflow (In-Flight vs. Post-Transfer)

* **Maximum Transfer Speed (Recommended for large files / low-power CPUs):**
  1. In the **Direct Cable** tab, set *In-Flight Verification Mode* to **`CRC32 Fast Stream`** or **`Disabled / Turbo Raw`**.
  2. Start transfer at full line rate with near 0% CPU consumption.
  3. After the transfer completes, navigate to the **Verify & Audit** tab, choose the session, and click **Start Cryptographic Audit**. Both computers read the saved files and compute full SHA-256 checksums to verify bit-for-bit parity.

* **Immediate Validation:**
  1. Set *In-Flight Verification Mode* to **`SHA-256 Cryptographic`**.
  2. Each 4 MB block is hashed in RAM and confirmed before writing to disk.

---

## 📂 Architecture

```text
tshare_app/
├── app.py                     # Desktop entrypoint (PyWebView + Browser fallback)
├── requirements.txt           # pywebview, psutil
├── run_linux.sh               # Linux launcher
├── run_mac.sh                 # macOS launcher
├── run_win.bat                # Windows launcher
├── set_ethernet_ip.sh         # Linux cable setup helper
├── set_ethernet_ip.bat        # Windows cable setup helper
├── tshare_history.db          # SQLite transfer and audit ledger
├── backend/
│   ├── bridge.py              # PyWebView JavaScript API endpoints
│   ├── protocol.py            # Raw TCP framing + dynamic integrity modes
│   ├── transfer_engine.py     # High-speed sender engine
│   ├── receiver_engine.py     # High-speed receiver + journal engine
│   ├── discovery.py           # UDP discovery + wire-locking
│   ├── web_portal.py          # LAN file server, upload portal & QR engine
│   ├── network_config.py      # IP auto-config & PID watchdogs
│   ├── hardware_info.py       # Telemetry for RAM, CPU, Disk, Link
│   ├── path_security.py       # Traversal security & boundary checks
│   ├── history_db.py          # SQLite persistence
│   └── verify_engine.py       # Two-tier parity & full SHA-256 auditor
├── ui/
│   ├── index.html             # 6-Tab master desktop dashboard
│   ├── styles.css             # Cyberpunk dark theme
│   ├── app.js                 # Frontend state and polling controller
│   └── portal/                # Mobile client portal
│       ├── index.html         # Responsive phone UI
│       ├── portal.css
│       └── portal.js
└── tests/
    └── test_tshare_app.py     # Automated test suite
```
