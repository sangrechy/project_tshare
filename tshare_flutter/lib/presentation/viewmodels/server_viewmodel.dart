import 'dart:io';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/foundation.dart';
import '../../core/utils/network_info.dart';
import '../../data/models/file_item.dart';
import '../../data/services/lan_file_server.dart';

class ServerViewModel extends ChangeNotifier {
  final LanFileServerService _server = LanFileServerService();
  String localIp = '127.0.0.1';
  final List<FileItem> sharedFiles = [];

  bool get isRunning => _server.isRunning;
  int get port => _server.port;
  String get sharedFolder => _server.sharedFolder;
  String get uploadsFolder => _server.uploadsFolder;
  bool get allowUploads => _server.allowUploads;
  String get portalUrl => 'http://$localIp:$port/';

  ServerViewModel() {
    _init();
  }

  Future<void> _init() async {
    localIp = await NetworkInfo.getPrimaryLocalIp();
    await refreshFiles();
    notifyListeners();
  }

  Future<bool> toggleServer() async {
    if (isRunning) {
      await _server.stop();
    } else {
      localIp = await NetworkInfo.getPrimaryLocalIp();
      await _server.start();
      await refreshFiles();
    }
    notifyListeners();
    return isRunning;
  }

  Future<void> pickSharedFolder() async {
    final path = await FilePicker.getDirectoryPath();
    if (path != null && await Directory(path).exists()) {
      _server.sharedFolder = path;
      await refreshFiles();
      notifyListeners();
    }
  }

  void setAllowUploads(bool allow) {
    _server.allowUploads = allow;
    notifyListeners();
  }

  Future<void> refreshFiles() async {
    sharedFiles.clear();
    final dir = Directory(_server.sharedFolder);
    if (await dir.exists()) {
      try {
        await for (final entity in dir.list(recursive: false, followLinks: false)) {
          if (entity is File) {
            final size = await entity.length();
            final name = entity.uri.pathSegments.lastWhere((s) => s.isNotEmpty, orElse: () => 'file');
            sharedFiles.add(FileItem(
              path: entity.path,
              name: name,
              size: size,
              isDirectory: false,
            ));
          }
        }
      } catch (_) {}
    }
    notifyListeners();
  }
}
