# 🚀 Web File Sharer — Upload & Download Portal

Web File Sharer is a web application built with **Node.js, Express, and Multer** for uploading, managing, and downloading files through a clean browser-based interface.

## 🚀 Features

* **Instant File Uploads:** Upload files seamlessly with multipart stream handling.
* **Direct File Downloads:** Download shared assets directly from the repository or upload pool.
* **Responsive Web Portal:** Includes Home, Upload, and Download portals with asset previews.
* **Extensible Storage:** Easily configure upload limits and storage directories.

## 📋 Requirements

* [Node.js](https://nodejs.org/) (v16+ recommended)
* `npm` (bundled with Node.js)

## 🛠️ Setup & Installation

### 1. Navigate to the application directory

From the `project_tshare` root:

```bash
cd share_by_web_tool/v1
```

### 2. Install dependencies

```bash
npm install
```

*(Dependencies: `express`, `multer`)*

### 3. Start the server

```bash
node server.js
```

### 4. Access the web interface

Open your web browser and navigate to:

```text
http://localhost:3000
```

Or from another device on the same local network:

```text
http://<your-local-ip>:3000
```

## 📂 Directory Structure

```text
share_by_web_tool/
├── .gitignore
├── README.md
└── v1/
    ├── package.json
    ├── package-lock.json
    ├── server.js
    ├── document.pdf
    ├── uploads/           # Storage directory for uploaded user files (gitignored)
    │   └── .gitkeep
    └── public/            # Frontend static assets
        ├── home.html
        ├── main.html
        ├── upload.html
        ├── download.html
        ├── script.js
        ├── styles.css
        └── images/
            ├── ICON.png
            ├── facebook.png
            ├── instagram.png
            └── twitter.png
```

## 🛡️ Security Considerations

* Restrict public access to the `/uploads` folder to trusted networks.
* Configure maximum upload file size in `multer` options to match your storage policies.
* Consider implementing rate-limiting via `express-rate-limit` for public deployments.
