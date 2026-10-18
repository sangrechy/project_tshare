# T-Share v3 — Direct Ethernet High-Speed File Transfer

High-performance, crash-resilient peer-to-peer file transfer engine engineered for direct laptop-to-laptop Ethernet connections (Windows ↔ Linux ↔ macOS). Capable of transferring **500 GB+** payloads at full 1 Gbps wire speed (**60–100+ MB/s**) with **zero data loss**, **automatic block-level resumption**, and **zero Samba/SMB dependencies**.

---

## Key Features

1. **Pure Native TCP Streaming (No TLS Overhead):**
   - Direct raw TCP socket streaming with `TCP_NODELAY` and 2 MB socket buffers.
   - Eliminates TLS encryption context-switching overhead to sustain full physical wire speed.

2. **In-Flight 4 MB Block Cryptographic Integrity:**
   - Files are partitioned into aligned 4 MB blocks.
   - The Sender calculates `SHA-256` of each block directly in RAM before sending.
   - The Receiver verifies the checksum in RAM *before* writing the block to disk.
   - Blocks with checksum errors are automatically re-requested (NACK).

3. **Crash-Safe Resumption via `.tshare_state` Journals:**
   - Resuming does not guess from partial file sizes.
   - The Receiver maintains a bitmask journal of verified blocks.
   - If the connection drops at 250 GB out of 500 GB, the Sender queries the journal on reconnect and transmits only missing blocks.

4. **Strict Path Security & Cross-Platform Sanitization:**
   - Traversal protection (`..` rejection).
   - Strips drive letters and leading slashes.
   - Sanitizes Windows reserved device names (`CON`, `PRN`, `AUX`, `NUL`, `COM1-9`, `LPT1-9`).
   - Receiver destination containment enforcement via `os.path.commonpath`.
   - **Sender never sees the Receiver's internal disk paths.**

5. **Strict 6-Tab User Interface:**
   - **Home:** Live hardware meters (link speed, disk space, CPU/RAM). Auto-switches here when transfer starts to display a live speedometer gauge (MB/s), ETA, active file, and progress bars.
   - **Send:** Auto-discovery + manual IP fallback, source file/folder picker, read-only receiver status.
   - **Receive:** Incoming offer inspection, receiver destination folder authority, collision policy selector, direct IP:port pill with copy button.
   - **Verify:** Dual history ledgers (Sender vs. Receiver) with Quick Parity and Full Cryptographic SHA-256 disk audits.
   - **History:** Completed transfer logs with "Open Folder" button.
   - **Settings:** "Use Full Resources" master toggle and 4 hardware-scaled sliders (RAM buffer, CPU duty cycle, Worker threads, Bandwidth cap).

---

## Quick Start

### Windows
Double-click `run_win.bat` or run:
```cmd
run_win.bat
```

### Linux
```bash
chmod +x run_linux.sh
./run_linux.sh
```

### macOS
```bash
chmod +x run_mac.sh
./run_mac.sh
```

---

## Direct Cable Setup (Zero Configuration)

1. Connect an Ethernet cable directly between the two laptops.
2. Both operating systems will automatically assign Link-Local addresses (`169.254.x.x`).
3. Start T-Share v3 on both laptops.
4. If auto-discovery is blocked by a local firewall, simply copy the **Direct Connect Address** shown on the **Receive** tab and paste it into the **Send** tab on the sender laptop.
