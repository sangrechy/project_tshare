import 'dart:convert';
import 'dart:io';
import 'package:crypto/crypto.dart';
import '../models/audit_result.dart';

class VerifyService {
  /// Computes SHA-256 digest of a file chunk-by-chunk without loading all bytes into RAM
  Future<String> calculateFileSha256(String filePath, {void Function(int bytesRead, int totalBytes)? onProgress}) async {
    final file = File(filePath);
    if (!await file.exists()) {
      throw FileSystemException('File does not exist', filePath);
    }

    final totalBytes = await file.length();
    int bytesRead = 0;

    Digest? digest;
    final output = ChunkedConversionSink<Digest>.withCallback((accumulated) {
      if (accumulated.isNotEmpty) {
        digest = accumulated.single;
      }
    });
    final input = sha256.startChunkedConversion(output);

    final stream = file.openRead(0, totalBytes);
    await for (final chunk in stream) {
      input.add(chunk);
      bytesRead += chunk.length;
      if (onProgress != null && totalBytes > 0) {
        onProgress(bytesRead, totalBytes);
      }
    }
    input.close();

    return digest?.toString() ?? '';
  }

  /// Compares two files using SHA-256 and returns a detailed AuditResult
  Future<AuditResult> verifyTwoFiles(String originalPath, String receivedPath) async {
    final origFile = File(originalPath);
    final recvFile = File(receivedPath);

    if (!await origFile.exists()) {
      return AuditResult.error('Original file does not exist: $originalPath');
    }
    if (!await recvFile.exists()) {
      return AuditResult.error('Received file does not exist: $receivedPath');
    }

    final stopwatch = Stopwatch()..start();

    try {
      final origSize = await origFile.length();
      final recvSize = await recvFile.length();

      final origHash = await calculateFileSha256(originalPath);
      final recvHash = await calculateFileSha256(receivedPath);

      stopwatch.stop();
      final duration = stopwatch.elapsedMilliseconds / 1000.0;
      final match = (origHash.toLowerCase() == recvHash.toLowerCase());

      return AuditResult(
        success: true,
        match: match,
        status: match ? 'MATCH' : 'MISMATCH',
        originalPath: originalPath,
        originalName: origFile.uri.pathSegments.isNotEmpty
            ? origFile.uri.pathSegments.lastWhere((s) => s.isNotEmpty, orElse: () => 'Original')
            : 'Original',
        originalHash: origHash,
        originalSize: origSize,
        receivedPath: receivedPath,
        receivedName: recvFile.uri.pathSegments.isNotEmpty
            ? recvFile.uri.pathSegments.lastWhere((s) => s.isNotEmpty, orElse: () => 'Received')
            : 'Received',
        receivedHash: recvHash,
        receivedSize: recvSize,
        durationSec: double.parse(duration.toStringAsFixed(3)),
      );
    } catch (e) {
      return AuditResult.error('Audit calculation error: $e');
    }
  }
}
