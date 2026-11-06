import 'dart:async';
import 'dart:convert';
import 'dart:io';
import '../models/peer_device.dart';
import '../../core/constants/app_constants.dart';

class PeerDiscoveryService {
  RawDatagramSocket? _socket;
  Timer? _broadcastTimer;
  final Map<String, PeerDevice> _peers = {};
  final _peerStreamController = StreamController<List<PeerDevice>>.broadcast();

  Stream<List<PeerDevice>> get peersStream => _peerStreamController.stream;
  List<PeerDevice> get peers => _peers.values.toList();

  bool _isRunning = false;
  bool get isRunning => _isRunning;

  Future<void> start({int tcpPort = AppConstants.defaultPort}) async {
    if (_isRunning) return;
    _isRunning = true;

    try {
      _socket = await RawDatagramSocket.bind(
        InternetAddress.anyIPv4,
        AppConstants.discoveryPort,
        reuseAddress: true,
        reusePort: false,
      );
      _socket?.broadcastEnabled = true;

      _socket?.listen((event) {
        if (event == RawSocketEvent.read) {
          final dg = _socket?.receive();
          if (dg != null) {
            _handlePacket(dg);
          }
        }
      });

      // Broadcast beacon every 2.5 seconds
      _broadcastTimer = Timer.periodic(const Duration(milliseconds: 2500), (_) {
        _broadcastPresence(tcpPort);
        _pruneStalePeers();
      });

      _broadcastPresence(tcpPort);
    } catch (e) {
      // Socket bind warning (e.g. port in use by another instance)
    }
  }

  void _broadcastPresence(int tcpPort) {
    if (_socket == null) return;
    try {
      final payload = jsonEncode({
        'magic': 'TSHR',
        'version': 4,
        'hostname': Platform.localHostname,
        'port': tcpPort,
        'os': Platform.operatingSystem,
      });
      final bytes = utf8.encode(payload);

      // Broadcast to standard IPv4 subnet targets
      final targets = [
        InternetAddress('255.255.255.255'),
        InternetAddress('192.168.123.255'),
        InternetAddress('169.254.255.255'),
      ];

      for (final t in targets) {
        try {
          _socket?.send(bytes, t, AppConstants.discoveryPort);
        } catch (_) {}
      }
    } catch (_) {}
  }

  void _handlePacket(Datagram dg) {
    try {
      final text = utf8.decode(dg.data);
      final json = jsonDecode(text) as Map<String, dynamic>;
      if (json['magic'] != 'TSHR') return;

      final senderIp = dg.address.address;
      final peerName = json['hostname'] as String? ?? 'Peer';
      final peerPort = json['port'] as int? ?? AppConstants.defaultPort;

      // Determine medium
      String medium = 'wifi';
      if (senderIp.startsWith('192.168.123.') || senderIp.startsWith('169.254.')) {
        medium = 'ethernet';
      }

      final peer = PeerDevice(
        id: '$senderIp:$peerPort',
        name: peerName,
        ip: senderIp,
        port: peerPort,
        medium: medium,
        status: 'Available',
        lastSeen: DateTime.now(),
      );

      _peers[peer.id] = peer;
      _peerStreamController.add(peers);
    } catch (_) {}
  }

  void _pruneStalePeers() {
    final now = DateTime.now();
    bool changed = false;
    _peers.removeWhere((id, p) {
      final isStale = now.difference(p.lastSeen).inSeconds > 10;
      if (isStale) changed = true;
      return isStale;
    });
    if (changed) {
      _peerStreamController.add(peers);
    }
  }

  void stop() {
    _isRunning = false;
    _broadcastTimer?.cancel();
    _socket?.close();
    _socket = null;
    _peers.clear();
  }
}
