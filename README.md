# project_tshare

A unified suite of file-sharing and transfer tools providing web-based portals, LAN file browsing, and high-speed direct Ethernet replication with cryptographic verification.

---

## 🧰 Tools Overview

The repository unites three specialized tools:

| Tool | Core Technology | Primary Use Case |
| :--- | :--- | :--- |
| [**`share_by_web_tool/`**](share_by_web_tool/) | Node.js, Express, Multer | Browser-based file sharing portal for uploading, downloading, and managing files across devices. |
| [**`file_server_tool/`**](file_server_tool/) | Node.js, Express | Lightweight read-only LAN file server with automatic IP detection and folder navigation. |
| [**`share_by_ethernet_tool/`**](share_by_ethernet_tool/) | Python, PyWebView, Robocopy | High-speed direct Ethernet / LAN sync with kernel I/O telemetry, safe resume, and multi-level cryptographic SHA-256 verification. |

---

## 📂 Repository Structure

```text
project_tshare/
├── README.md                      # Unified repository guide (this file)
├── .gitignore                     # Root gitignore
├── share_by_web_tool/             # Tool 1: Browser-based Upload & Download Server
│   ├── .gitignore
│   ├── README.md
│   └── v1/
│       ├── package.json
│       ├── package-lock.json
│       ├── server.js
│       ├── document.pdf
│       ├── uploads/               # Destination for uploaded files
│       │   └── .gitkeep
│       └── public/                # Web interface assets
│           ├── home.html
│           ├── main.html
│           ├── upload.html
│           ├── download.html
│           ├── script.js
│           ├── styles.css
│           └── images/
├── file_server_tool/              # Tool 2: Local Network File Browser & Server
│   ├── .gitignore
│   ├── README.md
│   ├── v1/                        # Baseline LAN file server
│   │   ├── app.js
│   │   └── public/
│   └── v2/                        # Enhanced UI with automatic LAN IPv4 detection
│       ├── app.js
│       └── public/
└── share_by_ethernet_tool/        # Tool 3: Direct Ethernet / LAN Robocopy Cockpit & Verifier
    ├── .gitignore
    ├── README.md
    └── v1/
        ├── app.py                 # Robocopy Dual-Deck Transfer Monitor (PyWebView)
        ├── tkinter_app.py         # Tkinter dark fallback Transfer Monitor
        ├── verify_app.py          # Transaction Deep Verifier (PyWebView)
        ├── verify_tkinter.py      # Tkinter dark fallback Deep Verifier
        ├── backend/
        │   ├── transfer_engine.py # Kernel I/O speed counters & Robocopy engine
        │   └── verify_engine.py   # Cryptographic SHA-256 & bit-by-bit auditor
        ├── ui/                    # Transfer Cockpit Neumorphic UI
        └── ui_verify/             # Deep Verifier Neumorphic UI
```

---

## 🚀 Quick Start Guide

### 1. Web File Sharer (`share_by_web_tool`)
Ideal for sharing files between phones, laptops, and PCs via a standard web browser.

```bash
cd share_by_web_tool/v1
npm install
node server.js
```
Open **`http://localhost:3000`** in your browser.

---

### 2. LAN File Browser (`file_server_tool`)
Ideal for exposing a folder of files to everyone on your Wi-Fi or Ethernet network.

```bash
# Recommended: Version 2 with auto LAN IP detection
cd file_server_tool/v2
npm install express
node app.js
```
Place files inside `file_server_tool/v2/files/` and navigate to the printed LAN URL (e.g. `http://<your-ip>:3000`).

---

### 3. Ethernet File Transfer & Deep Verifier (`share_by_ethernet_tool`)
Ideal for migrating massive directories over a direct Ethernet cable or Gigabit LAN with maximum hardware throughput and complete cryptographic certainty.

```powershell
cd share_by_ethernet_tool/v1
pip install pywebview

# Launch Dual-Deck Robocopy Transfer Monitor
python app.py

# Launch Transaction Deep Verifier (SHA-256 bit-by-bit audit)
python verify_app.py

# Optional: Run with Tkinter dark fallback
python app.py --tk
python verify_app.py --tk
```

---

## 🔒 Security & Privacy Notes

* All tools operate locally on your private network by default.
* For internet exposure via tunnels (e.g. ngrok), configure proper authentication and rate-limiting.
