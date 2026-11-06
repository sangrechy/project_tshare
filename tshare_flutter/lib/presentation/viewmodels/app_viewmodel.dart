import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

class AppViewModel extends ChangeNotifier {
  int currentNavIndex = 0; // 0: Home, 1: File Sharing, 2: File Server, 3: Verify, 4: Settings
  String downloadDirectory = '';
  String defaultHashMode = 'crc32'; // crc32, sha256, none
  double bandwidthLimit = 0.0; // 0 = unlimited

  AppViewModel() {
    _initDefaults();
  }

  void setNavIndex(int index) {
    if (currentNavIndex != index) {
      currentNavIndex = index;
      notifyListeners();
    }
  }

  Future<void> _initDefaults() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final savedDir = prefs.getString('download_directory');
      if (savedDir != null && savedDir.isNotEmpty && await Directory(savedDir).exists()) {
        downloadDirectory = savedDir;
      } else {
        Directory? baseDir;
        try {
          baseDir = await getDownloadsDirectory();
        } catch (_) {}
        baseDir ??= await getApplicationDocumentsDirectory();
        final tshareDir = Directory(p.join(baseDir.path, 'TShare_Downloads'));
        if (!await tshareDir.exists()) {
          await tshareDir.create(recursive: true);
        }
        downloadDirectory = tshareDir.path;
      }

      defaultHashMode = prefs.getString('hash_mode') ?? 'crc32';
      bandwidthLimit = prefs.getDouble('bandwidth_limit') ?? 0.0;
    } catch (_) {
      final home = Platform.environment['HOME'] ?? Platform.environment['USERPROFILE'] ?? '.';
      downloadDirectory = p.join(home, 'Downloads', 'TShare_Downloads');
    }
    notifyListeners();
  }

  Future<void> setDownloadDirectory(String newPath) async {
    downloadDirectory = newPath;
    final dir = Directory(newPath);
    if (!await dir.exists()) {
      await dir.create(recursive: true);
    }
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('download_directory', newPath);
    } catch (_) {}
    notifyListeners();
  }

  Future<void> setHashMode(String mode) async {
    defaultHashMode = mode;
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('hash_mode', mode);
    } catch (_) {}
    notifyListeners();
  }

  Future<void> setBandwidthLimit(double limit) async {
    bandwidthLimit = limit;
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setDouble('bandwidth_limit', limit);
    } catch (_) {}
    notifyListeners();
  }
}
