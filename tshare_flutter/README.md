# TShare – Cross-Platform Flutter Application

A complete cross-platform desktop & mobile implementation of **TShare** built in **Dart & Flutter**, targeting **Linux, Windows, macOS, and Android** from a single unified codebase.

---

## 🌟 Highlights & Features

- **Fixed Top Navigation Bar:** Instant switching between `HOME`, `FILE SHARING`, `FILE SERVER`, `VERIFY`, and `SETTINGS`.
- **Rotary File Sharing (Single Page 3-Stage Workflow):**
  - **State 1 – Rotary Dial Selector:** Vintage telephone-inspired circular dial with fixed labels (`SEND`, `RECEIVE`, `WiFi`, `BLE`, `Ethernet`) and an animated, interactive rotating outer ring with a central `SELECT` button.
  - **State 2 – Device Connection Panel:** Smooth transition into Manual Connect (IP/Port) and Auto Find Devices (UDP multicast peer discovery) with responsive device list and connection states.
  - **State 3 – Real-Time Transfer Dashboard:** Live speed gauge, CPU telemetry, block-by-block progress bar, in-flight checksum validation, pause/resume, and terminal logging.
- **Embedded LAN File Server:**
  - Built-in lightweight HTTP server (`dart:io`) on port `52003`.
  - Serves a modern mobile-responsive web portal with instant QR code generation for camera scanning.
  - Cross-device file download and multipart file uploads directly from phones, tablets, and laptops.
- **Pairwise Cryptographic Verification (`VERIFY`):**
  - Bit-for-bit SHA-256 chunked streaming file audit between original and received files.
  - Real-time comparison with instant `MATCH` / `MISMATCH` verdict and hexadecimal digest display.
- **Application Settings (`SETTINGS`):**
  - Configurable download directories with path picker.
  - In-flight integrity selection (`CRC32`, `SHA-256`, or `None / Turbo`).
  - Bandwidth rate limiter / governor slider.
  - Full system diagnostics and network hardware telemetry.

---

## 🏗️ Architecture

Layered Clean MVVM architecture:

```
lib/
├── core/
│   ├── constants/app_constants.dart      # Protocol magic (TSHR v4), ports, block sizing (4 MB)
│   ├── theme/app_theme.dart              # Cyber-dark theme with glowing cyan accents
│   └── utils/network_info.dart           # Cross-platform LAN IPv4 detection
├── data/
│   ├── models/
│   │   ├── audit_result.dart             # SHA-256 pairwise audit model
│   │   ├── file_item.dart                # Shared & transferred file descriptor
│   │   └── peer_device.dart              # Discovered LAN peer device model
│   └── services/
│       ├── lan_file_server.dart          # HTTP portal & mobile upload/download server
│       ├── peer_discovery.dart           # UDP broadcast announcer & listener
│       ├── transfer_receiver.dart        # TCP socket listener with atomic staging
│       ├── transfer_sender.dart          # High-performance 4 MB streaming socket client
│       ├── verify_service.dart           # Chunked SHA-256 streaming verification
│       └── wire_protocol.dart            # Binary framing, 16-byte magic header, CRC32, SHA-256
├── presentation/
│   ├── viewmodels/
│   │   ├── app_viewmodel.dart            # Global settings & navigation state
│   │   ├── server_viewmodel.dart         # LAN server lifecycle & file list
│   │   ├── sharing_viewmodel.dart        # 3-Stage file sharing state machine
│   │   └── verify_viewmodel.dart         # Verification comparator state
│   ├── views/
│   │   ├── file_server_view.dart         # Embedded server & QR code display
│   │   ├── file_sharing_view.dart        # 3-State rotary file sharing page
│   │   ├── home_view.dart                # System telemetry & transfer overview
│   │   ├── settings_view.dart            # Storage, integrity, governor & diagnostics
│   │   └── verify_view.dart              # Pairwise hash audit tool
│   └── widgets/
│       ├── circular_telemetry_gauge.dart # Radial arc gauges for Speed & CPU
│       ├── custom_progress_bar.dart      # Glowing gradient progress bar
│       ├── rotary_dial_widget.dart       # Telephone-style rotary outer ring selector
│       └── terminal_log_view.dart        # Monospace log terminal
└── main.dart                             # Application entrypoint & top nav bar
```

---

## 🚀 Running the App

### Prerequisites
- [Flutter SDK](https://flutter.dev) (v3.24.0 or newer)
- Linux desktop requirements: `clang`, `cmake`, `ninja-build`, `pkg-config`, `libgtk-3-dev`

### Run on Linux Desktop
```bash
flutter run -d linux
```

### Run on Windows
```powershell
flutter run -d windows
```

### Run on macOS
```bash
flutter run -d macos
```

### Run on Android
```bash
flutter run -d android
```

### Run Automated Tests & Static Analysis
```bash
flutter test
dart analyze
```
