import 'dart:io';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/foundation.dart';
import '../../data/models/audit_result.dart';
import '../../data/services/verify_service.dart';

class VerifyViewModel extends ChangeNotifier {
  final VerifyService _service = VerifyService();

  String? originalPath;
  String? originalName;
  int originalSize = 0;

  String? receivedPath;
  String? receivedName;
  int receivedSize = 0;

  bool isVerifying = false;
  AuditResult? result;

  Future<void> pickOriginalFile() async {
    final file = await FilePicker.pickFile();
    if (file != null && file.path != null) {
      originalPath = file.path!;
      originalName = file.name;
      final f = File(originalPath!);
      originalSize = (await file.length()) ?? (await f.exists() ? await f.length() : 0);
      result = null;
      notifyListeners();
    }
  }

  Future<void> pickReceivedFile() async {
    final file = await FilePicker.pickFile();
    if (file != null && file.path != null) {
      receivedPath = file.path!;
      receivedName = file.name;
      final f = File(receivedPath!);
      receivedSize = (await file.length()) ?? (await f.exists() ? await f.length() : 0);
      result = null;
      notifyListeners();
    }
  }

  Future<void> runVerification() async {
    if (originalPath == null || receivedPath == null || isVerifying) return;

    isVerifying = true;
    result = null;
    notifyListeners();

    try {
      result = await _service.verifyTwoFiles(originalPath!, receivedPath!);
    } catch (e) {
      result = AuditResult.error(e.toString());
    } finally {
      isVerifying = false;
      notifyListeners();
    }
  }

  void reset() {
    originalPath = null;
    originalName = null;
    originalSize = 0;
    receivedPath = null;
    receivedName = null;
    receivedSize = 0;
    result = null;
    isVerifying = false;
    notifyListeners();
  }
}
