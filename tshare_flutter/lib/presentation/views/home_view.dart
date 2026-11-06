import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import '../viewmodels/app_viewmodel.dart';
import '../viewmodels/sharing_viewmodel.dart';
import '../widgets/circular_telemetry_gauge.dart';
import '../widgets/custom_progress_bar.dart';
import '../widgets/terminal_log_view.dart';

class HomeView extends StatelessWidget {
  final AppViewModel appVm;
  final SharingViewModel sharingVm;

  const HomeView({
    super.key,
    required this.appVm,
    required this.sharingVm,
  });

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Top Welcome & Quick Action Card
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
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: const Color(0xFF0284C7).withAlpha(40),
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(Icons.swap_horizontal_circle_outlined, color: Color(0xFF38BDF8), size: 32),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'TShare High-Speed File Transfer',
                        style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: Colors.white),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        sharingVm.isTransferring
                            ? 'Transfer in progress with ${sharingVm.peerName} (${sharingVm.currentFileName})'
                            : 'Cross-platform streaming engine ready over WiFi, BLE & Ethernet.',
                        style: const TextStyle(fontSize: 13, color: Color(0xFF94A3B8)),
                      ),
                    ],
                  ),
                ),
                ElevatedButton.icon(
                  onPressed: () => appVm.setNavIndex(1),
                  icon: const Icon(Icons.rocket_launch_rounded, size: 16),
                  label: const Text('FILE SHARING'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF0284C7),
                    padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(height: 24),

          // Real-time Telemetry Section
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Dual Gauges Card
              Expanded(
                flex: 4,
                child: Container(
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    color: const Color(0xFF111827),
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: const Color(0xFF1E293B)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'REAL-TIME TELEMETRY',
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w800,
                          color: Color(0xFF94A3B8),
                          letterSpacing: 1.0,
                        ),
                      ),
                      const SizedBox(height: 20),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceAround,
                        children: [
                          CircularTelemetryGauge(
                            value: sharingVm.currentSpeedMbps,
                            maxValue: 200,
                            label: 'Speed',
                            unit: 'MB/s',
                            primaryColor: const Color(0xFF38BDF8),
                          ),
                          CircularTelemetryGauge(
                            value: sharingVm.currentCpuPercent,
                            maxValue: 100,
                            label: 'CPU',
                            unit: '%',
                            primaryColor: const Color(0xFF10B981),
                          ),
                        ],
                      ),
                      const SizedBox(height: 24),
                      CustomProgressBar(
                        progress: sharingVm.currentProgress,
                        leftLabel: sharingVm.isTransferring
                            ? 'File ${sharingVm.currentFileIndex} of ${sharingVm.totalFiles}'
                            : 'Transfer Idle',
                        rightLabel: sharingVm.isTransferring
                            ? '${(sharingVm.transferredBytes / (1024 * 1024)).toStringAsFixed(1)} / ${(sharingVm.totalBytes / (1024 * 1024)).toStringAsFixed(1)} MB'
                            : '0 MB',
                      ),
                    ],
                  ),
                ),
              ),

              const SizedBox(width: 20),

              // Live Event Logs
              Expanded(
                flex: 5,
                child: TerminalLogView(
                  logs: sharingVm.logs,
                  height: 275,
                ),
              ),
            ],
          ),

          const SizedBox(height: 24),

          // Download Destination Row
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
            decoration: BoxDecoration(
              color: const Color(0xFF111827),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: const Color(0xFF1E293B)),
            ),
            child: Row(
              children: [
                const Icon(Icons.folder_open_rounded, color: Color(0xFF38BDF8), size: 22),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'DEFAULT DOWNLOAD DIRECTORY',
                        style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: Color(0xFF94A3B8)),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        appVm.downloadDirectory,
                        style: const TextStyle(fontSize: 13, color: Colors.white, fontFamily: 'monospace'),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ),
                ),
                OutlinedButton.icon(
                  onPressed: () async {
                    final selected = await FilePicker.getDirectoryPath();
                    if (selected != null) {
                      await appVm.setDownloadDirectory(selected);
                    }
                  },
                  icon: const Icon(Icons.edit_location_alt_outlined, size: 16),
                  label: const Text('CHANGE FOLDER'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: const Color(0xFF38BDF8),
                    side: const BorderSide(color: Color(0xFF0284C7)),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
