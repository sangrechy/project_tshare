const express = require('express');
const path = require('path');
const fs = require('fs');

const app = express();
const PORT = 3000;

// Folder to expose
const ROOT_DIR = path.join(__dirname, 'files');

// Serve frontend files
app.use(express.static(path.join(__dirname, 'public')));

// API to list files/folders
app.get('/api/list', (req, res) => {
  const relPath = req.query.path || '';
  const absPath = path.join(ROOT_DIR, relPath);

  if (!absPath.startsWith(ROOT_DIR)) return res.status(403).send('Access denied');

  fs.readdir(absPath, { withFileTypes: true }, (err, entries) => {
    if (err) return res.status(500).send('Unable to read directory');

    const items = entries.map(entry => ({
      name: entry.name,
      isDir: entry.isDirectory()
    }));

    res.json({ currentPath: relPath, items });
  });
});

// Download route
app.get('/download', (req, res) => {
  const relPath = req.query.path;
  const absPath = path.join(ROOT_DIR, relPath);

  if (!absPath.startsWith(ROOT_DIR)) return res.status(403).send('Access denied');

  res.download(absPath);
});

// Start server and listen on all interfaces
app.listen(PORT, '0.0.0.0', () => {
  console.log(`File manager running at http://localhost:${PORT}`);
});
