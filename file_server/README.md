# 📁 FileCloud — Simple File Sharing Server

FileCloud is a simple file-sharing server built with **Node.js and Express**. It allows devices on the same network to browse folders and download files through a web browser.

## ✨ Features

* Browse folders and files
* Download files
* Breadcrumb navigation
* Simple dark-mode interface
* Secure file path handling
* Works on Wi-Fi or Ethernet LAN

## 🛠️ Requirements

* [Node.js](https://nodejs.org/) LTS
* A browser

## 📥 Installation

### 1. Clone the repository

```bash
git clone https://github.com/sangrechy/project_file_server.git
cd project_file_server/v2   # or v1 for earlier iteration
```

### 2. Install dependencies

```bash
npm install
```

If dependencies are not already listed in `package.json`, install them with:

```bash
npm install express multer
```

> `path`, `fs`, and `os` are built-in Node.js modules.

### 3. Create the shared folder

Create a `files` folder inside the version directory (`v2` or `v1`):

```bash
mkdir files
```

Put the files you want to share inside this folder.

## ▶️ Start the Server

Run (from the version directory, e.g. `v2/`):

```bash
node app.js
```

The server will display an address such as:

```text
File manager running at http://192.168.1.5:3000
```

Open this address in a browser on any device connected to the same network.

Example:

```text
http://192.168.1.5:3000
```

## 📁 Project Structure

```text
project_file_server/
├── v1/
│   ├── app.js
│   ├── public/
│   │   ├── index.html
│   │   ├── script.js
│   │   └── styles.css
│   └── files/
├── v2/
│   ├── app.js
│   ├── public/
│   │   ├── index.html
│   │   ├── script.js
│   │   └── styles.css
│   └── files/
├── .gitignore
├── README.md
└── LICENSE
```

### 📌 Version Breakdown
* **v1:** Initial simple file-sharing server with basic UI.
* **v2:** Enhanced modern UI and automatic local IPv4 interface detection for instant LAN access.

## 🌐 External Access

You can use **ngrok** to access the server from outside your local network.

```bash
ngrok http 3000
```

Ngrok will provide a public URL that can be opened from another network.

## 🔐 Security

* Only files inside the `files` directory are accessible.
* The server is read-only.
* Files cannot be deleted or modified through the web interface.
* File uploads are not enabled by default.

## 📜 License

This project is licensed under the **MIT License**.

## 🔗 Repository

https://github.com/sangrechy/project_file_server
