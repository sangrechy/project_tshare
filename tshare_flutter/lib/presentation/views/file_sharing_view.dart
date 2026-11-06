import 'package:flutter/material.dart';
import '../../core/constants/app_constants.dart';
import '../../core/theme/app_theme.dart';
import '../viewmodels/app_viewmodel.dart';
import '../viewmodels/sharing_viewmodel.dart';
import '../widgets/circular_telemetry_gauge.dart';
import '../widgets/custom_progress_bar.dart';
import '../widgets/rotary_dial_widget.dart';
import '../widgets/terminal_log_view.dart';

class FileSharingView extends StatefulWidget {
  final AppViewModel appVm;
  final SharingViewModel sharingVm;

  const FileSharingView({
    super.key,
    required this.appVm,
    required this.sharingVm,
  });

  @override
  State<FileSharingView> createState() => _FileSharingViewState();
}

class _FileSharingViewState extends State<FileSharingView> {
  final TextEditingController _ipController = TextEditingController();
  final TextEditingController _pathController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _ipController.text = widget.sharingVm.manualIp;
  }

  @override
  void didUpdateWidget(covariant FileSharingView oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.sharingVm.manualIp != _ipController.text && widget.sharingVm.manualIp.isNotEmpty) {
      _ipController.text = widget.sharingVm.manualIp;
    }
  }

  @override
  void dispose() {
    _ipController.dispose();
    _pathController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedSwitcher(
      duration: const Duration(milliseconds: 300),
      child: _buildStageContent(context),
    );
  }

  Widget _buildStageContent(BuildContext context) {
    switch (widget.sharingVm.stage) {
      case 1:
        return _buildStage1Rotary(context);
      case 2:
        return _buildStage2Connection(context);
      case 3:
      default:
        return _buildStage3Dashboard(context);
    }
  }

  // =========================================================================
  // STAGE 1: AUTHENTIC ROTARY TELEPHONE DIAL & 3-COLUMN SELECTION INTERFACE
  // [LEFT: SEND & RECEIVE]  [CENTER: ROTARY TELEPHONE]  [RIGHT: WIFI/ETH/BLE]
  // =========================================================================
  Widget _buildStage1Rotary(BuildContext context) {
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Top Section Header
            const Text(
              'ROTARY TELEPHONE SELECTOR',
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w900,
                color: Colors.white,
                letterSpacing: 2.0,
              ),
            ),
            const SizedBox(height: 6),
            const Text(
              'Select transmission action and medium using the authentic rotary phone dial or the wing panels.',
              style: TextStyle(fontSize: 12, color: AppTheme.themeTextSecondary),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 28),

            // 3-Panel Console: Left (SEND/RECEIVE), Center (ROTARY DIAL), Right (WIFI/ETH/BLE)
            Wrap(
              alignment: WrapAlignment.center,
              crossAxisAlignment: WrapCrossAlignment.center,
              spacing: 28,
              runSpacing: 28,
              children: [
                // -----------------------------------------------------------
                // LEFT WING: ACTION (SEND / RECEIVE)
                // -----------------------------------------------------------
                _buildActionWing(context),

                // -----------------------------------------------------------
                // CENTER: ROTARY TELEPHONE DIAL
                // -----------------------------------------------------------
                _buildRotaryCenter(context),

                // -----------------------------------------------------------
                // RIGHT WING: CONNECTION (WIFI / ETHERNET / BLE)
                // -----------------------------------------------------------
                _buildConnectionWing(context),
              ],
            ),

            const SizedBox(height: 32),

            // Bottom Confirmation Bar
            Container(
              constraints: const BoxConstraints(maxWidth: 960),
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
              decoration: BoxDecoration(
                color: AppTheme.themeCardBg,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: AppTheme.themeCardBorder),
              ),
              child: Row(
                children: [
                  const Icon(Icons.tune_rounded, color: Colors.white, size: 20),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'CONFIGURED MODE',
                          style: TextStyle(
                            fontSize: 10,
                            fontWeight: FontWeight.w800,
                            color: AppTheme.themeTextSecondary,
                            letterSpacing: 1.0,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          '${widget.sharingVm.selectedAction}  •  ${widget.sharingVm.selectedConnection}',
                          style: const TextStyle(
                            fontSize: 15,
                            fontWeight: FontWeight.w900,
                            color: Colors.white,
                            letterSpacing: 0.5,
                          ),
                        ),
                      ],
                    ),
                  ),
                  ElevatedButton.icon(
                    onPressed: () => widget.sharingVm.confirmRotarySelection(widget.appVm.downloadDirectory),
                    icon: const Icon(Icons.arrow_forward_rounded, size: 16, color: Colors.black),
                    label: Text('CONFIRM: ${widget.sharingVm.selectedAction} + ${widget.sharingVm.selectedConnection}'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.white,
                      foregroundColor: Colors.black,
                      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                      elevation: 0,
                      textStyle: const TextStyle(fontWeight: FontWeight.w900, letterSpacing: 0.5),
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

  // Left Wing: ACTION panel
  Widget _buildActionWing(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(maxWidth: 280),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppTheme.themeCardBg,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppTheme.themeCardBorder),
        boxShadow: const [
          BoxShadow(color: Colors.black45, blurRadius: 10, offset: Offset(0, 4)),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              const Icon(Icons.swap_horiz_rounded, size: 18, color: Colors.white),
              const SizedBox(width: 8),
              const Text(
                'ACTION',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w900,
                  color: AppTheme.themeTextSecondary,
                  letterSpacing: 1.5,
                ),
              ),
              const Spacer(),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: const Color(0xFF1C1C1C),
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(color: const Color(0x33FFFFFF)),
                ),
                child: const Text('LEFT', style: TextStyle(fontSize: 9, color: Color(0xFFAAAAAA), fontWeight: FontWeight.w700)),
              ),
            ],
          ),
          const SizedBox(height: 16),
          _buildOptionCard(
            number: '1',
            title: 'SEND',
            subtitle: 'Transmit local files to peer',
            icon: Icons.upload_rounded,
            isSelected: widget.sharingVm.selectedAction == 'SEND',
            onTap: () => widget.sharingVm.selectAction('SEND'),
          ),
          const SizedBox(height: 12),
          _buildOptionCard(
            number: '2',
            title: 'RECEIVE',
            subtitle: 'Listen & accept incoming files',
            icon: Icons.download_rounded,
            isSelected: widget.sharingVm.selectedAction == 'RECEIVE',
            onTap: () => widget.sharingVm.selectAction('RECEIVE'),
          ),
        ],
      ),
    );
  }

  // Center: Authentic Rotary Phone Dial
  Widget _buildRotaryCenter(BuildContext context) {
    return ConstrainedBox(
      constraints: const BoxConstraints(maxWidth: 380),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          RotaryDialWidget(
            selectedAction: widget.sharingVm.selectedAction,
            selectedConnection: widget.sharingVm.selectedConnection,
            onActionChanged: (act) => widget.sharingVm.selectAction(act),
            onConnectionChanged: (conn) => widget.sharingVm.selectConnection(conn),
            onConfirm: () => widget.sharingVm.confirmRotarySelection(widget.appVm.downloadDirectory),
            size: 360,
          ),
        ],
      ),
    );
  }

  // Right Wing: CONNECTION panel
  Widget _buildConnectionWing(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(maxWidth: 280),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppTheme.themeCardBg,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppTheme.themeCardBorder),
        boxShadow: const [
          BoxShadow(color: Colors.black45, blurRadius: 10, offset: Offset(0, 4)),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              const Icon(Icons.settings_input_antenna_rounded, size: 18, color: Colors.white),
              const SizedBox(width: 8),
              const Text(
                'CONNECTION',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w900,
                  color: AppTheme.themeTextSecondary,
                  letterSpacing: 1.5,
                ),
              ),
              const Spacer(),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: const Color(0xFF1C1C1C),
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(color: const Color(0x33FFFFFF)),
                ),
                child: const Text('RIGHT', style: TextStyle(fontSize: 9, color: Color(0xFFAAAAAA), fontWeight: FontWeight.w700)),
              ),
            ],
          ),
          const SizedBox(height: 16),
          _buildOptionCard(
            number: '3',
            title: 'WIFI',
            subtitle: 'High-speed Local Area Network',
            icon: Icons.wifi_rounded,
            isSelected: widget.sharingVm.selectedConnection == 'WIFI',
            onTap: () => widget.sharingVm.selectConnection('WIFI'),
          ),
          const SizedBox(height: 10),
          _buildOptionCard(
            number: '4',
            title: 'ETHERNET',
            subtitle: 'Direct gigabit wired network',
            icon: Icons.settings_ethernet_rounded,
            isSelected: widget.sharingVm.selectedConnection == 'ETHERNET',
            onTap: () => widget.sharingVm.selectConnection('ETHERNET'),
          ),
          const SizedBox(height: 10),
          _buildOptionCard(
            number: '5',
            title: 'BLE',
            subtitle: 'Bluetooth Low Energy discovery',
            icon: Icons.bluetooth_rounded,
            isSelected: widget.sharingVm.selectedConnection == 'BLE',
            onTap: () => widget.sharingVm.selectConnection('BLE'),
          ),
        ],
      ),
    );
  }

  Widget _buildOptionCard({
    required String number,
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
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        decoration: BoxDecoration(
          color: isSelected ? AppTheme.themeCardBgElevated : AppTheme.themeInnerBoxBg,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
            color: isSelected ? Colors.white : AppTheme.themeInnerBoxBorder,
            width: isSelected ? 1.5 : 1,
          ),
        ),
        child: Row(
          children: [
            Container(
              width: 22,
              height: 22,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: isSelected ? Colors.white : const Color(0xFF1E1E1E),
                shape: BoxShape.circle,
                border: Border.all(color: isSelected ? Colors.white : const Color(0x33FFFFFF)),
              ),
              child: Text(
                number,
                style: TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w900,
                  color: isSelected ? Colors.black : Colors.white,
                  fontFamily: 'monospace',
                ),
              ),
            ),
            const SizedBox(width: 10),
            Icon(icon, size: 20, color: isSelected ? Colors.white : AppTheme.themeTextSecondary),
            const SizedBox(width: 10),
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
                  Text(
                    subtitle,
                    style: const TextStyle(fontSize: 10.5, color: AppTheme.themeTextMuted),
                  ),
                ],
              ),
            ),
            if (isSelected)
              const Icon(Icons.check_circle_rounded, color: Colors.white, size: 16),
          ],
        ),
      ),
    );
  }

  // =========================================================================
  // STAGE 2: DEVICE CONNECTION, DIRECT FILE SELECTION, & BACKEND TESTING
  // =========================================================================
  Widget _buildStage2Connection(BuildContext context) {
    final isSend = widget.sharingVm.selectedAction == 'SEND';
    final hasFiles = widget.sharingVm.selectedFiles.isNotEmpty;
    final hasIp = widget.sharingVm.manualIp.trim().isNotEmpty || widget.sharingVm.targetDevice != null;
    final isReadyToTransfer = hasFiles && hasIp;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header Bar
          Row(
            children: [
              IconButton(
                onPressed: () => widget.sharingVm.resetToRotary(),
                icon: const Icon(Icons.arrow_back_rounded, color: Colors.white),
                tooltip: 'Back to Rotary Selector',
              ),
              const SizedBox(width: 8),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('DEVICE CONNECTION', style: TextStyle(fontSize: 17, fontWeight: FontWeight.w900, color: Colors.white)),
                  Text(
                    'Active Mode: ${widget.sharingVm.selectedAction}  •  Medium: ${widget.sharingVm.selectedConnection}',
                    style: const TextStyle(fontSize: 12, color: AppTheme.themeTextSecondary, fontWeight: FontWeight.w600),
                  ),
                ],
              ),
              const Spacer(),
              if (isSend)
                ElevatedButton.icon(
                  onPressed: isReadyToTransfer
                      ? () => widget.sharingVm.initiateSendTransfer(hashMode: widget.appVm.defaultHashMode)
                      : (hasFiles
                          ? () {
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(
                                  content: Text('Please enter a Target IP address (or click USE 127.0.0.1 for loopback test)'),
                                  backgroundColor: Color(0xFF222222),
                                ),
                              );
                            }
                          : () {
                              widget.sharingVm.addTestPayload();
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(
                                  content: Text('Added sample test file. Enter Target IP or click USE 127.0.0.1 to transfer!'),
                                  backgroundColor: Color(0xFF222222),
                                ),
                              );
                            }),
                  icon: Icon(
                    Icons.send_rounded,
                    size: 16,
                    color: isReadyToTransfer ? Colors.black : Colors.white,
                  ),
                  label: Text(
                    isReadyToTransfer
                        ? 'START TRANSFER (${widget.sharingVm.selectedFiles.length} item${widget.sharingVm.selectedFiles.length == 1 ? '' : 's'})'
                        : (!hasFiles ? '+ ADD SAMPLE FILE & TEST' : 'ENTER TARGET IP'),
                  ),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: isReadyToTransfer ? Colors.white : const Color(0xFF242424),
                    foregroundColor: isReadyToTransfer ? Colors.black : Colors.white,
                    side: isReadyToTransfer ? BorderSide.none : const BorderSide(color: Color(0x33FFFFFF)),
                    padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                  ),
                )
              else
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                  decoration: BoxDecoration(
                    color: const Color(0xFF141414),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: Colors.white),
                  ),
                  child: const Row(
                    children: [
                      Icon(Icons.radio_button_checked, size: 14, color: Colors.white),
                      SizedBox(width: 8),
                      Text('RECEIVER LISTENING', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: Colors.white)),
                    ],
                  ),
                ),
            ],
          ),

          const SizedBox(height: 20),

          // Receiver Incoming Offer Banner
          if (!isSend && widget.sharingVm.receiver.pendingOffer != null)
            Container(
              margin: const EdgeInsets.only(bottom: 20),
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(
                color: AppTheme.themeCardBgElevated,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: Colors.white, width: 1.5),
                boxShadow: const [
                  BoxShadow(color: Colors.black54, blurRadius: 16),
                ],
              ),
              child: Row(
                children: [
                  const Icon(Icons.notifications_active_rounded, color: Colors.white, size: 32),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Incoming Transfer Offer from ${widget.sharingVm.receiver.pendingOffer!.peerName}',
                          style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w800, color: Colors.white),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          '${widget.sharingVm.receiver.pendingOffer!.totalFiles} files (${(widget.sharingVm.receiver.pendingOffer!.totalBytes / (1024 * 1024)).toStringAsFixed(1)} MB) • Integrity: ${widget.sharingVm.receiver.pendingOffer!.hashMode.toUpperCase()}',
                          style: const TextStyle(fontSize: 12, color: AppTheme.themeTextSecondary),
                        ),
                      ],
                    ),
                  ),
                  OutlinedButton(
                    onPressed: () => widget.sharingVm.receiver.pendingOffer?.decline(),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: const Color(0xFFCCCCCC),
                      side: const BorderSide(color: Color(0x28FFFFFF)),
                    ),
                    child: const Text('DECLINE'),
                  ),
                  const SizedBox(width: 12),
                  ElevatedButton(
                    onPressed: () => widget.sharingVm.receiver.pendingOffer?.accept(),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.white,
                      foregroundColor: Colors.black,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                    ),
                    child: const Text('ACCEPT TRANSFER', style: TextStyle(fontWeight: FontWeight.w800)),
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
                        color: AppTheme.themeCardBg,
                        borderRadius: BorderRadius.circular(14),
                        border: Border.all(color: AppTheme.themeCardBorder),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Row(
                            children: [
                              Icon(Icons.tune_rounded, size: 18, color: Colors.white),
                              SizedBox(width: 8),
                              Text(
                                'MANUAL CONNECT',
                                style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: AppTheme.themeTextSecondary, letterSpacing: 1.0),
                              ),
                            ],
                          ),
                          const SizedBox(height: 14),
                          Row(
                            children: [
                              Expanded(
                                flex: 3,
                                child: TextFormField(
                                  controller: _ipController,
                                  onChanged: (val) => widget.sharingVm.setManualIp(val),
                                  style: const TextStyle(fontFamily: 'monospace', fontSize: 13, color: Colors.white),
                                  decoration: InputDecoration(
                                    labelText: 'Target IP Address',
                                    labelStyle: const TextStyle(color: AppTheme.themeTextSecondary),
                                    hintText: 'e.g. 192.168.1.100 or 127.0.0.1',
                                    hintStyle: const TextStyle(color: AppTheme.themeTextMuted),
                                    isDense: true,
                                    filled: true,
                                    fillColor: AppTheme.themeTextFieldBg,
                                    enabledBorder: OutlineInputBorder(
                                      borderRadius: BorderRadius.circular(8),
                                      borderSide: const BorderSide(color: AppTheme.themeTextFieldBorder),
                                    ),
                                    focusedBorder: OutlineInputBorder(
                                      borderRadius: BorderRadius.circular(8),
                                      borderSide: const BorderSide(color: Colors.white),
                                    ),
                                  ),
                                ),
                              ),
                              const SizedBox(width: 10),
                              Expanded(
                                flex: 1,
                                child: TextFormField(
                                  initialValue: '${widget.sharingVm.manualPort}',
                                  readOnly: true,
                                  style: const TextStyle(fontFamily: 'monospace', fontSize: 13, color: Colors.white),
                                  decoration: InputDecoration(
                                    labelText: 'Port',
                                    labelStyle: const TextStyle(color: AppTheme.themeTextSecondary),
                                    isDense: true,
                                    filled: true,
                                    fillColor: AppTheme.themeTextFieldBg,
                                    enabledBorder: OutlineInputBorder(
                                      borderRadius: BorderRadius.circular(8),
                                      borderSide: const BorderSide(color: AppTheme.themeTextFieldBorder),
                                    ),
                                    focusedBorder: OutlineInputBorder(
                                      borderRadius: BorderRadius.circular(8),
                                      borderSide: const BorderSide(color: Colors.white),
                                    ),
                                  ),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 12),
                          // Quick IP Helpers (Localhost 127.0.0.1 shortcut)
                          Row(
                            children: [
                              OutlinedButton.icon(
                                onPressed: () {
                                  _ipController.text = '127.0.0.1';
                                  widget.sharingVm.setLocalhostIp();
                                },
                                icon: const Icon(Icons.loop_rounded, size: 14),
                                label: const Text('USE 127.0.0.1 (LOOPBACK TEST)', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700)),
                                style: OutlinedButton.styleFrom(
                                  foregroundColor: Colors.white,
                                  side: const BorderSide(color: Color(0x33FFFFFF)),
                                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                                ),
                              ),
                              const SizedBox(width: 8),
                              TextButton(
                                onPressed: () {
                                  _ipController.clear();
                                  widget.sharingVm.setManualIp('');
                                },
                                style: TextButton.styleFrom(foregroundColor: AppTheme.themeTextMuted),
                                child: const Text('CLEAR', style: TextStyle(fontSize: 11)),
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
                        color: AppTheme.themeCardBg,
                        borderRadius: BorderRadius.circular(14),
                        border: Border.all(color: AppTheme.themeCardBorder),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              const Icon(Icons.radar_rounded, size: 18, color: Colors.white),
                              const SizedBox(width: 8),
                              const Text(
                                'AUTO FIND DEVICES',
                                style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: AppTheme.themeTextSecondary, letterSpacing: 1.0),
                              ),
                              const Spacer(),
                              if (widget.sharingVm.isAutoDiscovering)
                                const SizedBox(
                                  width: 14,
                                  height: 14,
                                  child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                                ),
                              const SizedBox(width: 8),
                              TextButton(
                                onPressed: () {
                                  if (widget.sharingVm.isAutoDiscovering) {
                                    widget.sharingVm.stopAutoDiscovery();
                                  } else {
                                    widget.sharingVm.startAutoDiscovery();
                                  }
                                },
                                style: TextButton.styleFrom(foregroundColor: Colors.white),
                                child: Text(widget.sharingVm.isAutoDiscovering ? 'STOP SEARCH' : 'SEARCH PEERS'),
                              ),
                            ],
                          ),
                          const SizedBox(height: 12),
                          if (widget.sharingVm.discoveredDevices.isEmpty)
                            Container(
                              padding: const EdgeInsets.symmetric(vertical: 24),
                              alignment: Alignment.center,
                              child: Text(
                                widget.sharingVm.isAutoDiscovering ? 'Searching for devices on LAN...' : 'No devices discovered. Tap SEARCH PEERS or use Target IP above.',
                                style: const TextStyle(color: AppTheme.themeTextMuted, fontSize: 12),
                              ),
                            )
                          else
                            ListView.separated(
                              shrinkWrap: true,
                              physics: const NeverScrollableScrollPhysics(),
                              itemCount: widget.sharingVm.discoveredDevices.length,
                              separatorBuilder: (_, _) => const Divider(color: AppTheme.themeCardBorder, height: 1),
                              itemBuilder: (context, idx) {
                                final dev = widget.sharingVm.discoveredDevices[idx];
                                final isSelected = widget.sharingVm.targetDevice?.ip == dev.ip;

                                return ListTile(
                                  contentPadding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                  leading: const Icon(Icons.laptop_chromebook_rounded, color: Colors.white),
                                  title: Text(dev.name, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13, color: Colors.white)),
                                  subtitle: Text('${dev.ip}:${dev.port} • ${dev.medium.toUpperCase()}', style: const TextStyle(fontSize: 11, color: AppTheme.themeTextSecondary)),
                                  trailing: ElevatedButton(
                                    onPressed: () {
                                      _ipController.text = dev.ip;
                                      widget.sharingVm.selectDevice(dev);
                                    },
                                    style: ElevatedButton.styleFrom(
                                      backgroundColor: isSelected ? Colors.white : const Color(0xFF161616),
                                      foregroundColor: isSelected ? Colors.black : Colors.white,
                                      side: isSelected ? BorderSide.none : const BorderSide(color: Color(0x28FFFFFF)),
                                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                                    ),
                                    child: Text(isSelected ? 'SELECTED' : 'SELECT', style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700)),
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
                          color: AppTheme.themeCardBg,
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(color: AppTheme.themeCardBorder),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                const Icon(Icons.folder_shared_rounded, size: 18, color: Colors.white),
                                const SizedBox(width: 8),
                                const Text(
                                  'FILES TO SEND',
                                  style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: AppTheme.themeTextSecondary, letterSpacing: 1.0),
                                ),
                                const Spacer(),
                                OutlinedButton.icon(
                                  onPressed: () => widget.sharingVm.pickFiles(),
                                  icon: const Icon(Icons.add, size: 14),
                                  label: const Text('ADD FILES', style: TextStyle(fontSize: 11)),
                                  style: OutlinedButton.styleFrom(
                                    foregroundColor: Colors.white,
                                    side: const BorderSide(color: Color(0x28FFFFFF)),
                                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                                  ),
                                ),
                                const SizedBox(width: 6),
                                OutlinedButton.icon(
                                  onPressed: () => widget.sharingVm.pickDirectory(),
                                  icon: const Icon(Icons.create_new_folder_outlined, size: 14),
                                  label: const Text('ADD FOLDER', style: TextStyle(fontSize: 11)),
                                  style: OutlinedButton.styleFrom(
                                    foregroundColor: Colors.white,
                                    side: const BorderSide(color: Color(0x28FFFFFF)),
                                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                                  ),
                                ),
                                const SizedBox(width: 6),
                                ElevatedButton.icon(
                                  onPressed: () {
                                    widget.sharingVm.addTestPayload();
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      const SnackBar(
                                        content: Text('Added sample test file for transfer testing.'),
                                        backgroundColor: Color(0xFF222222),
                                      ),
                                    );
                                  },
                                  icon: const Icon(Icons.playlist_add_check_rounded, size: 14, color: Colors.black),
                                  label: const Text('+ SAMPLE', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800)),
                                  style: ElevatedButton.styleFrom(
                                    backgroundColor: Colors.white,
                                    foregroundColor: Colors.black,
                                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                                  ),
                                ),
                              ],
                            ),

                            const SizedBox(height: 12),

                            // Direct Manual Fedora File Path Input
                            Row(
                              children: [
                                Expanded(
                                  child: TextFormField(
                                    controller: _pathController,
                                    style: const TextStyle(fontFamily: 'monospace', fontSize: 12, color: Colors.white),
                                    decoration: InputDecoration(
                                      hintText: 'Enter local Fedora file path (e.g. /home/... or /tmp/...)',
                                      hintStyle: const TextStyle(color: AppTheme.themeTextMuted, fontSize: 11),
                                      isDense: true,
                                      contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
                                      filled: true,
                                      fillColor: AppTheme.themeTextFieldBg,
                                      enabledBorder: OutlineInputBorder(
                                        borderRadius: BorderRadius.circular(6),
                                        borderSide: const BorderSide(color: AppTheme.themeTextFieldBorder),
                                      ),
                                      focusedBorder: OutlineInputBorder(
                                        borderRadius: BorderRadius.circular(6),
                                        borderSide: const BorderSide(color: Colors.white),
                                      ),
                                    ),
                                  ),
                                ),
                                const SizedBox(width: 8),
                                OutlinedButton(
                                  onPressed: () async {
                                    final path = _pathController.text.trim();
                                    if (path.isNotEmpty) {
                                      final added = await widget.sharingVm.addManualFilePath(path);
                                      if (added) {
                                        _pathController.clear();
                                      } else {
                                        if (context.mounted) {
                                          ScaffoldMessenger.of(context).showSnackBar(
                                            const SnackBar(
                                              content: Text('Could not find file or directory at specified path'),
                                              backgroundColor: Color(0xFF222222),
                                            ),
                                          );
                                        }
                                      }
                                    }
                                  },
                                  style: OutlinedButton.styleFrom(
                                    foregroundColor: Colors.white,
                                    side: const BorderSide(color: Colors.white),
                                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
                                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                                  ),
                                  child: const Text('ADD PATH', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800)),
                                ),
                              ],
                            ),

                            const SizedBox(height: 14),

                            if (widget.sharingVm.selectedFiles.isEmpty)
                              Container(
                                height: 200,
                                alignment: Alignment.center,
                                decoration: BoxDecoration(
                                  border: Border.all(color: AppTheme.themeCardBorder, style: BorderStyle.solid),
                                  borderRadius: BorderRadius.circular(10),
                                ),
                                child: const Column(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    Icon(Icons.cloud_upload_outlined, size: 36, color: AppTheme.themeTextMuted),
                                    SizedBox(height: 8),
                                    Text('No files selected yet.', style: TextStyle(color: AppTheme.themeTextSecondary, fontSize: 13)),
                                    Text('Tap Add Files, Add Folder, or + SAMPLE above.', style: TextStyle(color: AppTheme.themeTextMuted, fontSize: 11)),
                                  ],
                                ),
                              )
                            else
                              Container(
                                height: 200,
                                decoration: BoxDecoration(
                                  color: AppTheme.themeInnerBoxBg,
                                  borderRadius: BorderRadius.circular(10),
                                  border: Border.all(color: AppTheme.themeInnerBoxBorder),
                                ),
                                child: ListView.separated(
                                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                                  itemCount: widget.sharingVm.selectedFiles.length,
                                  separatorBuilder: (_, _) => const Divider(color: AppTheme.themeCardBorder, height: 1),
                                  itemBuilder: (context, idx) {
                                    final file = widget.sharingVm.selectedFiles[idx];
                                    return ListTile(
                                      dense: true,
                                      leading: Icon(
                                        file.isDirectory ? Icons.folder_rounded : Icons.insert_drive_file_rounded,
                                        color: Colors.white,
                                        size: 18,
                                      ),
                                      title: Text(file.name, style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600, color: Colors.white)),
                                      subtitle: Text(file.formattedSize, style: const TextStyle(fontSize: 11, color: AppTheme.themeTextSecondary)),
                                      trailing: IconButton(
                                        icon: const Icon(Icons.close_rounded, size: 16, color: Color(0xFFCCCCCC)),
                                        onPressed: () => widget.sharingVm.removeFile(idx),
                                      ),
                                    );
                                  },
                                ),
                              ),

                            const SizedBox(height: 10),
                            Row(
                              children: [
                                Text(
                                  'Total: ${widget.sharingVm.selectedFiles.length} item(s)',
                                  style: const TextStyle(fontSize: 11, color: AppTheme.themeTextSecondary, fontWeight: FontWeight.w600),
                                ),
                                const Spacer(),
                                if (widget.sharingVm.selectedFiles.isNotEmpty)
                                  TextButton(
                                    onPressed: () => widget.sharingVm.clearFiles(),
                                    style: TextButton.styleFrom(foregroundColor: AppTheme.themeTextMuted),
                                    child: const Text('CLEAR ALL', style: TextStyle(fontSize: 11)),
                                  ),
                              ],
                            ),
                          ],
                        ),
                      )
                    : Container(
                        padding: const EdgeInsets.all(24),
                        decoration: BoxDecoration(
                          color: AppTheme.themeCardBg,
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(color: AppTheme.themeCardBorder),
                        ),
                        child: Column(
                          children: [
                            const Icon(Icons.cell_tower_rounded, color: Colors.white, size: 48),
                            const SizedBox(height: 16),
                            const Text(
                              'Receiver Server Active',
                              style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800, color: Colors.white),
                            ),
                            const SizedBox(height: 6),
                            Text(
                              'Listening for incoming connections on port ${AppConstants.tcpTransferPort}.\nSender devices on this network will discover this receiver automatically.',
                              style: const TextStyle(fontSize: 12, color: AppTheme.themeTextSecondary, height: 1.4),
                              textAlign: TextAlign.center,
                            ),
                            const SizedBox(height: 20),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                              decoration: BoxDecoration(
                                color: AppTheme.themePillBg,
                                borderRadius: BorderRadius.circular(8),
                                border: Border.all(color: AppTheme.themePillBorder),
                              ),
                              child: Text(
                                'Saving to: ${widget.appVm.downloadDirectory}',
                                style: const TextStyle(fontSize: 11, fontFamily: 'monospace', color: Colors.white),
                              ),
                            ),
                            const SizedBox(height: 24),
                            // Receiver Test Simulator
                            Container(
                              padding: const EdgeInsets.all(14),
                              decoration: BoxDecoration(
                                color: const Color(0xFF141414),
                                borderRadius: BorderRadius.circular(10),
                                border: Border.all(color: const Color(0x28FFFFFF)),
                              ),
                              child: Column(
                                children: [
                                  const Text(
                                    'LOOPBACK / OFFLINE RECEIVER TEST BENCH',
                                    style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: Colors.white, letterSpacing: 0.8),
                                  ),
                                  const SizedBox(height: 6),
                                  const Text(
                                    'Test accept/decline banners & protocol integrity without needing a second computer.',
                                    style: TextStyle(fontSize: 11, color: AppTheme.themeTextMuted),
                                    textAlign: TextAlign.center,
                                  ),
                                  const SizedBox(height: 12),
                                  ElevatedButton.icon(
                                    onPressed: () => widget.sharingVm.simulateTestOffer(),
                                    icon: const Icon(Icons.play_arrow_rounded, size: 16, color: Colors.black),
                                    label: const Text('SIMULATE INCOMING OFFER'),
                                    style: ElevatedButton.styleFrom(
                                      backgroundColor: Colors.white,
                                      foregroundColor: Colors.black,
                                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                                    ),
                                  ),
                                ],
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

  // =========================================================================
  // STAGE 3: REAL-TIME TELEMETRY DASHBOARD & PROTOCOL AUDIT LOGS
  // =========================================================================
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
              color: AppTheme.themeCardBg,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: AppTheme.themeCardBorder),
            ),
            child: Row(
              children: [
                Icon(
                  widget.sharingVm.isCompleted
                      ? Icons.check_circle_rounded
                      : (widget.sharingVm.isError ? Icons.error_outline_rounded : Icons.sync_rounded),
                  color: Colors.white,
                  size: 24,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        widget.sharingVm.isCompleted
                            ? 'TRANSFER COMPLETE'
                            : (widget.sharingVm.isError ? 'TRANSFER ERROR' : 'TRANSFER IN PROGRESS'),
                        style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w800, color: Colors.white),
                      ),
                      Text(
                        '${widget.sharingVm.selectedAction} via ${widget.sharingVm.selectedConnection} • Peer: ${widget.sharingVm.peerName} • Integrity: ${widget.sharingVm.activeHashMode.toUpperCase()}',
                        style: const TextStyle(fontSize: 12, color: AppTheme.themeTextSecondary),
                      ),
                    ],
                  ),
                ),
                if (widget.sharingVm.isTransferring)
                  OutlinedButton.icon(
                    onPressed: () => widget.sharingVm.cancelTransfer(),
                    icon: const Icon(Icons.cancel_outlined, size: 16),
                    label: const Text('CANCEL'),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: const Color(0xFFCCCCCC),
                      side: const BorderSide(color: Color(0x28FFFFFF)),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                    ),
                  )
                else
                  ElevatedButton.icon(
                    onPressed: () => widget.sharingVm.resetToRotary(),
                    icon: const Icon(Icons.refresh_rounded, size: 16, color: Colors.black),
                    label: const Text('NEW TRANSFER'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.white,
                      foregroundColor: Colors.black,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                    ),
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
                    color: AppTheme.themeCardBg,
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: AppTheme.themeCardBorder),
                  ),
                  child: Column(
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceAround,
                        children: [
                          CircularTelemetryGauge(
                            value: widget.sharingVm.currentSpeedMbps,
                            maxValue: 200,
                            label: 'Speed',
                            unit: 'MB/s',
                            primaryColor: Colors.white,
                          ),
                          CircularTelemetryGauge(
                            value: widget.sharingVm.currentCpuPercent,
                            maxValue: 100,
                            label: 'CPU',
                            unit: '%',
                            primaryColor: AppTheme.themeAccentSilver,
                          ),
                        ],
                      ),
                      const SizedBox(height: 22),
                      CustomProgressBar(
                        progress: widget.sharingVm.currentProgress,
                        leftLabel: widget.sharingVm.totalFiles > 0
                            ? 'File ${widget.sharingVm.currentFileIndex} of ${widget.sharingVm.totalFiles}: ${widget.sharingVm.currentFileName}'
                            : 'Starting session...',
                        rightLabel: '${(widget.sharingVm.transferredBytes / (1024 * 1024)).toStringAsFixed(1)} / ${(widget.sharingVm.totalBytes / (1024 * 1024)).toStringAsFixed(1)} MB (ETA: ${widget.sharingVm.etaSeconds}s)',
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
                  logs: widget.sharingVm.logs,
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
