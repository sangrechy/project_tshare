class PeerDevice {
  final String id;
  final String name;
  final String ip;
  final int port;
  final String medium; // 'wifi', 'ble', 'ethernet'
  final String status;
  final DateTime lastSeen;

  PeerDevice({
    required this.id,
    required this.name,
    required this.ip,
    required this.port,
    required this.medium,
    this.status = 'Available',
    DateTime? lastSeen,
  }) : lastSeen = lastSeen ?? DateTime.now();

  Map<String, dynamic> toJson() => {
    'id': id,
    'name': name,
    'ip': ip,
    'port': port,
    'medium': medium,
    'status': status,
  };

  factory PeerDevice.fromJson(Map<String, dynamic> json) => PeerDevice(
    id: json['id'] as String? ?? '',
    name: json['name'] as String? ?? 'Peer',
    ip: json['ip'] as String? ?? '127.0.0.1',
    port: json['port'] as int? ?? 52001,
    medium: json['medium'] as String? ?? 'wifi',
    status: json['status'] as String? ?? 'Available',
  );
}
