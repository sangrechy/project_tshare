# 📁 FileCloud — LAN File Browser & Server

FileCloud is a simple, lightweight file-sharing server built with **Node.js and Express**. It allows devices on the same network (Wi-Fi or Ethernet LAN) to browse folders and download files through any modern web browser.

## ✨ Features

* **Folder & File Browsing:** Traverse directories with real-time breadcrumb navigation.
* **Direct File Downloads:** Fast downloads for all file types.
* **Modern Web Interface:** Clean dark-mode interface with mobile and desktop responsive views.
* **Safe Path Resolution:** Secure path validation to prevent directory traversal outside the shared root.
* **LAN Auto-Discovery (v2):** Automatically detects and prints active local IPv4 addresses for one-click access from phones, tablets, and laptops.

## 🛠️ Requirements

* [Node.js](https://nodejs.org/) (v16+ recommended)
* Any modern web browser

## 📥 Setup & Usage

### 1. Navigate to the desired version directory

From the `project_tshare` root:

```bash
# Version 2 (Recommended - auto-detects LAN IP with modern dark UI)
cd file_server_tool/v2

# Version 1 (Classic lightweight baseline)
cd file_server_tool/v1
```

### 2. Install dependencies

```bash
npm install express
```

### 3. Place files to share

Create a `files` folder in the version directory (if not already present) and place any files or folders you want to share:

```bash
mkdir files
```

### 4. Start the server

```bash
node app.js
```

The server will bind to port `3000` and display your LAN access URLs, for example:

```text
File manager running at http://localhost:3000
File manager running at http://192.168.1.X:3000
```

Open the displayed address on any client device on your local network.

## 📁 Directory Structure

```text
file_server_tool/
├── .gitignore
├── README.md
├── v1/
│   ├── app.js
│   ├── files/          # User-shared content (gitignored)
│   └── public/
│       ├── index.html
│       ├── script.js
│       └── styles.css
└── v2/
    ├── app.js
    ├── files/          # User-shared content (gitignored)
    └── public/
        ├── index.html
        ├── script.js
        └── styles.css
```

### 📌 Version Breakdown
* **v1:** Minimal file-sharing server with basic table UI.
* **v2:** Enhanced UI, breadcrumbs, search, and automatic IPv4 network interface detection.

## 🌐 External Access (Optional)

To access your file server outside your local network, you can tunnel through tools like **ngrok**:

```bash
ngrok http 3000
```

## 🔐 Security Considerations

* Only files inside the designated `files/` directory are accessible.
* The server operates in read-only mode by default; files cannot be modified or deleted through the web UI.
