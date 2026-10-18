# ⚡ Ethernet File Transfer & Deep Verification Suite

A high-performance **Dark Neumorphic & Glassmorphic Desktop Application Suite** designed for ultra-fast, resilient local network and direct Ethernet file transfers and bit-level transaction audits on Windows.

---

## 🚀 Quick Start: v2 Unified Cockpit (Cross-Platform)

**v2 combines Send, Receive, 3-Tier Verification, and SQLite History into a single modern desktop app running across Windows, Linux, and macOS:**

```bash
# Launch v2 application:
cd share_by_ethernet_tool/v2
python app.py
```

* **Home:** Hardware network adapters, link speeds (1G/2.5G/10G), IP display, local drive storage meters.
* **Send:** Multithreaded Robocopy (`/Z /J /MT`) on Windows, `rsync` (`--partial --inplace`) on Linux/macOS, dual kernel I/O dials, live 60fps canvas chart, safe resume, auto-verify.
* **Receive:** Computer IP & hostname display, automated network share provisioner with permission rollback, live incoming folder watcher.
* **Verify:** Sender vs Receiver cross-audit or single-tree audit with Fast Parity, Smart Block SHA-256, or Full Bit-by-Bit SHA-256, plus exportable HTML certificates.
* **History:** Persistent SQLite history ledger (`tshare_history.db`) with one-click re-verify and folder open.

### 🌐 Cross-Platform Architecture & Decoupled Platform Folders
Operating-system-specific logic is strictly decoupled into dedicated modules under `v2/platforms/`:
* **`v2/platforms/win/`**: Windows adapter (Robocopy `/E /Z /J /MT:8`, Win32 `GetProcessIoCounters`, PowerShell network discovery, `net share` UAC elevation).
* **`v2/platforms/linux/`**: Linux adapter (`rsync --partial --inplace`, `/proc/[pid]/io` kernel metrics, `ip/sysfs` discovery, Samba usershares with `pkexec` elevation).
* **`v2/platforms/mac/`**: macOS adapter (`rsync`, `scutil/networksetup` discovery, macOS `sharing` CLI with AppleScript administrator prompt).

### 🛡️ Fail-Safe Share Permission Lease & Crash Recovery
* **Permission Journaling:** Before modifying any network sharing permissions or creating a share, the app journals the lease in `share_lease.json`.
* **Automatic Rollback:** Share permissions are immediately revoked when a transfer completes, is canceled, or when receiver monitoring stops.
* **Boot-Time Recovery:** If the app is killed abruptly, crashes, or the machine shuts down during a transfer, **the very first action executed upon next startup is detecting the orphaned lease and revoking all share permissions**.

---

## 📦 Suite Versions

* **[v2/ (Unified Desktop Cockpit)](file:///E:/projects/project_tshare/share_by_ethernet_tool/v2):** All-in-one unified desktop application combining transfer, receiver, deep verification, history, and cross-platform decoupling (`win`, `linux`, `mac`).
* **[v1/ (Original Split Tools)](file:///E:/projects/project_tshare/share_by_ethernet_tool/v1/README.md):** Standalone monitors (`app.py` for Transfer and `verify_app.py` for Verification).

---

## 📦 Legacy Suite Applications (v1)

### 1. Dual-Deck Robocopy Transfer Monitor (`app.py`)
* **Safe Resume Mode:** Uses Windows Robocopy with `/E /Z /J /XO /FFT /R:2 /W:2 /MT:8` to safely copy and resume interrupted transfers without ever deleting or corrupting existing destination files.
* **Kernel I/O Telemetry:** Independent real-time upload/read outflow and download/disk write speed dials sampled directly from Windows process I/O counters (`GetProcessIoCounters`).
* **Live Visuals:** Real-time throughput sparkline graph, animated flow equalizers, connection latency monitors, and continuous Estimation Time (ETA) calculation.
* **Process Identity Protection:** Tracks Robocopy PID and creation timestamps (`FILETIME`) via Win32 API, allowing you to close and re-attach the GUI monitor anytime without interrupting the background transfer.

```powershell
# From share_by_ethernet_tool/v1/

# Launch primary Neumorphic Soft UI (PyWebView)
python app.py

# Launch Tkinter dark fallback interface
python app.py --tk

# Launch with custom source and destination paths
python app.py --source "\\192.168.1.X\SharedFolder" --dest "D:\Transfer"
```

---

### 2. Transaction Deep Verifier (`verify_app.py`)
A comprehensive multi-level audit suite designed to verify file transfers across trees down to the byte and bit level.

* **Level 1: Fast Parity Audit:**
  * Traverses both directory trees.
  * Verifies 100% relative path parity (identifies any missing files).
  * Confirms exact file size in bytes matches down to the single byte.
  * Checks timestamps with SMB tolerance. Completes in seconds.
* **Level 2: Smart Block Checksum:**
  * Computes cryptographic SHA-256 hashes of the Header (1MB), Middle (1MB), and Footer (1MB) of every file.
  * Catches corrupted headers, truncated media files, and bit flips in a fraction of full-hash time.
* **Level 3: Full Cryptographic SHA-256 Bit-by-Bit Verification:**
  * Multi-threaded bit-by-bit SHA-256 hash comparison across the entire volume.
  * Mathematically guarantees 100% data integrity with zero bit rot or silent corruption.
  * Displays live hashing throughput (MB/s) and estimated time remaining (ETA).
* **Interactive Audit Ledger:**
  * Searchable and filterable ledger displaying every verified file, size, integrity status, and hash footprint.
* **Exportable Audit Certificate:**
  * One-click export to a standalone Dark Neumorphic HTML Verification Certificate (`TRANSACTION_VERIFICATION_CERTIFICATE.html`).

```powershell
# From share_by_ethernet_tool/v1/

# Launch primary Neumorphic Soft UI (PyWebView)
python verify_app.py

# Launch Tkinter dark fallback interface
python verify_app.py --tk

# Launch with custom paths
python verify_app.py --source "\\192.168.1.X\SharedFolder" --dest "D:\Transfer"
```

---

## 🛠️ Requirements & Prerequisites

* **Operating System:** Windows 10 / 11 (Robocopy and Win32 kernel I/O counters are native to Windows)
* **Python:** 3.10 or newer
* **Dependencies:**
  ```powershell
  pip install pywebview
  ```
  *(Tkinter is bundled with standard Windows Python installations)*

---

## ⚙️ Configuration & Environment Variables

You can supply paths via CLI arguments or set default environment variables:

| Variable | Description | Default Fallback |
| :--- | :--- | :--- |
| `TSHARE_SOURCE` | Default source directory or UNC network share | `\\192.168.1.X\SharedFolder` |
| `TSHARE_DEST` | Default target destination directory | `D:\Transfer` |

---

## 📁 Directory Structure

```text
share_by_ethernet_tool/
├── .gitignore
├── README.md
└── v1/
    ├── app.py                      # Main Transfer Monitor launcher (PyWebView)
    ├── tkinter_app.py              # Tkinter dark Transfer Monitor fallback
    ├── verify_app.py               # Deep Verifier launcher (PyWebView)
    ├── verify_tkinter.py           # Tkinter dark Deep Verifier fallback
    ├── backend/
    │   ├── transfer_engine.py      # Robocopy engine & kernel I/O speed counters
    │   └── verify_engine.py        # Cryptographic SHA-256 & parity audit engine
    ├── ui/                         # Transfer Monitor Neumorphic UI
    │   ├── index.html
    │   ├── styles.css
    │   └── app.js
    └── ui_verify/                  # Deep Verifier Neumorphic UI
        ├── index.html
        ├── styles.css
        └── app.js
```
