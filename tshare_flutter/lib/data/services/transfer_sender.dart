import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math';
import 'dart:typed_data';
import 'package:path/path.dart' as p;
import '../models/file_item.dart';
import 'wire_protocol.dart';
import '../../core/constants/app_constants.dart';

class TransferSender {
  Socket? _socket;
  StreamSubscription? _socketSub;
  final BytesBuilder _inBuffer = BytesBuilder();
  Completer<Map<String, dynamic>?>? _pendingJsonCompleter;
  bool _cancelRequested = false;

  String status = 'idle'; // idle, connecting, negotiating, streaming, completed, cancelled, error
  String peerName = 'Unknown';
  String peerIp = '';
  String hashMode = 'crc32'; // crc32, sha256, none
  int totalFiles = 0;
  int currentFileIndex = 0;
  String currentFileName = '';
  int totalBytes = 0;
  int transferredBytes = 0;
  double speedMbps = 0.0;
  int etaSeconds = 0;
  String errorMessage = '';

  final List<String> logs = [];
  final StreamController<void> _updateController = StreamController<void>.broadcast();
  Stream<void> get updateStream => _updateController.stream;

  bool get isActive => status == 'connecting' || status == 'negotiating' || status == 'streaming';

  void logEvent(String msg) {
    final now = DateTime.now();
    final h = now.hour.toString().padLeft(2, '0');
    final m = now.minute.toString().padLeft(2, '0');
    final s = now.second.toString().padLeft(2, '0');
    final entry = '$h:$m:$s  $msg';
    logs.add(entry);
    if (logs.length > 500) logs.removeAt(0);
    _notify();
  }

  void _notify() {
    if (!_updateController.isClosed) {
      _updateController.add(null);
    }
  }

  void cancel() {
    _cancelRequested = true;
    status = 'cancelled';
    logEvent('Transfer cancelled by user');
    try {
      if (_socket != null) {
        final cancelPacket = WireProtocol.encodeJsonPayload(AppConstants.msgCancel, 0, {'reason': 'Cancelled by user'});
        _socket?.add(cancelPacket);
        _socket?.destroy();
      }
    } catch (_) {}
    try {
      _socketSub?.cancel();
    } catch (_) {}
    _socketSub = null;
    _notify();
  }

  Future<bool> startTransfer({
    required String targetIp,
    required int targetPort,
    required List<FileItem> items,
    String hashMode = 'crc32',
  }) async {
    if (isActive) return false;

    _cancelRequested = false;
    peerIp = targetIp;
    this.hashMode = hashMode;
    status = 'connecting';
    errorMessage = '';
    logs.clear();
    logEvent('Transfer initialized');
    logEvent('Connecting to peer at $targetIp:$targetPort...');
    _notify();

    final stopwatch = Stopwatch()..start();
    final sessionId = Random().nextInt(899999) + 100000;

    try {
      _socket = await Socket.connect(targetIp, targetPort, timeout: const Duration(seconds: 10));
      _socket?.setOption(SocketOption.tcpNoDelay, true);
      logEvent('TCP connection established');

      _inBuffer.clear();
      _socketSub = _socket?.listen(
        (data) {
          _inBuffer.add(data);
          while (_inBuffer.length >= AppConstants.headerSize) {
            final currentBytes = Uint8List.fromList(_inBuffer.takeBytes());
            final header = WireProtocol.decodeHeader(currentBytes);
            if (header == null) break;
            final payloadLen = header['payloadLen']!;
            final totalLen = AppConstants.headerSize + payloadLen;
            if (currentBytes.length < totalLen) {
              _inBuffer.add(currentBytes);
              break;
            }
            final payload = currentBytes.sublist(AppConstants.headerSize, totalLen);
            if (currentBytes.length > totalLen) {
              _inBuffer.add(currentBytes.sublist(totalLen));
            }
            try {
              final json = jsonDecode(utf8.decode(payload)) as Map<String, dynamic>;
              if (_pendingJsonCompleter != null && !_pendingJsonCompleter!.isCompleted) {
                _pendingJsonCompleter!.complete(json);
              }
            } catch (_) {}
          }
        },
        onError: (err) {
          if (_pendingJsonCompleter != null && !_pendingJsonCompleter!.isCompleted) {
            _pendingJsonCompleter!.complete(null);
          }
        },
        onDone: () {
          if (_pendingJsonCompleter != null && !_pendingJsonCompleter!.isCompleted) {
            _pendingJsonCompleter!.complete(null);
          }
        },
      );

      // 1. Handshake HELLO
      status = 'negotiating';
      final helloPayload = WireProtocol.encodeJsonPayload(AppConstants.msgHello, sessionId, {
        'version': 4,
        'hostname': Platform.localHostname,
        'hash_mode': hashMode,
      });
      _socket?.add(helloPayload);

      // Await HELLO_ACK
      final ackData = await _recvJsonPacket();
      if (ackData == null || ackData['accepted'] != true) {
        throw Exception('Peer rejected connection handshake');
      }
      peerName = ackData['name'] as String? ?? 'Receiver';
      logEvent('Device verified: $peerName');

      // 2. Build Manifest
      final manifestFiles = <Map<String, dynamic>>[];
      int accumulatedBytes = 0;
      int fileIdCounter = 1;

      for (final item in items) {
        if (item.isDirectory) {
          final dir = Directory(item.path);
          if (await dir.exists()) {
            await for (final entity in dir.list(recursive: true, followLinks: false)) {
              if (entity is File) {
                final len = await entity.length();
                final relPath = p.relative(entity.path, from: p.dirname(item.path)).replaceAll('\\', '/');
                manifestFiles.add({
                  'id': fileIdCounter++,
                  'rel_path': relPath,
                  'abs_path': entity.path,
                  'size': len,
                });
                accumulatedBytes += len;
              }
            }
          }
        } else {
          final file = File(item.path);
          if (await file.exists()) {
            final len = await file.length();
            manifestFiles.add({
              'id': fileIdCounter++,
              'rel_path': item.name,
              'abs_path': item.path,
              'size': len,
            });
            accumulatedBytes += len;
          }
        }
      }

      totalFiles = manifestFiles.length;
      totalBytes = accumulatedBytes;
      transferredBytes = 0;
      logEvent('Manifest created: $totalFiles files (${(totalBytes / (1024 * 1024)).toStringAsFixed(1)} MB)');

      // Send Manifest
      final manifestClean = manifestFiles.map((f) => {
        'id': f['id'],
        'rel_path': f['rel_path'],
        'size': f['size'],
      }).toList();

      final manifestPayload = WireProtocol.encodeJsonPayload(AppConstants.msgManifest, sessionId, {
        'session_id': sessionId,
        'hash_mode': hashMode,
        'total_files': totalFiles,
        'total_bytes': totalBytes,
        'files': manifestClean,
      });
      _socket?.add(manifestPayload);

      logEvent('Awaiting receiver approval...');
      _notify();

      // Await MSG_ACCEPT
      final acceptData = await _recvJsonPacket();
      if (acceptData == null || acceptData['accepted'] != true) {
        final reason = acceptData?['reason'] ?? 'Declined by peer';
        logEvent('Transfer declined by peer: $reason');
        status = 'rejected';
        _notify();
        return false;
      }

      logEvent('Receiver accepted transfer (Integrity: ${hashMode.toUpperCase()})');
      logEvent('File transfer started');
      status = 'streaming';
      _notify();

      // 3. Stream Blocks
      int lastSpeedTime = DateTime.now().millisecondsSinceEpoch;
      int lastSpeedBytes = 0;

      for (int i = 0; i < manifestFiles.length; i++) {
        if (_cancelRequested) break;
        final fMeta = manifestFiles[i];
        final fileId = fMeta['id'] as int;
        final relPath = fMeta['rel_path'] as String;
        final absPath = fMeta['abs_path'] as String;
        final fileSize = fMeta['size'] as int;

        currentFileIndex = i + 1;
        currentFileName = relPath;
        _notify();

        final file = File(absPath);
        final raf = await file.open(mode: FileMode.read);
        final totalBlocks = (fileSize / AppConstants.blockSize).ceil();

        for (int bIdx = 0; bIdx < (totalBlocks == 0 ? 1 : totalBlocks); bIdx++) {
          if (_cancelRequested) break;

          final bLen = min(AppConstants.blockSize, fileSize - (bIdx * AppConstants.blockSize));
          final blockData = bLen > 0 ? await raf.read(bLen) : Uint8List(0);
          final chk = WireProtocol.computeBlockChecksum(blockData, hashMode);

          final bHeader = WireProtocol.encodeBlockHeader(sessionId, fileId, bIdx, blockData.length, chk);
          final pHeader = WireProtocol.encodeHeader(AppConstants.msgBlock, sessionId, bHeader.length + blockData.length);

          _socket?.add(pHeader);
          _socket?.add(bHeader);
          if (blockData.isNotEmpty) {
            _socket?.add(blockData);
          }
          await _socket?.flush();

          transferredBytes += blockData.length;

          // Speed & ETA
          final now = DateTime.now().millisecondsSinceEpoch;
          final dt = (now - lastSpeedTime) / 1000.0;
          if (dt >= 0.4) {
            final diffBytes = transferredBytes - lastSpeedBytes;
            speedMbps = (diffBytes / dt) / (1024 * 1024);
            final remBytes = max(0, totalBytes - transferredBytes);
            etaSeconds = speedMbps > 0 ? (remBytes / (speedMbps * 1024 * 1024)).toInt() : 0;
            lastSpeedTime = now;
            lastSpeedBytes = transferredBytes;
            _notify();
          }
        }
        await raf.close();

        // Send MSG_FILE_DONE
        if (!_cancelRequested) {
          final fileDonePayload = WireProtocol.encodeJsonPayload(AppConstants.msgFileDone, sessionId, {'file_id': fileId});
          _socket?.add(fileDonePayload);
          await _recvJsonPacket();
          logEvent('File sent [$currentFileIndex/$totalFiles]: $currentFileName');
          _notify();
        }
      }

      // 4. Session Done
      if (!_cancelRequested) {
        final sessionDone = WireProtocol.encodeJsonPayload(AppConstants.msgSessionDone, sessionId, {});
        _socket?.add(sessionDone);
        await _socket?.flush();

        stopwatch.stop();
        final duration = max(0.1, stopwatch.elapsedMilliseconds / 1000.0);
        final avgSpeed = (transferredBytes / duration) / (1024 * 1024);

        status = 'completed';
        logEvent('Transfer completed: $totalFiles files (${(totalBytes / (1024 * 1024)).toStringAsFixed(1)} MB) in ${duration.toStringAsFixed(1)}s (Avg ${avgSpeed.toStringAsFixed(1)} MB/s)');
        _notify();
        return true;
      } else {
        status = 'cancelled';
        _notify();
        return false;
      }
    } catch (e) {
      status = 'error';
      errorMessage = e.toString();
      logEvent('Transfer error: $e');
      _notify();
      return false;
    } finally {
      try {
        _socketSub?.cancel();
      } catch (_) {}
      _socketSub = null;
      try {
        _socket?.close();
      } catch (_) {}
      _socket = null;
    }
  }

  Future<Map<String, dynamic>?> _recvJsonPacket({Duration timeout = const Duration(seconds: 15)}) async {
    final completer = Completer<Map<String, dynamic>?>();
    _pendingJsonCompleter = completer;
    return completer.future.timeout(timeout, onTimeout: () {
      if (_pendingJsonCompleter == completer) {
        _pendingJsonCompleter = null;
      }
      return null;
    });
  }
}
