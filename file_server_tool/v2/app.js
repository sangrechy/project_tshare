const express = require('express');
const path = require('path');
const fs = require('fs');
const os = require('os');

const app = express();
const PORT = 3000;

const ROOT_DIR = path.join(__dirname, 'files');

app.use(express.static(path.join(__dirname, 'public')));

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

app.get('/download', (req, res) => {
  const relPath = req.query.path;
  const absPath = path.join(ROOT_DIR, relPath);

  if (!absPath.startsWith(ROOT_DIR)) return res.status(403).send('Access denied');

  res.download(absPath);
});

app.listen(PORT, '0.0.0.0', () => {
  const interfaces = os.networkInterfaces();
  Object.values(interfaces).forEach(ifaceList => {
    ifaceList.forEach(iface => {
      if (iface.family === 'IPv4' && !iface.internal) {
        console.log(`File manager running at http://${iface.address}:${PORT}`);
      }
    });
  });
});
