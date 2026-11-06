import 'dart:async';
import 'dart:io';
import 'dart:math';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/foundation.dart';
import '../../core/constants/app_constants.dart';
import '../../data/models/file_item.dart';
import '../../data/models/peer_device.dart';
import '../../data/services/peer_discovery.dart';
import '../../data/services/transfer_receiver.dart';
import '../../data/services/transfer_sender.dart';

class SharingViewModel extends ChangeNotifier {
  // Navigation stage: 1 = Rotary, 2 = Connection, 3 = Dashboard
  int stage = 1;

  // State 1: Rotary Selection
  String selectedAction = 'SEND'; // 'SEND' or 'RECEIVE'
  String selectedConnection = 'WIFI'; // 'WIFI', 'BLE', 'ETHERNET'
  double rotaryAngle = 0.0;

  // State 2: Device Connection & File Selection
  bool isAutoDiscovering = false;
  final List<PeerDevice> discoveredDevices = [];
  String manualIp = '';
  int manualPort = AppConstants.tcpTransferPort;
  PeerDevice? targetDevice;
  final List<FileItem> selectedFiles = [];

  // Services
  final TransferSender sender = TransferSender();
  final TransferReceiver receiver = TransferReceiver();
  final PeerDiscoveryService discovery = PeerDiscoveryService();

  StreamSubscription? _senderSub;
  StreamSubscription? _receiverSub;
  StreamSubscription? _discoverySub;
  Timer? _cpuTicker;

  // Live telemetry for State 3
  double currentCpuPercent = 12.0;

  SharingViewModel() {
    _senderSub = sender.updateStream.listen((_) => notifyListeners());
    _receiverSub = receiver.updateStream.listen((_) {
      if (receiver.status == 'streaming' && stage == 2) {
        stage = 3;
      }
      notifyListeners();
    });
    _discoverySub = discovery.peersStream.listen((peers) {
      discoveredDevices.clear();
      discoveredDevices.addAll(peers);
      notifyListeners();
    });

    // Simulate realistic hardware CPU load indicator during active transfer
    _cpuTicker = Timer.periodic(const Duration(milliseconds: 800), (_) {
      if (isTransferring) {
        final speedRatio = min(1.0, currentSpeedMbps / 150.0);
        currentCpuPercent = (15.0 + (speedRatio * 45.0) + (Random().nextDouble() * 6.0));
        notifyListeners();
      } else {
        if (currentCpuPercent > 8.0) {
          currentCpuPercent = max(4.0, currentCpuPercent * 0.85);
          notifyListeners();
        }
      }
    });
  }

  @override
  void dispose() {
    _senderSub?.cancel();
    _receiverSub?.cancel();
    _discoverySub?.cancel();
    _cpuTicker?.cancel();
    discovery.stop();
    receiver.stopServer();
    super.dispose();
  }

  // --- State 1 Actions ---
  void selectAction(String action) {
    selectedAction = action;
    rotaryAngle = (action == 'SEND') ? -0.25 : -0.75;
    notifyListeners();
  }

  void selectConnection(String conn) {
    selectedConnection = conn;
    if (conn == 'WIFI') rotaryAngle = 0.15;
    if (conn == 'BLE') rotaryAngle = 0.65;
    if (conn == 'ETHERNET') rotaryAngle = 1.15;
    notifyListeners();
  }

  void confirmRotarySelection(String saveDir) {
    stage = 2;
    if (selectedAction == 'RECEIVE') {
      startReceiverServer(saveDir);
    } else {
      startAutoDiscovery();
    }
    notifyListeners();
  }

  // --- State 2 Actions ---
  void startAutoDiscovery() {
    isAutoDiscovering = true;
    discoveredDevices.clear();
    discovery.start(tcpPort: AppConstants.tcpTransferPort);
    notifyListeners();
  }

  void stopAutoDiscovery() {
    isAutoDiscovering = false;
    discovery.stop();
    notifyListeners();
  }

  void selectDevice(PeerDevice device) {
    targetDevice = device;
    manualIp = device.ip;
    manualPort = device.port;
    notifyListeners();
  }

  void setManualIp(String ip) {
    manualIp = ip;
    notifyListeners();
  }

  void setLocalhostIp() {
    manualIp = '127.0.0.1';
    notifyListeners();
  }

  void addTestPayload() {
    final tempDir = Directory.systemTemp.path;
    final testFilePath = '$tempDir/tshare_fedora_sample.txt';
    final testFile = File(testFilePath);
    if (!testFile.existsSync()) {
      testFile.writeAsStringSync(
        '=== T-SHARE FEDORA P2P DEMO PAYLOAD ===\n'
        'High-performance direct local peer-to-peer file transfer.\n'
        'Protocol: Streamlined TCP framed blocks with CRC32/Blake3 verification.\n'
        '${'TEST DATA BLOCK 0123456789 ABCDEFGHIJKLMNOPQRSTUVWXYZ\n' * 500}',
      );
    }
    final size = testFile.existsSync() ? testFile.lengthSync() : 25600;
    selectedFiles.add(FileItem(
      path: testFilePath,
      name: 'tshare_fedora_sample.txt',
      size: size,
      isDirectory: false,
    ));
    notifyListeners();
  }

  void simulateTestOffer() {
    final completer = Completer<bool>();
    completer.future.then((accepted) {
      if (accepted) {
        receiver.logEvent('Incoming test offer accepted by receiver.');
      } else {
        receiver.logEvent('Incoming test offer declined by receiver.');
      }
      receiver.pendingOffer = null;
      notifyListeners();
    });

    final offer = ManifestOffer(
      sessionId: 9999,
      peerName: 'Fedora-Workstation (Test Peer)',
      peerIp: '127.0.0.1',
      hashMode: 'crc32',
      totalFiles: 2,
      totalBytes: 25 * 1024 * 1024,
      files: [
        {'name': 'document_archive.tar.gz', 'size': 20 * 1024 * 1024},
        {'name': 'system_report.pdf', 'size': 5 * 1024 * 1024},
      ],
      decisionCompleter: completer,
    );
    receiver.pendingOffer = offer;
    notifyListeners();
  }

  Future<void> pickFiles() async {
    try {
      final files = await FilePicker.pickFiles();
      if (files.isNotEmpty) {
        for (final f in files) {
          final filePath = f.path ?? f.name;
          int size = f.lengthSync() ?? 0;
          if (size <= 0) {
            size = (await f.length()) ?? 0;
          }
          if (size <= 0 && f.path != null) {
            final file = File(f.path!);
            if (await file.exists()) {
              size = await file.length();
            }
          }
          selectedFiles.add(FileItem(
            path: filePath,
            name: f.name,
            size: size > 0 ? size : 1024,
            isDirectory: false,
          ));
        }
        notifyListeners();
      }
    } catch (e) {
      debugPrint('File picker error: $e');
    }
  }

  Future<bool> addManualFilePath(String inputPath) async {
    final trimmed = inputPath.trim();
    if (trimmed.isEmpty) return false;

    try {
      final file = File(trimmed);
      if (await file.exists()) {
        final size = await file.length();
        selectedFiles.add(FileItem(
          path: trimmed,
          name: file.uri.pathSegments.lastWhere((s) => s.isNotEmpty, orElse: () => 'file'),
          size: size,
          isDirectory: false,
        ));
        notifyListeners();
        return true;
      }

      final dir = Directory(trimmed);
      if (await dir.exists()) {
        int dirSize = 0;
        await for (final entity in dir.list(recursive: true, followLinks: false)) {
          if (entity is File) {
            dirSize += await entity.length();
          }
        }
        selectedFiles.add(FileItem(
          path: trimmed,
          name: dir.uri.pathSegments.reversed.skip(1).firstOrNull ?? 'Folder',
          size: dirSize,
          isDirectory: true,
        ));
        notifyListeners();
        return true;
      }

      // Allow adding path even if mock/virtual
      selectedFiles.add(FileItem(
        path: trimmed,
        name: trimmed.split('/').last,
        size: 1048576,
        isDirectory: false,
      ));
      notifyListeners();
      return true;
    } catch (_) {
      return false;
    }
  }

  Future<void> pickDirectory() async {
    try {
      final path = await FilePicker.getDirectoryPath();
      if (path != null) {
        final dir = Directory(path);
        if (await dir.exists()) {
          int dirSize = 0;
          await for (final entity in dir.list(recursive: true, followLinks: false)) {
            if (entity is File) {
              dirSize += await entity.length();
            }
          }
          selectedFiles.add(FileItem(
            path: path,
            name: dir.uri.pathSegments.reversed.skip(1).firstOrNull ?? 'Folder',
            size: dirSize,
            isDirectory: true,
          ));
          notifyListeners();
        }
      }
    } catch (e) {
      debugPrint('Directory picker error: $e');
    }
  }

  void removeFile(int index) {
    if (index >= 0 && index < selectedFiles.length) {
      selectedFiles.removeAt(index);
      notifyListeners();
    }
  }

  void clearFiles() {
    selectedFiles.clear();
    notifyListeners();
  }

  Future<void> startReceiverServer(String saveDir) async {
    receiver.onOfferReceived = (offer) {
      notifyListeners();
    };
    await receiver.startServer(port: AppConstants.tcpTransferPort, saveDir: saveDir);
    discovery.start(tcpPort: AppConstants.tcpTransferPort);
    notifyListeners();
  }

  Future<void> initiateSendTransfer({required String hashMode}) async {
    final ip = manualIp.trim().isNotEmpty ? manualIp.trim() : targetDevice?.ip;
    if (ip == null || ip.isEmpty || selectedFiles.isEmpty) return;

    stage = 3;
    notifyListeners();

    await sender.startTransfer(
      targetIp: ip,
      targetPort: manualPort,
      items: selectedFiles,
      hashMode: hashMode,
    );
    notifyListeners();
  }

  void cancelTransfer() {
    if (selectedAction == 'SEND') {
      sender.cancel();
    } else {
      receiver.cancel();
    }
    notifyListeners();
  }

  void resetToRotary() {
    stopAutoDiscovery();
    selectedFiles.clear();
    targetDevice = null;
    stage = 1;
    notifyListeners();
  }

  // --- Getters for UI State 3 ---
  bool get isTransferring => sender.isActive || receiver.isActive;
  bool get isCompleted => (selectedAction == 'SEND' ? sender.status : receiver.status) == 'completed';
  bool get isCancelled => (selectedAction == 'SEND' ? sender.status : receiver.status) == 'cancelled';
  bool get isError => (selectedAction == 'SEND' ? sender.status : receiver.status) == 'error';

  double get currentSpeedMbps => selectedAction == 'SEND' ? sender.speedMbps : receiver.speedMbps;
  double get currentProgress {
    final total = selectedAction == 'SEND' ? sender.totalBytes : receiver.totalBytes;
    final transferred = selectedAction == 'SEND' ? sender.transferredBytes : receiver.transferredBytes;
    if (total <= 0) return 0.0;
    return (transferred / total).clamp(0.0, 1.0);
  }

  int get currentFileIndex => selectedAction == 'SEND' ? sender.currentFileIndex : receiver.currentFileIndex;
  int get totalFiles => selectedAction == 'SEND' ? sender.totalFiles : receiver.totalFiles;
  String get currentFileName => selectedAction == 'SEND' ? sender.currentFileName : receiver.currentFileName;
  int get transferredBytes => selectedAction == 'SEND' ? sender.transferredBytes : receiver.transferredBytes;
  int get totalBytes => selectedAction == 'SEND' ? sender.totalBytes : receiver.totalBytes;
  int get etaSeconds => selectedAction == 'SEND' ? sender.etaSeconds : receiver.etaSeconds;
  List<String> get logs => selectedAction == 'SEND' ? sender.logs : receiver.logs;
  String get peerName => selectedAction == 'SEND' ? sender.peerName : receiver.peerName;
  String get activeHashMode => selectedAction == 'SEND' ? sender.hashMode : receiver.hashMode;
}
