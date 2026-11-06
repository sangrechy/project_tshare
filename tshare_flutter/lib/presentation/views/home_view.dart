import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import '../../core/theme/app_theme.dart';
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
    return LayoutBuilder(
      builder: (context, constraints) {
        final isMobile = constraints.maxWidth < 768;

        final welcomeCard = Container(
          padding: const EdgeInsets.all(22),
          decoration: BoxDecoration(
            color: AppTheme.themeCardBg,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: AppTheme.themeCardBorder),
          ),
          child: isMobile
              ? Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.all(10),
                          decoration: BoxDecoration(
                            color: AppTheme.themeCardBgElevated,
                            shape: BoxShape.circle,
                            border: Border.all(color: AppTheme.themeCardBorder),
                          ),
                          child: const Icon(Icons.swap_horizontal_circle_outlined, color: AppTheme.themeTextPrimary, size: 22),
                        ),
                        const SizedBox(width: 12),
                        const Expanded(
                          child: Text(
                            'TShare File Transfer',
                            style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800, color: AppTheme.themeTextPrimary),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    Text(
                      sharingVm.isTransferring
                          ? 'Transfer in progress with ${sharingVm.peerName} (${sharingVm.currentFileName})'
                          : 'High-speed streaming engine ready over WiFi, BLE & Ethernet.',
                      style: const TextStyle(fontSize: 12.5, color: AppTheme.themeTextSecondary),
                    ),
                    const SizedBox(height: 14),
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton.icon(
                        onPressed: () => appVm.setNavIndex(1),
                        icon: const Icon(Icons.arrow_forward_rounded, size: 16),
                        label: const Text('FILE SHARING'),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: AppTheme.themeAccentPrimary,
                          foregroundColor: const Color(0xFF000000),
                          padding: const EdgeInsets.symmetric(vertical: 13),
                        ),
                      ),
                    ),
                  ],
                )
              : Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: AppTheme.themeCardBgElevated,
                        shape: BoxShape.circle,
                        border: Border.all(color: AppTheme.themeCardBorder),
                      ),
                      child: const Icon(Icons.swap_horizontal_circle_outlined, color: AppTheme.themeTextPrimary, size: 28),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'TShare File Transfer Suite',
                            style: TextStyle(fontSize: 17, fontWeight: FontWeight.w800, color: AppTheme.themeTextPrimary),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            sharingVm.isTransferring
                                ? 'Transfer in progress with ${sharingVm.peerName} (${sharingVm.currentFileName})'
                                : 'High-speed streaming engine ready over WiFi, BLE & Ethernet.',
                            style: const TextStyle(fontSize: 13, color: AppTheme.themeTextSecondary),
                          ),
                        ],
                      ),
                    ),
                    ElevatedButton.icon(
                      onPressed: () => appVm.setNavIndex(1),
                      icon: const Icon(Icons.arrow_forward_rounded, size: 16),
                      label: const Text('FILE SHARING'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppTheme.themeAccentPrimary,
                        foregroundColor: const Color(0xFF000000),
                        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
                      ),
                    ),
                  ],
                ),
        );

        final gaugesCard = Container(
          padding: const EdgeInsets.all(22),
          decoration: BoxDecoration(
            color: AppTheme.themeCardBg,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: AppTheme.themeCardBorder),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'REAL-TIME TELEMETRY',
                style: TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w800,
                  color: AppTheme.themeTextSecondary,
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
                    primaryColor: AppTheme.themeAccentPrimary,
                  ),
                  CircularTelemetryGauge(
                    value: sharingVm.currentCpuPercent,
                    maxValue: 100,
                    label: 'CPU',
                    unit: '%',
                    primaryColor: AppTheme.themeAccentSilver,
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
                primaryColor: AppTheme.themeAccentPrimary,
              ),
            ],
          ),
        );

        final logsView = TerminalLogView(
          logs: sharingVm.logs,
          height: isMobile ? 220 : 275,
        );

        final downloadCard = Container(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
          decoration: BoxDecoration(
            color: AppTheme.themeCardBg,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: AppTheme.themeCardBorder),
          ),
          child: isMobile
              ? Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Row(
                      children: [
                        Icon(Icons.folder_open_rounded, color: AppTheme.themeTextPrimary, size: 20),
                        SizedBox(width: 10),
                        Text(
                          'DOWNLOAD DIRECTORY',
                          style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: AppTheme.themeTextSecondary),
                        ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    Text(
                      appVm.downloadDirectory,
                      style: const TextStyle(fontSize: 12, color: AppTheme.themeTextPrimary, fontFamily: 'monospace'),
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 10),
                    SizedBox(
                      width: double.infinity,
                      child: OutlinedButton.icon(
                        onPressed: () async {
                          final selected = await FilePicker.getDirectoryPath();
                          if (selected != null) {
                            await appVm.setDownloadDirectory(selected);
                          }
                        },
                        icon: const Icon(Icons.edit_location_alt_outlined, size: 16),
                        label: const Text('CHANGE FOLDER'),
                        style: OutlinedButton.styleFrom(
                          foregroundColor: AppTheme.themeTextPrimary,
                          side: const BorderSide(color: AppTheme.themeCardBorder),
                        ),
                      ),
                    ),
                  ],
                )
              : Row(
                  children: [
                    const Icon(Icons.folder_open_rounded, color: AppTheme.themeTextPrimary, size: 22),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'DEFAULT DOWNLOAD DIRECTORY',
                            style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: AppTheme.themeTextSecondary),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            appVm.downloadDirectory,
                            style: const TextStyle(fontSize: 13, color: AppTheme.themeTextPrimary, fontFamily: 'monospace'),
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
                        foregroundColor: AppTheme.themeTextPrimary,
                        side: const BorderSide(color: AppTheme.themeCardBorder),
                      ),
                    ),
                  ],
                ),
        );

        return SingleChildScrollView(
          padding: EdgeInsets.all(isMobile ? 14 : 24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              welcomeCard,
              const SizedBox(height: 20),
              if (isMobile) ...[
                gaugesCard,
                const SizedBox(height: 16),
                logsView,
              ] else ...[
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(flex: 4, child: gaugesCard),
                    const SizedBox(width: 20),
                    Expanded(flex: 5, child: logsView),
                  ],
                ),
              ],
              const SizedBox(height: 20),
              downloadCard,
            ],
          ),
        );
      },
    );
  }
}
