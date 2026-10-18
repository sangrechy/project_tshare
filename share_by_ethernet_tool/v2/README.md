# ⚡ T-Share v2 Pro • Ethernet Transfer & Deep Verification Cockpit

A unified, high-performance **Dark Neumorphic & Glassmorphic Desktop Application** combining high-speed Windows Robocopy process orchestration, direct Ethernet receiver monitoring, multi-tier cryptographic integrity audits, and persistent SQLite history tracking into a single cohesive interface.

---

## 🌟 What's New in v2 vs v1

| Feature | v1 Suite | v2 Unified Cockpit |
| :--- | :--- | :--- |
| **Application Architecture** | Two separate apps (`app.py` & `verify_app.py`) | **Single Unified Desktop Cockpit** with instant tab navigation |
| **Home Dashboard** | None | **Live Hardware & Network Telemetry**, Adapter Link Speed (100M/1G/2.5G/10G), Drive Storage meters |
| **Receiver Mode** | Manual path typing only | **Receiver Dashboard**, Host & IP auto-display, 1-click Windows SMB Share setup, Live Folder Watcher |
| **Verification Integration** | Standalone manual tool | **Seamless Sender-to-Receiver Handshake** + Optional **Auto-Verify on Transfer Finish** |
| **History & Auditing** | None (Lost on close) | **Persistent SQLite Database (`tshare_history.db`)** with 1-click Re-Verify and Report recall |
| **Folder Selection** | Manual UNC string entry | **Native Windows Folder Selection Dialogs** via PyWebView & Win32 API |
| **Visual Design** | Neumorphic dark cards | **Refined Cyber Soft UI / Glassmorphism** with 60fps Canvas Throughput Chart and Equalizers |

---

## 🚀 Quick Launch (Per OS Launchers)

Each launcher automatically checks dependencies, self-installs any missing Python packages via `pip`, verifies system utilities (Robocopy on Windows, rsync on Linux/macOS), and launches the Cockpit.

### 🪟 Windows:
* **Double-click:** [`run_win.bat`](file:///e:/projects/project_tshare/share_by_ethernet_tool/v2/run_win.bat)
* **Terminal:**
  ```powershell
  cd share_by_ethernet_tool\v2
  .\run_win.bat
  ```

### 🐧 Linux:
* **Terminal:**
  ```bash
  cd share_by_ethernet_tool/v2
  chmod +x run_linux.sh
  ./run_linux.sh
  ```

### 🍎 macOS:
* **Finder:** Double-click [`run_mac.command`](file:///e:/projects/project_tshare/share_by_ethernet_tool/v2/run_mac.command)
* **Terminal:**
  ```bash
  cd share_by_ethernet_tool/v2
  chmod +x run_mac.sh
  ./run_mac.sh
  ```

### ⚡ Launch with Pre-Configured Source & Target Paths:
```bash
python app.py --source "/path/to/source" --dest "/path/to/destination"
```

---

## 📦 Application Modules

### 1. ☖ Home Dashboard
- **Active Network Telemetry:** Automatically identifies all local network interfaces (Ethernet, Wi-Fi 6, PCIe NICs), current link speeds (e.g. `1000 Mbps`, `2500 Mbps`), MAC addresses, and assigned IPv4 addresses.
- **Drive Storage Status:** Real-time visual progress meters showing used and free space across all local drives (`C:`, `D:`, `E:`, etc.).
- **Active Operation Banner:** If a background Robocopy transfer or verification audit is running, Home shows a live mini-player widget with current speed, active file, and progress bar.
- **Lifetime Statistics:** Persistent lifetime counters for total bytes transferred, peak speed, completed transfers, and verified files.

---

### 2. ↑ Send (High-Speed Robocopy Deck)
- **Safe Resume Mode (`/Z`):** Restarts interrupted copies from where they left off without re-copying or corrupting existing destination files.
- **Direct Unbuffered I/O (`/J`):** Bypasses the Windows file cache for gigabit and multi-gigabit transfers to eliminate RAM exhaustion on large files.
- **Multi-Threading (`/MT:1` to `/MT:64`):** Maximizes I/O queue depth across high-bandwidth Ethernet connections.
- **Dual Kernel Speed Telemetry:** Real-time Upload/Read and Download/Write speed dials sampled directly from Windows process I/O counters (`GetProcessIoCounters`).
- **Live Throughput Chart:** 60fps HTML5 Canvas graph rendering upload (violet) and download (blue) throughput curves with peak speed indicator.
- **Process Identity Protection:** Tracks Robocopy PID and creation timestamps (`FILETIME`). You can close the app and re-launch it anytime; it automatically re-attaches to the running transfer.
- **Auto-Verify Trigger:** When enabled, the app immediately transitions into the Deep Verifier upon transfer completion and executes the verification audit automatically.

---

### 3. ↓ Receive (Receiver & Share Assistant)
- **Local Machine Identity:** Displays your computer's Hostname, Ethernet IP address, and ready-to-copy UNC paths (e.g. `\\MY-PC\Transfers` or `\\192.168.1.45\Transfers`).
- **Windows Share Helper:** One-click generation and execution of Windows network share commands (`net share Transfers="D:\Incoming" /grant:Everyone,FULL`).
- **Inbound Folder Watcher:** A background directory watcher that tracks files landing in the destination directory in real-time, calculating live incoming write throughput and displaying recently arrived files.
- **Pass to Verifier:** Instant button to pre-fill and launch the Deep Verifier on the received files.

---

### 4. 🛡 Verify (Deep Transaction & Bit-Level Audit)
- **Dual Role Audit:**
  - **Cross-Audit:** Verifies integrity between Sender Source tree and Receiver Destination tree across the Ethernet connection.
  - **Single-Tree Audit:** Self-audits an incoming or local folder for corruptions or against generated manifests.
- **3 Verification Tiers:**
  - **Level 1 (Fast Parity Audit):** Compares byte-exact file sizes, counts, and relative path structure down to the single byte with SMB timestamp tolerance. Completes in seconds.
  - **Level 2 (Smart Block Checksum):** Computes cryptographic SHA-256 hashes of the Header (1MB), Middle (1MB), and Footer (1MB) of every file. Catches media truncations and bit corruption 10x faster.
  - **Level 3 (Cryptographic Bit-by-Bit SHA-256):** Full SHA-256 hash comparison across the entire volume with a multi-threaded parallel worker pool. Mathematically guarantees zero bit rot.
- **Interactive Audit Ledger:** Searchable and filterable ledger (`All`, `Matched`, `Mismatched`, `Missing`, `Extra`) with status badges and hash fingerprints.
- **Exportable HTML Certificate:** Generates a standalone Dark Neumorphic Verification Certificate (`TRANSACTION_AUDIT_CERTIFICATE_*.html`) with digital seal and timestamp.

---

### 5. ⏱ History & Database
- Powered by a local SQLite database (`tshare_history.db`).
- Records every Transfer and Verification task with timestamp, paths, file counts, total size, peak/average speeds, duration, and status.
- Action buttons on every entry:
  - **🛡 Re-Verify:** Automatically opens the Verifier tab pre-filled with the exact source and destination paths from that session.
  - **📂 Open:** Opens the target folder directly in Windows Explorer.
  - **✕ Delete:** Removes individual records or clears all history.

---

### 6. ⚙ Logs & Diagnostics
- **SMB Ping Diagnostic:** Test TCP latency to port 445 on any remote host or UNC path with millisecond precision.
- **Active Shares Inspector:** Discovers all currently shared folders on the host machine.
- **Unified Event Log:** Real-time log stream showing engine lifecycle events, warnings, and Robocopy execution traces.

---

## 📁 Project Structure

```text
share_by_ethernet_tool/
├── README.md                       # Root suite guide
├── requirements.txt                # Root dependencies specification
├── run_v2.bat                      # Windows root launcher
├── run_v2.sh                       # Linux / macOS root launcher
├── v1/                             # v1 legacy standalone tools
└── v2/                             # v2 Unified Cockpit
    ├── app.py                      # Main unified application entrypoint (PyWebView)
    ├── requirements.txt            # v2 dependencies (pywebview + macOS WebKit bindings)
    ├── run.bat                     # Windows primary batch launcher (checks & installs deps)
    ├── run_win.bat                 # Windows alias launcher
    ├── run_linux.sh                # Linux bash launcher (checks & installs deps)
    ├── run_mac.sh                  # macOS shell launcher (checks & installs deps)
    ├── run_mac.command             # macOS Finder double-clickable launcher
    ├── run.sh                      # Universal POSIX auto-dispatch launcher
    ├── README.md                   # Complete v2 documentation
    ├── backend/
    │   ├── __init__.py
    │   ├── bridge.py               # Bidirectional JS/Python API bridge & folder pickers
    │   ├── dependency_checker.py   # Pre-flight environment audit & auto-installer
    │   ├── history_db.py           # SQLite database operations & aggregate stats
    │   ├── network_detector.py     # Cross-platform network adapters, speeds, IPs, and drives
    │   ├── receiver_engine.py      # Incoming folder watcher & share assistant
    │   ├── transfer_engine.py      # Transfer orchestrator (Robocopy & rsync) & telemetry
    │   └── verify_engine.py        # 3-tier cryptographic verification & HTML certificates
    ├── platforms/
    │   ├── __init__.py             # Platform adapter factory & startup safety check
    │   ├── base.py                 # Abstract PlatformAdapter ABC
    │   ├── lease_manager.py        # Share lease journal & crash-recovery cleanup
    │   ├── win/                    # Windows-specific implementation (Robocopy, Win32 I/O, net share)
    │   ├── linux/                  # Linux-specific implementation (rsync, /proc/io, Samba pkexec)
    │   └── mac/                    # macOS-specific implementation (rsync, sharing CLI, AppleScript)
    ├── ui/
    │   ├── index.html              # Unified Single-Page Application
    │   ├── styles.css              # Dark Neumorphic & Glassmorphic CSS design system
    │   └── app.js                  # Frontend telemetry, canvas chart, & state controller
    └── reports/                    # Generated HTML audit certificates
```

---

## 🛠️ Requirements & Compatibility

- **OS:** Windows 10/11, Linux (Ubuntu/Debian, Fedora, Arch), macOS 11+
- **Python:** 3.8+ (tested on Python 3.10, 3.11, 3.12, 3.14)
- **Dependencies:**
  All Python dependencies are defined in `requirements.txt` and automatically installed by the launchers (`run.bat`, `run_linux.sh`, `run_mac.sh`):
  ```bash
  pip install -r requirements.txt
  ```
  *(Standard Python library supplies sqlite3, ctypes, threading, socket, hashlib, and subprocess)*
