# Combined File Sharing Projects

This repository contains two independent Node.js file sharing applications. Their histories are retained under their own top-level directories, and version numbers are scoped to each project.

## Applications

### File Sharing Server

The upload and download application lives in [`file_sharing_server/`](file_sharing_server/). Its current version is `v1`.

From the repository root:

```sh
cd file_sharing_server/v1
npm install
node server.js
```

### File Server

The read-only LAN file browser lives in [`file_server/`](file_server/), with versions `v1` and `v2`.

From the repository root, choose a version and run:

```sh
cd file_server/v2
npm install express multer
node app.js
```

The application serves files placed in that version's `files/` directory. See each project's README for details and its own setup instructions.

## License

Both original projects are MIT licensed. Their original license files remain with their respective project directories.
