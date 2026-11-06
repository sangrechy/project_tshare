import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math';
import 'dart:typed_data';
import 'package:path/path.dart' as p;
import 'wire_protocol.dart';
import '../../core/constants/app_constants.dart';

class ManifestOffer {
  final int sessionId;
  final String peerName;
  final String peerIp;
  final String hashMode;
  final int totalFiles;
  final int totalBytes;
  final List<Map<String, dynamic>> files;
  final Completer<bool> decisionCompleter;

  ManifestOffer({
    required this.sessionId,
    required this.peerName,
    required this.peerIp,
    required this.hashMode,
    required this.totalFiles,
    required this.totalBytes,
    required this.files,
    required this.decisionCompleter,
  });

  void accept() {
    if (!decisionCompleter.isCompleted) {
      decisionCompleter.complete(true);
    }
  }

  void decline([String reason = 'Transfer declined by receiver']) {
    if (!decisionCompleter.isCompleted) {
      decisionCompleter.complete(false);
    }
  }
}

class TransferReceiver {
  ServerSocket? _serverSocket;
  Socket? _currentSocket;
  bool _cancelRequested = false;

  String downloadDirectory = '';
  String status = 'idle'; // idle, listening, negotiating, streaming, completed, cancelled, error
  String peerName = 'Unknown';
  String peerIp = '';
  String hashMode = 'crc32';
  int totalFiles = 0;
  int currentFileIndex = 0;
  String currentFileName = '';
  int totalBytes = 0;
  int transferredBytes = 0;
  double speedMbps = 0.0;
  int etaSeconds = 0;
  String errorMessage = '';

  ManifestOffer? pendingOffer;
  void Function(ManifestOffer offer)? onOfferReceived;

  final List<String> logs = [];
  final StreamController<void> _updateController = StreamController<void>.broadcast();
  Stream<void> get updateStream => _updateController.stream;

  bool get isListening => _serverSocket != null;
  bool get isActive => status == 'negotiating' || status == 'streaming';

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

  Future<bool> startServer({int port = AppConstants.tcpTransferPort, required String saveDir}) async {
    if (_serverSocket != null) return true;
    downloadDirectory = saveDir;
    try {
      _serverSocket = await ServerSocket.bind(InternetAddress.anyIPv4, port, shared: true);
      status = 'listening';
      logEvent('Receiver listening on port $port');
      _notify();

      _serverSocket?.listen(
        _handleClientConnection,
        onError: (err) {
          logEvent('Server socket error: $err');
          status = 'error';
          _notify();
        },
      );
      return true;
    } catch (e) {
      status = 'error';
      errorMessage = e.toString();
      logEvent('Failed to bind receiver socket on port $port: $e');
      _notify();
      return false;
    }
  }

  Future<void> stopServer() async {
    cancel();
    try {
      await _serverSocket?.close();
    } catch (_) {}
    _serverSocket = null;
    status = 'idle';
    logEvent('Receiver server stopped');
    _notify();
  }

  void cancel() {
    _cancelRequested = true;
    status = 'cancelled';
    logEvent('Transfer cancelled');
    try {
      _currentSocket?.destroy();
    } catch (_) {}
    _currentSocket = null;
    pendingOffer?.decline('Cancelled by receiver');
    pendingOffer = null;
    _notify();
  }

  Future<void> _handleClientConnection(Socket socket) async {
    if (isActive) {
      // Busy with another active transfer
      final busyPacket = WireProtocol.encodeJsonPayload(AppConstants.msgCancel, 0, {'reason': 'Receiver busy'});
      socket.add(busyPacket);
      await socket.flush();
      socket.destroy();
      return;
    }

    _currentSocket = socket;
    _cancelRequested = false;
    peerIp = socket.remoteAddress.address;
    logEvent('Incoming connection from $peerIp');
    _notify();

    final stopwatch = Stopwatch();
    final stagingDir = Directory(p.join(downloadDirectory, '.tshare_staging'));
    if (!await stagingDir.exists()) {
      await stagingDir.create(recursive: true);
    }

    final buffer = BytesBuilder();

    // Transfer session state
    Map<int, Map<String, dynamic>> manifestMap = {};
    RandomAccessFile? currentFileRaf;
    String? currentStagingPath;
    String? currentFinalPath;

    int lastSpeedTime = DateTime.now().millisecondsSinceEpoch;
    int lastSpeedBytes = 0;

    try {
      await for (final data in socket) {
        if (_cancelRequested) {
          socket.destroy();
          break;
        }
        buffer.add(data);

        // Process all complete frames currently in buffer
        while (buffer.length >= AppConstants.headerSize) {
          if (_cancelRequested) {
            socket.destroy();
            break;
          }
          final rawBytes = Uint8List.fromList(buffer.takeBytes());
          final header = WireProtocol.decodeHeader(rawBytes);
          if (header == null) {
            // Malformed frame header
            logEvent('Corrupted frame header received from $peerIp');
            socket.destroy();
            break;
          }

          final msgType = header['msgType']!;
          final sessionId = header['sessionId']!;
          final payloadLen = header['payloadLen']!;
          final totalFrameLen = AppConstants.headerSize + payloadLen;

          if (rawBytes.length < totalFrameLen) {
            // Re-insert uncompleted bytes back to buffer
            buffer.add(rawBytes);
            break;
          }

          // Extract current packet payload
          final payload = rawBytes.sublist(AppConstants.headerSize, totalFrameLen);
          // Leftover bytes go back to buffer
          if (rawBytes.length > totalFrameLen) {
            buffer.add(rawBytes.sublist(totalFrameLen));
          }

          // Process packet by msgType
          if (msgType == AppConstants.msgHello) {
            try {
              final json = jsonDecode(utf8.decode(payload)) as Map<String, dynamic>;
              peerName = json['hostname'] as String? ?? 'Sender';
              hashMode = json['hash_mode'] as String? ?? 'crc32';
              logEvent('Handshake from $peerName (Hash mode: ${hashMode.toUpperCase()})');

              final ack = WireProtocol.encodeJsonPayload(AppConstants.msgHelloAck, sessionId, {
                'accepted': true,
                'name': Platform.localHostname,
              });
              socket.add(ack);
              await socket.flush();
            } catch (e) {
              logEvent('Error decoding HELLO: $e');
            }
          } else if (msgType == AppConstants.msgManifest) {
            try {
              final json = jsonDecode(utf8.decode(payload)) as Map<String, dynamic>;
              hashMode = json['hash_mode'] as String? ?? hashMode;
              totalFiles = json['total_files'] as int? ?? 0;
              totalBytes = json['total_bytes'] as int? ?? 0;
              transferredBytes = 0;

              final filesList = (json['files'] as List<dynamic>? ?? []).cast<Map<String, dynamic>>();
              manifestMap = {for (var f in filesList) (f['id'] as int): f};

              logEvent('Incoming manifest: $totalFiles files (${(totalBytes / (1024 * 1024)).toStringAsFixed(1)} MB)');
              status = 'negotiating';
              _notify();

              // Prompt user or auto-accept
              bool accepted = true;
              if (onOfferReceived != null) {
                final offer = ManifestOffer(
                  sessionId: sessionId,
                  peerName: peerName,
                  peerIp: peerIp,
                  hashMode: hashMode,
                  totalFiles: totalFiles,
                  totalBytes: totalBytes,
                  files: filesList,
                  decisionCompleter: Completer<bool>(),
                );
                pendingOffer = offer;
                onOfferReceived!(offer);
                _notify();
                accepted = await offer.decisionCompleter.future;
                pendingOffer = null;
              }

              if (accepted) {
                logEvent('Accepted transfer offer from $peerName');
                final acceptPacket = WireProtocol.encodeJsonPayload(AppConstants.msgAccept, sessionId, {
                  'accepted': true,
                });
                socket.add(acceptPacket);
                await socket.flush();

                status = 'streaming';
                stopwatch.start();
                _notify();
              } else {
                logEvent('Declined transfer offer from $peerName');
                final declinePacket = WireProtocol.encodeJsonPayload(AppConstants.msgAccept, sessionId, {
                  'accepted': false,
                  'reason': 'Declined by receiver',
                });
                socket.add(declinePacket);
                await socket.flush();
                status = 'listening';
                _notify();
              }
            } catch (e) {
              logEvent('Error processing manifest: $e');
            }
          } else if (msgType == AppConstants.msgBlock) {
            if (payload.length < AppConstants.blockHeaderSize) {
              logEvent('Invalid block payload size');
              continue;
            }

            final bHeaderBytes = payload.sublist(0, AppConstants.blockHeaderSize);
            final bDataBytes = payload.sublist(AppConstants.blockHeaderSize);
            final bHeader = WireProtocol.decodeBlockHeader(bHeaderBytes);

            if (bHeader != null) {
              final fileId = bHeader['fileId']!;
              final blockIndex = bHeader['blockIndex']!;
              final declaredSize = bHeader['blockSize']!;
              final checksum = bHeader['checksum'] as Uint8List;

              if (bDataBytes.length != declaredSize) {
                logEvent('Corrupted block length: expected $declaredSize, got ${bDataBytes.length}');
                continue;
              }

              // Check integrity
              if (hashMode != 'none') {
                final computedChk = WireProtocol.computeBlockChecksum(bDataBytes, hashMode);
                bool valid = true;
                if (checksum.length == computedChk.length) {
                  for (int i = 0; i < checksum.length; i++) {
                    if (checksum[i] != computedChk[i]) {
                      valid = false;
                      break;
                    }
                  }
                } else {
                  valid = false;
                }

                if (!valid) {
                  logEvent('Checksum MISMATCH at block $blockIndex for file #$fileId! Aborting.');
                  socket.destroy();
                  status = 'error';
                  errorMessage = 'Block checksum mismatch';
                  _notify();
                  return;
                }
              }

              // Manage target file handle
              final fMeta = manifestMap[fileId];
              final relPath = fMeta?['rel_path'] as String? ?? 'file_$fileId.bin';

              if (currentFileRaf == null || currentFileName != relPath) {
                if (currentFileRaf != null) {
                  await currentFileRaf.close();
                }
                currentFileName = relPath;
                currentFileIndex = fileId;

                currentStagingPath = p.join(stagingDir.path, '${sessionId}_$fileId.part');
                currentFinalPath = p.join(downloadDirectory, relPath);

                final partFile = File(currentStagingPath);
                currentFileRaf = await partFile.open(mode: FileMode.write);
              }

              if (bDataBytes.isNotEmpty) {
                await currentFileRaf.writeFrom(bDataBytes);
                transferredBytes += bDataBytes.length;
              }

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
          } else if (msgType == AppConstants.msgFileDone) {
            if (currentFileRaf != null) {
              await currentFileRaf.close();
              currentFileRaf = null;
            }

            if (currentStagingPath != null && currentFinalPath != null) {
              final finalFile = File(currentFinalPath);
              final parentDir = Directory(p.dirname(currentFinalPath));
              if (!await parentDir.exists()) {
                await parentDir.create(recursive: true);
              }
              if (await finalFile.exists()) {
                await finalFile.delete();
              }
              final partFile = File(currentStagingPath);
              if (await partFile.exists()) {
                await partFile.rename(currentFinalPath);
              }
            }

            logEvent('File saved [$currentFileIndex/$totalFiles]: $currentFileName');

            // Send ACK
            final ack = WireProtocol.encodeJsonPayload(AppConstants.msgFileDoneAck, sessionId, {'status': 'ok'});
            socket.add(ack);
            await socket.flush();
            _notify();
          } else if (msgType == AppConstants.msgSessionDone) {
            stopwatch.stop();
            final duration = max(0.1, stopwatch.elapsedMilliseconds / 1000.0);
            final avgSpeed = (transferredBytes / duration) / (1024 * 1024);

            status = 'completed';
            logEvent('Transfer session finished: $totalFiles files in ${duration.toStringAsFixed(1)}s (Avg ${avgSpeed.toStringAsFixed(1)} MB/s)');
            _notify();
          } else if (msgType == AppConstants.msgCancel) {
            logEvent('Transfer cancelled by peer');
            status = 'cancelled';
            _notify();
          }
        }
      }
    } catch (e) {
      logEvent('Connection error: $e');
      status = 'error';
      errorMessage = e.toString();
      _notify();
    } finally {
      if (currentFileRaf != null) {
        try {
          await currentFileRaf.close();
        } catch (_) {}
        currentFileRaf = null;
      }
    }
    _currentSocket = null;
    if (status == 'completed' || status == 'cancelled' || status == 'error') {
      // Return to listening state after a brief moment if server is still up
      Future.delayed(const Duration(seconds: 4), () {
        if (_serverSocket != null && (status == 'completed' || status == 'cancelled')) {
          status = 'listening';
          _notify();
        }
      });
    }
  }
}
