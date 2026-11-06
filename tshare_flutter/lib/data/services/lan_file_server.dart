import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:path/path.dart' as p;
import '../../core/constants/app_constants.dart';

class LanFileServerService {
  HttpServer? _server;
  String sharedFolder = '';
  String uploadsFolder = '';
  bool allowUploads = true;
  int port = AppConstants.portalPort;

  bool get isRunning => _server != null;

  LanFileServerService() {
    _initDefaultFolders();
  }

  Future<void> _initDefaultFolders() async {
    final home = Platform.environment['HOME'] ?? Platform.environment['USERPROFILE'] ?? '.';
    sharedFolder = p.join(home, 'Downloads', 'TShare_Shared');
    uploadsFolder = p.join(home, 'Downloads', 'TShare_Uploads');
    try {
      await Directory(sharedFolder).create(recursive: true);
      await Directory(uploadsFolder).create(recursive: true);
    } catch (_) {}
  }

  Future<bool> start() async {
    if (isRunning) return true;
    try {
      _server = await HttpServer.bind(InternetAddress.anyIPv4, port);
      _server?.listen(_handleRequest);
      return true;
    } catch (e) {
      // Port in use, try next ports
      for (int i = 1; i <= 5; i++) {
        try {
          _server = await HttpServer.bind(InternetAddress.anyIPv4, port + i);
          port += i;
          _server?.listen(_handleRequest);
          return true;
        } catch (_) {}
      }
      return false;
    }
  }

  Future<void> stop() async {
    await _server?.close(force: true);
    _server = null;
  }

  Future<void> _handleRequest(HttpRequest request) async {
    // Enable CORS
    request.response.headers.add('Access-Control-Allow-Origin', '*');
    request.response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    request.response.headers.add('Access-Control-Allow-Headers', 'Content-Type');

    if (request.method == 'OPTIONS') {
      request.response.statusCode = HttpStatus.ok;
      await request.response.close();
      return;
    }

    final path = request.uri.path;

    if (path == '/api/info') {
      _sendJson(request, {
        'hostname': Platform.localHostname,
        'shared_folder': sharedFolder,
        'allow_uploads': allowUploads,
        'os': Platform.operatingSystem,
      });
      return;
    }

    if (path == '/api/list') {
      await _handleList(request);
      return;
    }

    if (path == '/api/download') {
      await _handleDownload(request);
      return;
    }

    if (path == '/api/upload' && request.method == 'POST') {
      await _handleUpload(request);
      return;
    }

    // Default: Serve responsive mobile-friendly HTML Web Portal
    _servePortalHtml(request);
  }

  Future<void> _handleList(HttpRequest request) async {
    final dir = Directory(sharedFolder);
    final items = <Map<String, dynamic>>[];

    if (await dir.exists()) {
      await for (final entity in dir.list(followLinks: false)) {
        if (entity is File) {
          final stat = await entity.stat();
          items.add({
            'name': p.basename(entity.path),
            'size': stat.size,
            'is_dir': false,
            'modified': stat.modified.toIso8601String(),
          });
        }
      }
    }

    _sendJson(request, {'success': true, 'items': items});
  }

  Future<void> _handleDownload(HttpRequest request) async {
    final filename = request.uri.queryParameters['file'];
    if (filename == null || filename.contains('..')) {
      request.response.statusCode = HttpStatus.badRequest;
      request.response.write('Invalid file');
      await request.response.close();
      return;
    }

    final file = File(p.join(sharedFolder, filename));
    if (!await file.exists()) {
      request.response.statusCode = HttpStatus.notFound;
      request.response.write('File not found');
      await request.response.close();
      return;
    }

    final length = await file.length();
    request.response.headers.contentType = ContentType.binary;
    request.response.headers.set(
      'Content-Disposition',
      'attachment; filename="${Uri.encodeComponent(filename)}"',
    );
    request.response.headers.contentLength = length;

    await file.openRead().pipe(request.response);
  }

  Future<void> _handleUpload(HttpRequest request) async {
    if (!allowUploads) {
      _sendJson(request, {'success': false, 'error': 'Uploads disabled by host'}, status: HttpStatus.forbidden);
      return;
    }

    final filename = request.uri.queryParameters['name'] ?? 'upload_${DateTime.now().millisecondsSinceEpoch}.bin';
    if (filename.contains('..')) {
      _sendJson(request, {'success': false, 'error': 'Invalid file name'}, status: HttpStatus.badRequest);
      return;
    }

    final targetPath = p.join(uploadsFolder, filename);
    final file = File(targetPath);
    final sink = file.openWrite();

    try {
      await sink.addStream(request);
      await sink.close();
      _sendJson(request, {'success': true, 'filename': filename});
    } catch (e) {
      await sink.close();
      _sendJson(request, {'success': false, 'error': e.toString()}, status: HttpStatus.internalServerError);
    }
  }

  void _sendJson(HttpRequest request, Map<String, dynamic> data, {int status = HttpStatus.ok}) {
    request.response.statusCode = status;
    request.response.headers.contentType = ContentType.json;
    request.response.write(jsonEncode(data));
    request.response.close();
  }

  void _servePortalHtml(HttpRequest request) {
    request.response.statusCode = HttpStatus.ok;
    request.response.headers.contentType = ContentType.html;
    request.response.write('''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>TShare Mobile LAN Portal</title>
  <style>
    body { font-family: -apple-system, sans-serif; background: #0b0f19; color: #f3f4f6; margin: 0; padding: 20px; }
    .card { background: #111827; border: 1px solid #1e293b; border-radius: 12px; padding: 18px; margin-bottom: 16px; }
    h2, h3 { margin: 0 0 10px; color: #38bdf8; }
    .btn { background: #3b82f6; color: white; border: none; padding: 10px 18px; border-radius: 6px; font-weight: bold; cursor: pointer; text-decoration: none; display: inline-block; }
    .file-item { display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid #1e293b; }
    .upload-box { border: 2px dashed #38bdf8; padding: 20px; text-align: center; border-radius: 8px; margin-top: 10px; }
  </style>
</head>
<body>
  <h2>TShare LAN File Portal</h2>
  <p>Connected to <strong>${Platform.localHostname}</strong></p>
  <div class="card">
    <h3>Shared Files (Download)</h3>
    <div id="fileList">Loading files...</div>
  </div>
  <div class="card">
    <h3>Upload File to PC</h3>
    <input type="file" id="uploadInput" style="display:none" onchange="uploadFile(this.files[0])">
    <div class="upload-box" onclick="document.getElementById('uploadInput').click()">
      Tap here to choose and send file
    </div>
    <div id="uploadStatus" style="margin-top: 10px; font-size: 13px; color: #10b981;"></div>
  </div>
  <script>
    async function loadFiles() {
      try {
        const res = await fetch('/api/list');
        const data = await res.json();
        const container = document.getElementById('fileList');
        if (!data.items || data.items.length === 0) {
          container.innerHTML = '<p style="color:#64748b">No files in shared folder.</p>';
          return;
        }
        container.innerHTML = data.items.map(f => `
          <div class="file-item">
            <span>\${f.name} (\${(f.size / (1024*1024)).toFixed(1)} MB)</span>
            <a class="btn" href="/api/download?file=\${encodeURIComponent(f.name)}">Download</a>
          </div>
        `).join('');
      } catch (e) {
        document.getElementById('fileList').textContent = 'Error loading files';
      }
    }
    async function uploadFile(file) {
      if (!file) return;
      const status = document.getElementById('uploadStatus');
      status.textContent = 'Uploading ' + file.name + '...';
      try {
        const res = await fetch('/api/upload?name=' + encodeURIComponent(file.name), {
          method: 'POST',
          body: file
        });
        const d = await res.json();
        status.textContent = d.success ? 'Uploaded successfully!' : ('Upload failed: ' + d.error);
        loadFiles();
      } catch (err) {
        status.textContent = 'Upload error: ' + err;
      }
    }
    loadFiles();
  </script>
</body>
</html>''');
    request.response.close();
  }
}
