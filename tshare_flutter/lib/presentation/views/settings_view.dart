import 'dart:io';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import '../../core/constants/app_constants.dart';
import '../viewmodels/app_viewmodel.dart';

class SettingsView extends StatelessWidget {
  final AppViewModel appVm;

  const SettingsView({
    super.key,
    required this.appVm,
  });

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header Card
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [Color(0xFF1E293B), Color(0xFF0F172A)],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: const Color(0xFF334155)),
            ),
            child: const Row(
              children: [
                Icon(Icons.settings_rounded, color: Color(0xFF38BDF8), size: 32),
                SizedBox(width: 16),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('APPLICATION SETTINGS', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800, color: Colors.white)),
                    SizedBox(height: 2),
                    Text('Manage storage directories, network protocol framing, and hashing security.', style: TextStyle(fontSize: 12, color: Color(0xFF94A3B8))),
                  ],
                ),
              ],
            ),
          ),

          const SizedBox(height: 24),

          // Download Path Setting
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: const Color(0xFF111827),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: const Color(0xFF1E293B)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Row(
                  children: [
                    Icon(Icons.folder_rounded, color: Color(0xFF38BDF8), size: 18),
                    SizedBox(width: 8),
                    Text(
                      'DEFAULT DOWNLOAD DIRECTORY',
                      style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: Color(0xFF94A3B8), letterSpacing: 1.0),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                        decoration: BoxDecoration(
                          color: const Color(0xFF0F172A),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: const Color(0xFF1E293B)),
                        ),
                        child: Text(
                          appVm.downloadDirectory,
                          style: const TextStyle(fontSize: 12.5, fontFamily: 'monospace', color: Colors.white),
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    ElevatedButton.icon(
                      onPressed: () async {
                        final selected = await FilePicker.getDirectoryPath();
                        if (selected != null) {
                          await appVm.setDownloadDirectory(selected);
                        }
                      },
                      icon: const Icon(Icons.folder_open_rounded, size: 16),
                      label: const Text('BROWSE'),
                      style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF0284C7)),
                    ),
                  ],
                ),
              ],
            ),
          ),

          const SizedBox(height: 20),

          // Integrity Hash Mode Setting
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: const Color(0xFF111827),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: const Color(0xFF1E293B)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Row(
                  children: [
                    Icon(Icons.security_rounded, color: Color(0xFF38BDF8), size: 18),
                    SizedBox(width: 8),
                    Text(
                      'BLOCK INTEGRITY MODE',
                      style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: Color(0xFF94A3B8), letterSpacing: 1.0),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                const Text(
                  'Select the checksum calculation applied per 4 MB streaming frame:',
                  style: TextStyle(fontSize: 12, color: Color(0xFF64748B)),
                ),
                const SizedBox(height: 16),
                _buildRadioOption(
                  title: 'CRC32 (Recommended)',
                  description: 'Ultra fast 32-bit hardware cyclic redundancy check. Lowest CPU usage with corruption detection.',
                  value: 'crc32',
                  groupValue: appVm.defaultHashMode,
                  onChanged: (val) => appVm.setHashMode(val!),
                ),
                const SizedBox(height: 8),
                _buildRadioOption(
                  title: 'SHA-256 (High Security)',
                  description: 'Cryptographic hash checking per 4 MB chunk. Guards against malicious alteration and packet tampering.',
                  value: 'sha256',
                  groupValue: appVm.defaultHashMode,
                  onChanged: (val) => appVm.setHashMode(val!),
                ),
                const SizedBox(height: 8),
                _buildRadioOption(
                  title: 'None (Raw Throughput)',
                  description: 'Zero checksum verification overhead for maximum transfer speed over reliable networks.',
                  value: 'none',
                  groupValue: appVm.defaultHashMode,
                  onChanged: (val) => appVm.setHashMode(val!),
                ),
              ],
            ),
          ),

          const SizedBox(height: 20),

          // Network Diagnostics & System Information
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: const Color(0xFF111827),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: const Color(0xFF1E293B)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Row(
                  children: [
                    Icon(Icons.info_outline_rounded, color: Color(0xFF38BDF8), size: 18),
                    SizedBox(width: 8),
                    Text(
                      'SYSTEM & PROTOCOL INFORMATION',
                      style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: Color(0xFF94A3B8), letterSpacing: 1.0),
                    ),
                  ],
                ),
                const SizedBox(height: 14),
                _buildInfoRow('Device Hostname', Platform.localHostname),
                _buildInfoRow('Operating System', '${Platform.operatingSystem} ${Platform.operatingSystemVersion}'),
                _buildInfoRow('TCP Streaming Port', '${AppConstants.tcpTransferPort}'),
                _buildInfoRow('UDP Discovery Port', '${AppConstants.discoveryPort}'),
                _buildInfoRow('HTTP Web Portal Port', '${AppConstants.portalPort}'),
                _buildInfoRow('Streaming Block Size', '4 MB (4,194,304 bytes)'),
                _buildInfoRow('Protocol Version', 'v4.0.0 (TSHR Magic: 0x54534852)'),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildRadioOption({
    required String title,
    required String description,
    required String value,
    required String groupValue,
    required ValueChanged<String?> onChanged,
  }) {
    final isSelected = value == groupValue;

    return InkWell(
      onTap: () => onChanged(value),
      borderRadius: BorderRadius.circular(8),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          color: isSelected ? const Color(0xFF0284C7).withAlpha(30) : const Color(0xFF0F172A),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(
            color: isSelected ? const Color(0xFF38BDF8) : const Color(0xFF1E293B),
            width: isSelected ? 1.5 : 1,
          ),
        ),
        child: Row(
          children: [
            Container(
              width: 18,
              height: 18,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(
                  color: isSelected ? const Color(0xFF38BDF8) : const Color(0xFF64748B),
                  width: 2,
                ),
              ),
              child: isSelected
                  ? Center(
                      child: Container(
                        width: 8,
                        height: 8,
                        decoration: const BoxDecoration(
                          shape: BoxShape.circle,
                          color: Color(0xFF38BDF8),
                        ),
                      ),
                    )
                  : null,
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w800,
                      color: isSelected ? Colors.white : const Color(0xFFE2E8F0),
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    description,
                    style: const TextStyle(fontSize: 11, color: Color(0xFF64748B)),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildInfoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(fontSize: 12, color: Color(0xFF94A3B8))),
          const SizedBox(width: 12),
          Flexible(
            child: Text(
              value,
              style: const TextStyle(fontSize: 12, fontFamily: 'monospace', color: Colors.white),
              overflow: TextOverflow.ellipsis,
              textAlign: TextAlign.right,
            ),
          ),
        ],
      ),
    );
  }
}
