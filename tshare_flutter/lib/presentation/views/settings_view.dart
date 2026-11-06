import 'dart:io';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import '../../core/constants/app_constants.dart';
import '../../core/theme/app_theme.dart';
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
              color: AppTheme.themeCardBg,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: AppTheme.themeCardBorder),
              boxShadow: const [
                BoxShadow(color: Colors.black45, blurRadius: 10, offset: Offset(0, 4)),
              ],
            ),
            child: const Row(
              children: [
                Icon(Icons.settings_rounded, color: Colors.white, size: 32),
                SizedBox(width: 16),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('APPLICATION SETTINGS', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800, color: Colors.white)),
                    SizedBox(height: 2),
                    Text('Manage storage directories, network protocol framing, and hashing security.', style: TextStyle(fontSize: 12, color: AppTheme.themeTextSecondary)),
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
              color: AppTheme.themeCardBg,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: AppTheme.themeCardBorder),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Row(
                  children: [
                    Icon(Icons.folder_rounded, color: Colors.white, size: 18),
                    SizedBox(width: 8),
                    Text(
                      'DEFAULT DOWNLOAD DIRECTORY',
                      style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: AppTheme.themeTextSecondary, letterSpacing: 1.0),
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
                          color: AppTheme.themeInnerBoxBg,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: AppTheme.themeInnerBoxBorder),
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
                      icon: const Icon(Icons.folder_open_rounded, size: 16, color: Colors.black),
                      label: const Text('BROWSE'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.white,
                        foregroundColor: Colors.black,
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                        elevation: 0,
                      ),
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
              color: AppTheme.themeCardBg,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: AppTheme.themeCardBorder),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Row(
                  children: [
                    Icon(Icons.security_rounded, color: Colors.white, size: 18),
                    SizedBox(width: 8),
                    Text(
                      'BLOCK INTEGRITY MODE',
                      style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: AppTheme.themeTextSecondary, letterSpacing: 1.0),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                const Text(
                  'Select the checksum calculation applied per 4 MB streaming frame:',
                  style: TextStyle(fontSize: 12, color: AppTheme.themeTextMuted),
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
              color: AppTheme.themeCardBg,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: AppTheme.themeCardBorder),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Row(
                  children: [
                    Icon(Icons.info_outline_rounded, color: Colors.white, size: 18),
                    SizedBox(width: 8),
                    Text(
                      'SYSTEM & PROTOCOL INFORMATION',
                      style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: AppTheme.themeTextSecondary, letterSpacing: 1.0),
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
          color: isSelected ? AppTheme.themeCardBgElevated : AppTheme.themeInnerBoxBg,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(
            color: isSelected ? Colors.white : AppTheme.themeInnerBoxBorder,
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
                  color: isSelected ? Colors.white : AppTheme.themeTextMuted,
                  width: isSelected ? 2 : 1.5,
                ),
              ),
              child: isSelected
                  ? Center(
                      child: Container(
                        width: 8,
                        height: 8,
                        decoration: const BoxDecoration(
                          shape: BoxShape.circle,
                          color: Colors.white,
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
                      color: isSelected ? Colors.white : const Color(0xFFD4D4D4),
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    description,
                    style: const TextStyle(fontSize: 11, color: AppTheme.themeTextMuted),
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
          Text(label, style: const TextStyle(fontSize: 12, color: AppTheme.themeTextSecondary)),
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
