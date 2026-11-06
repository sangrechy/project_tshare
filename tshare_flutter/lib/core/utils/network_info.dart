import 'dart:io';

class NetworkInfo {
  /// Returns the most likely local IPv4 address (e.g. 192.168.x.x, 10.x.x.x, 172.x.x.x)
  static Future<String> getPrimaryLocalIp() async {
    try {
      final interfaces = await NetworkInterface.list(
        type: InternetAddressType.IPv4,
        includeLinkLocal: false,
      );

      for (final iface in interfaces) {
        final name = iface.name.toLowerCase();
        // Skip loopback, virtual bridges, docker, etc.
        if (name.contains('lo') || name.contains('docker') || name.contains('veth') || name.contains('virbr')) {
          continue;
        }
        for (final addr in iface.addresses) {
          if (!addr.isLoopback && !addr.isLinkLocal) {
            return addr.address;
          }
        }
      }

      // Fallback to first non-loopback address
      for (final iface in interfaces) {
        for (final addr in iface.addresses) {
          if (!addr.isLoopback) return addr.address;
        }
      }
    } catch (_) {}
    return '127.0.0.1';
  }
}
