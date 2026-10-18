# ⚡ Ethernet File Transfer Suite (T-Share)

High-performance, cross-platform file transfer suite designed for direct Ethernet cable and local network transfers between Windows, Linux, and macOS.

---

## Current Architecture

* **[v3/](v3/) (Active Version):** High-speed direct wire P2P socket engine (60–100+ MB/s) with 4 MB block streaming, in-flight SHA-256 integrity, crash-safe resumption, strict cross-platform path security, and a 6-tab modern desktop dashboard (`Home`, `Send`, `Receive`, `Verify`, `History`, `Settings`). Zero Samba/SMB dependencies.
* **`v1.zip` (Archived):** Original split transfer and verification tools.
* **`v2.zip` (Archived):** Prior iteration with Samba/OS sharing mechanism.

---

## Quick Launch (v3)

### Windows
```cmd
cd v3
run_win.bat
```

### Linux
```bash
cd v3
chmod +x run_linux.sh
./run_linux.sh
```

### macOS
```bash
cd v3
chmod +x run_mac.sh
./run_mac.sh
```
