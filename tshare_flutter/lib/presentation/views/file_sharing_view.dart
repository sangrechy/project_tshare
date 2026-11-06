import 'package:flutter/material.dart';
import '../../core/constants/app_constants.dart';
import '../viewmodels/app_viewmodel.dart';
import '../viewmodels/sharing_viewmodel.dart';
import '../widgets/circular_telemetry_gauge.dart';
import '../widgets/custom_progress_bar.dart';
import '../widgets/rotary_dial_widget.dart';
import '../widgets/terminal_log_view.dart';

class FileSharingView extends StatelessWidget {
  final AppViewModel appVm;
  final SharingViewModel sharingVm;

  const FileSharingView({
    super.key,
    required this.appVm,
    required this.sharingVm,
  });

  @override
  Widget build(BuildContext context) {
    return AnimatedSwitcher(
      duration: const Duration(milliseconds: 350),
      child: _buildStageContent(context),
    );
  }

  Widget _buildStageContent(BuildContext context) {
    switch (sharingVm.stage) {
      case 1:
        return _buildStage1Rotary(context);
      case 2:
        return _buildStage2Connection(context);
      case 3:
      default:
        return _buildStage3Dashboard(context);
    }
  }

  // ==========================================
  // STATE 1: ROTARY SELECTION INTERFACE
  // ==========================================
  Widget _buildStage1Rotary(BuildContext context) {
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Wrap(
          alignment: WrapAlignment.center,
          crossAxisAlignment: WrapCrossAlignment.center,
          spacing: 32,
          runSpacing: 32,
          children: [
            // Left: The Rotary Dial
            ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 450),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Text(
                    'ROTARY TELEPHONE SELECTOR',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w800,
                      color: Color(0xFF94A3B8),
                      letterSpacing: 1.5,
                    ),
                  ),
                  const SizedBox(height: 6),
                  const Text(
                    'Select Action & Connection method. The outer ring rotates to indicate selection.',
                    style: TextStyle(fontSize: 12, color: Color(0xFF64748B)),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 24),
                  RotaryDialWidget(
                    selectedAction: sharingVm.selectedAction,
                    selectedConnection: sharingVm.selectedConnection,
                    onActionChanged: (act) => sharingVm.selectAction(act),
                    onConnectionChanged: (conn) => sharingVm.selectConnection(conn),
                    onConfirm: () => sharingVm.confirmRotarySelection(appVm.downloadDirectory),
                  ),
                ],
              ),
            ),

            // Right: Mirrored Selection Summary Boxes
            Container(
              constraints: const BoxConstraints(maxWidth: 380),
                padding: const EdgeInsets.all(24),
                decoration: BoxDecoration(
                  color: const Color(0xFF111827),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: const Color(0xFF1E293B)),
                  boxShadow: const [
                    BoxShadow(color: Colors.black26, blurRadius: 10, offset: Offset(0, 4)),
                  ],
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    // ACTION Section
                    const Text(
                      'ACTION',
                      style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: Color(0xFF94A3B8), letterSpacing: 1.2),
                    ),
                    const SizedBox(height: 10),
                    _buildSelectionOption(
                      title: 'SEND',
                      subtitle: 'Transmit files to remote peer',
                      icon: Icons.upload_rounded,
                      isSelected: sharingVm.selectedAction == 'SEND',
                      onTap: () => sharingVm.selectAction('SEND'),
                    ),
                    const SizedBox(height: 8),
                    _buildSelectionOption(
                      title: 'RECEIVE',
                      subtitle: 'Wait for and accept incoming files',
                      icon: Icons.download_rounded,
                      isSelected: sharingVm.selectedAction == 'RECEIVE',
                      onTap: () => sharingVm.selectAction('RECEIVE'),
                    ),

                    const Padding(
                      padding: EdgeInsets.symmetric(vertical: 16),
                      child: Divider(color: Color(0xFF1E293B), height: 1),
                    ),

                    // CONNECTION Section
                    const Text(
                      'CONNECTION',
                      style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: Color(0xFF94A3B8), letterSpacing: 1.2),
                    ),
                    const SizedBox(height: 10),
                    _buildSelectionOption(
                      title: 'WIFI',
                      subtitle: 'High speed Local Area Network',
                      icon: Icons.wifi_rounded,
                      isSelected: sharingVm.selectedConnection == 'WIFI',
                      onTap: () => sharingVm.selectConnection('WIFI'),
                    ),
                    const SizedBox(height: 8),
                    _buildSelectionOption(
                      title: 'BLE',
                      subtitle: 'Bluetooth Low Energy discovery',
                      icon: Icons.bluetooth_rounded,
                      isSelected: sharingVm.selectedConnection == 'BLE',
                      onTap: () => sharingVm.selectConnection('BLE'),
                    ),
                    const SizedBox(height: 8),
                    _buildSelectionOption(
                      title: 'ETHERNET',
                      subtitle: 'Direct gigabit wired network',
                      icon: Icons.settings_ethernet_rounded,
                      isSelected: sharingVm.selectedConnection == 'ETHERNET',
                      onTap: () => sharingVm.selectConnection('ETHERNET'),
                    ),

                    const SizedBox(height: 24),

                    // Confirm Button
                    ElevatedButton(
                      onPressed: () => sharingVm.confirmRotarySelection(appVm.downloadDirectory),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF0284C7),
                        padding: const EdgeInsets.symmetric(vertical: 16),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                      ),
                      child: Text(
                        'CONFIRM: ${sharingVm.selectedAction} + ${sharingVm.selectedConnection}',
                        style: const TextStyle(fontWeight: FontWeight.w800, letterSpacing: 0.5),
                      ),
                    ),
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildSelectionOption({
    required String title,
    required String subtitle,
    required IconData icon,
    required bool isSelected,
    required VoidCallback onTap,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(10),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          color: isSelected ? const Color(0xFF0284C7).withAlpha(40) : const Color(0xFF0F172A),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
            color: isSelected ? const Color(0xFF38BDF8) : const Color(0xFF1E293B),
            width: isSelected ? 1.5 : 1,
          ),
        ),
        child: Row(
          children: [
            Icon(icon, size: 20, color: isSelected ? const Color(0xFF38BDF8) : const Color(0xFF94A3B8)),
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
                  Text(
                    subtitle,
                    style: const TextStyle(fontSize: 11, color: Color(0xFF64748B)),
                  ),
                ],
              ),
            ),
            if (isSelected)
              const Icon(Icons.check_circle_rounded, color: Color(0xFF38BDF8), size: 18),
          ],
        ),
      ),
    );
  }

  // ==========================================
  // STATE 2: DEVICE CONNECTION INTERFACE
  // ==========================================
  Widget _buildStage2Connection(BuildContext context) {
    final isSend = sharingVm.selectedAction == 'SEND';

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header Bar
          Row(
            children: [
              IconButton(
                onPressed: () => sharingVm.resetToRotary(),
                icon: const Icon(Icons.arrow_back_rounded, color: Color(0xFF94A3B8)),
                tooltip: 'Back to Rotary Selector',
              ),
              const SizedBox(width: 8),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('DEVICE CONNECTION', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: Colors.white)),
                  Text(
                    'Selected Mode: ${sharingVm.selectedAction} + ${sharingVm.selectedConnection}',
                    style: const TextStyle(fontSize: 13, color: Color(0xFF38BDF8), fontWeight: FontWeight.w600),
                  ),
                ],
              ),
              const Spacer(),
              if (isSend)
                ElevatedButton.icon(
                  onPressed: (sharingVm.selectedFiles.isEmpty || (sharingVm.manualIp.isEmpty && sharingVm.targetDevice == null))
                      ? null
                      : () => sharingVm.initiateSendTransfer(hashMode: appVm.defaultHashMode),
                  icon: const Icon(Icons.send_rounded, size: 16),
                  label: const Text('START TRANSFER'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF10B981),
                    padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
                  ),
                ),
            ],
          ),

          const SizedBox(height: 20),

          // Receiver Incoming Offer Banner
          if (!isSend && sharingVm.receiver.pendingOffer != null)
            Container(
              margin: const EdgeInsets.only(bottom: 20),
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(
                color: const Color(0xFF0F172A),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: const Color(0xFF38BDF8), width: 2),
                boxShadow: [
                  BoxShadow(color: const Color(0xFF38BDF8).withAlpha(60), blurRadius: 16),
                ],
              ),
              child: Row(
                children: [
                  const Icon(Icons.notifications_active_rounded, color: Color(0xFF38BDF8), size: 32),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Incoming Transfer Offer from ${sharingVm.receiver.pendingOffer!.peerName}',
                          style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w800, color: Colors.white),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          '${sharingVm.receiver.pendingOffer!.totalFiles} files (${(sharingVm.receiver.pendingOffer!.totalBytes / (1024 * 1024)).toStringAsFixed(1)} MB) • Integrity: ${sharingVm.receiver.pendingOffer!.hashMode.toUpperCase()}',
                          style: const TextStyle(fontSize: 12, color: Color(0xFF94A3B8)),
                        ),
                      ],
                    ),
                  ),
                  OutlinedButton(
                    onPressed: () => sharingVm.receiver.pendingOffer?.decline(),
                    style: OutlinedButton.styleFrom(foregroundColor: const Color(0xFFEF4444)),
                    child: const Text('DECLINE'),
                  ),
                  const SizedBox(width: 12),
                  ElevatedButton(
                    onPressed: () => sharingVm.receiver.pendingOffer?.accept(),
                    style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF10B981)),
                    child: const Text('ACCEPT TRANSFER'),
                  ),
                ],
              ),
            ),

          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Left Column: Manual Connect + Discovered Devices
              Expanded(
                flex: 5,
                child: Column(
                  children: [
                    // Manual Connect Box
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
                              Icon(Icons.tune_rounded, size: 18, color: Color(0xFF38BDF8)),
                              SizedBox(width: 8),
                              Text(
                                'MANUAL CONNECT',
                                style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: Color(0xFF94A3B8), letterSpacing: 1.0),
                              ),
                            ],
                          ),
                          const SizedBox(height: 14),
                          Row(
                            children: [
                              Expanded(
                                flex: 3,
                                child: TextFormField(
                                  initialValue: sharingVm.manualIp,
                                  onChanged: (val) => sharingVm.setManualIp(val),
                                  style: const TextStyle(fontFamily: 'monospace', fontSize: 13),
                                  decoration: InputDecoration(
                                    labelText: 'Target IP Address',
                                    hintText: 'e.g. 192.168.1.100',
                                    isDense: true,
                                    filled: true,
                                    fillColor: const Color(0xFF0F172A),
                                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                                  ),
                                ),
                              ),
                              const SizedBox(width: 10),
                              Expanded(
                                flex: 1,
                                child: TextFormField(
                                  initialValue: '${sharingVm.manualPort}',
                                  readOnly: true,
                                  style: const TextStyle(fontFamily: 'monospace', fontSize: 13),
                                  decoration: InputDecoration(
                                    labelText: 'Port',
                                    isDense: true,
                                    filled: true,
                                    fillColor: const Color(0xFF0F172A),
                                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),

                    const SizedBox(height: 18),

                    // Auto Find Devices Box
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
                          Row(
                            children: [
                              const Icon(Icons.radar_rounded, size: 18, color: Color(0xFF38BDF8)),
                              const SizedBox(width: 8),
                              const Text(
                                'AUTO FIND DEVICES',
                                style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: Color(0xFF94A3B8), letterSpacing: 1.0),
                              ),
                              const Spacer(),
                              if (sharingVm.isAutoDiscovering)
                                const SizedBox(
                                  width: 14,
                                  height: 14,
                                  child: CircularProgressIndicator(strokeWidth: 2, color: Color(0xFF38BDF8)),
                                ),
                              const SizedBox(width: 8),
                              TextButton(
                                onPressed: () {
                                  if (sharingVm.isAutoDiscovering) {
                                    sharingVm.stopAutoDiscovery();
                                  } else {
                                    sharingVm.startAutoDiscovery();
                                  }
                                },
                                child: Text(sharingVm.isAutoDiscovering ? 'STOP SEARCH' : 'SEARCH'),
                              ),
                            ],
                          ),
                          const SizedBox(height: 12),
                          if (sharingVm.discoveredDevices.isEmpty)
                            Container(
                              padding: const EdgeInsets.symmetric(vertical: 24),
                              alignment: Alignment.center,
                              child: Text(
                                sharingVm.isAutoDiscovering ? 'Searching for devices on LAN...' : 'No devices discovered. Tap SEARCH.',
                                style: const TextStyle(color: Color(0xFF64748B), fontSize: 12),
                              ),
                            )
                          else
                            ListView.separated(
                              shrinkWrap: true,
                              physics: const NeverScrollableScrollPhysics(),
                              itemCount: sharingVm.discoveredDevices.length,
                              separatorBuilder: (_, _) => const Divider(color: Color(0xFF1E293B), height: 1),
                              itemBuilder: (context, idx) {
                                final dev = sharingVm.discoveredDevices[idx];
                                final isSelected = sharingVm.targetDevice?.ip == dev.ip;

                                return ListTile(
                                  contentPadding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                  leading: const Icon(Icons.laptop_chromebook_rounded, color: Color(0xFF38BDF8)),
                                  title: Text(dev.name, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
                                  subtitle: Text('${dev.ip}:${dev.port} • ${dev.medium.toUpperCase()}', style: const TextStyle(fontSize: 11, color: Color(0xFF94A3B8))),
                                  trailing: ElevatedButton(
                                    onPressed: () => sharingVm.selectDevice(dev),
                                    style: ElevatedButton.styleFrom(
                                      backgroundColor: isSelected ? const Color(0xFF10B981) : const Color(0xFF1E293B),
                                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                                    ),
                                    child: Text(isSelected ? 'SELECTED' : 'SELECT', style: const TextStyle(fontSize: 11)),
                                  ),
                                );
                              },
                            ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(width: 20),

              // Right Column: Files to Send (in SEND mode) or Receiver Status (in RECEIVE mode)
              Expanded(
                flex: 5,
                child: isSend
                    ? Container(
                        padding: const EdgeInsets.all(20),
                        decoration: BoxDecoration(
                          color: const Color(0xFF111827),
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(color: const Color(0xFF1E293B)),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                const Icon(Icons.folder_shared_rounded, size: 18, color: Color(0xFF38BDF8)),
                                const SizedBox(width: 8),
                                const Text(
                                  'FILES TO SEND',
                                  style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: Color(0xFF94A3B8), letterSpacing: 1.0),
                                ),
                                const Spacer(),
                                OutlinedButton.icon(
                                  onPressed: () => sharingVm.pickFiles(),
                                  icon: const Icon(Icons.add, size: 14),
                                  label: const Text('ADD FILES', style: TextStyle(fontSize: 11)),
                                ),
                                const SizedBox(width: 6),
                                OutlinedButton.icon(
                                  onPressed: () => sharingVm.pickDirectory(),
                                  icon: const Icon(Icons.create_new_folder_outlined, size: 14),
                                  label: const Text('ADD FOLDER', style: TextStyle(fontSize: 11)),
                                ),
                              ],
                            ),
                            const SizedBox(height: 14),
                            if (sharingVm.selectedFiles.isEmpty)
                              Container(
                                height: 220,
                                alignment: Alignment.center,
                                decoration: BoxDecoration(
                                  border: Border.all(color: const Color(0xFF1E293B), style: BorderStyle.solid),
                                  borderRadius: BorderRadius.circular(10),
                                ),
                                child: const Column(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    Icon(Icons.cloud_upload_outlined, size: 36, color: Color(0xFF475569)),
                                    SizedBox(height: 8),
                                    Text('No files selected yet.', style: TextStyle(color: Color(0xFF64748B), fontSize: 13)),
                                    Text('Tap Add Files or Add Folder above.', style: TextStyle(color: Color(0xFF475569), fontSize: 11)),
                                  ],
                                ),
                              )
                            else
                              Container(
                                height: 220,
                                decoration: BoxDecoration(
                                  color: const Color(0xFF0F172A),
                                  borderRadius: BorderRadius.circular(10),
                                ),
                                child: ListView.separated(
                                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                                  itemCount: sharingVm.selectedFiles.length,
                                  separatorBuilder: (_, _) => const Divider(color: Color(0xFF1E293B), height: 1),
                                  itemBuilder: (context, idx) {
                                    final file = sharingVm.selectedFiles[idx];
                                    return ListTile(
                                      dense: true,
                                      leading: Icon(
                                        file.isDirectory ? Icons.folder_rounded : Icons.insert_drive_file_rounded,
                                        color: const Color(0xFF38BDF8),
                                        size: 18,
                                      ),
                                      title: Text(file.name, style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600)),
                                      subtitle: Text(file.formattedSize, style: const TextStyle(fontSize: 11, color: Color(0xFF94A3B8))),
                                      trailing: IconButton(
                                        icon: const Icon(Icons.close_rounded, size: 16, color: Color(0xFFEF4444)),
                                        onPressed: () => sharingVm.removeFile(idx),
                                      ),
                                    );
                                  },
                                ),
                              ),
                          ],
                        ),
                      )
                    : Container(
                        padding: const EdgeInsets.all(24),
                        decoration: BoxDecoration(
                          color: const Color(0xFF111827),
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(color: const Color(0xFF1E293B)),
                        ),
                        child: Column(
                          children: [
                            const Icon(Icons.cell_tower_rounded, color: Color(0xFF38BDF8), size: 48),
                            const SizedBox(height: 16),
                            const Text(
                              'Receiver Server Active',
                              style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800, color: Colors.white),
                            ),
                            const SizedBox(height: 6),
                            Text(
                              'Listening for incoming connections on port ${AppConstants.tcpTransferPort}.\nSender devices on this network will discover this receiver automatically.',
                              style: const TextStyle(fontSize: 12, color: Color(0xFF94A3B8), height: 1.4),
                              textAlign: TextAlign.center,
                            ),
                            const SizedBox(height: 20),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                              decoration: BoxDecoration(
                                color: const Color(0xFF0F172A),
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: Text(
                                'Saving to: ${appVm.downloadDirectory}',
                                style: const TextStyle(fontSize: 11, fontFamily: 'monospace', color: Color(0xFF38BDF8)),
                              ),
                            ),
                          ],
                        ),
                      ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  // ==========================================
  // STATE 3: TRANSFER MONITORING DASHBOARD
  // ==========================================
  Widget _buildStage3Dashboard(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Top Transfer Header
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
            decoration: BoxDecoration(
              color: const Color(0xFF111827),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: const Color(0xFF1E293B)),
            ),
            child: Row(
              children: [
                Icon(
                  sharingVm.isCompleted
                      ? Icons.check_circle_rounded
                      : (sharingVm.isError ? Icons.error_rounded : Icons.sync_rounded),
                  color: sharingVm.isCompleted
                      ? const Color(0xFF10B981)
                      : (sharingVm.isError ? const Color(0xFFEF4444) : const Color(0xFF38BDF8)),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        sharingVm.isCompleted
                            ? 'TRANSFER COMPLETE'
                            : (sharingVm.isError ? 'TRANSFER ERROR' : 'TRANSFER IN PROGRESS'),
                        style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w800, color: Colors.white),
                      ),
                      Text(
                        '${sharingVm.selectedAction} via ${sharingVm.selectedConnection} • Peer: ${sharingVm.peerName} • Integrity: ${sharingVm.activeHashMode.toUpperCase()}',
                        style: const TextStyle(fontSize: 12, color: Color(0xFF94A3B8)),
                      ),
                    ],
                  ),
                ),
                if (sharingVm.isTransferring)
                  OutlinedButton.icon(
                    onPressed: () => sharingVm.cancelTransfer(),
                    icon: const Icon(Icons.cancel_outlined, size: 16),
                    label: const Text('CANCEL'),
                    style: OutlinedButton.styleFrom(foregroundColor: const Color(0xFFEF4444)),
                  )
                else
                  ElevatedButton.icon(
                    onPressed: () => sharingVm.resetToRotary(),
                    icon: const Icon(Icons.refresh_rounded, size: 16),
                    label: const Text('NEW TRANSFER'),
                    style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF0284C7)),
                  ),
              ],
            ),
          ),

          const SizedBox(height: 20),

          // Gauges & Progress Row
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Radial Gauges Card
              Expanded(
                flex: 4,
                child: Container(
                  padding: const EdgeInsets.all(22),
                  decoration: BoxDecoration(
                    color: const Color(0xFF111827),
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: const Color(0xFF1E293B)),
                  ),
                  child: Column(
                    children: [
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
                      const SizedBox(height: 22),
                      CustomProgressBar(
                        progress: sharingVm.currentProgress,
                        leftLabel: sharingVm.totalFiles > 0
                            ? 'File ${sharingVm.currentFileIndex} of ${sharingVm.totalFiles}: ${sharingVm.currentFileName}'
                            : 'Starting session...',
                        rightLabel: '${(sharingVm.transferredBytes / (1024 * 1024)).toStringAsFixed(1)} / ${(sharingVm.totalBytes / (1024 * 1024)).toStringAsFixed(1)} MB (ETA: ${sharingVm.etaSeconds}s)',
                      ),
                    ],
                  ),
                ),
              ),

              const SizedBox(width: 20),

              // Terminal Log View
              Expanded(
                flex: 5,
                child: TerminalLogView(
                  logs: sharingVm.logs,
                  height: 270,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
