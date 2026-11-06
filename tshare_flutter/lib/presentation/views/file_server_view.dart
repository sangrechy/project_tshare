import 'package:flutter/material.dart';
import 'package:qr_flutter/qr_flutter.dart';
import '../viewmodels/server_viewmodel.dart';

class FileServerView extends StatelessWidget {
  final ServerViewModel serverVm;

  const FileServerView({
    super.key,
    required this.serverVm,
  });

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Top Control Card
          Container(
            padding: const EdgeInsets.all(22),
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
                    color: (serverVm.isRunning ? const Color(0xFF10B981) : const Color(0xFF64748B)).withAlpha(40),
                    shape: BoxShape.circle,
                  ),
                  child: Icon(
                    Icons.public_rounded,
                    color: serverVm.isRunning ? const Color(0xFF10B981) : const Color(0xFF94A3B8),
                    size: 32,
                  ),
                ),
                const SizedBox(width: 18),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          const Text(
                            'EMBEDDED LAN FILE SERVER',
                            style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800, color: Colors.white),
                          ),
                          const SizedBox(width: 12),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
                            decoration: BoxDecoration(
                              color: (serverVm.isRunning ? const Color(0xFF10B981) : const Color(0xFFEF4444)).withAlpha(40),
                              borderRadius: BorderRadius.circular(6),
                              border: Border.all(
                                color: serverVm.isRunning ? const Color(0xFF10B981) : const Color(0xFFEF4444),
                              ),
                            ),
                            child: Text(
                              serverVm.isRunning ? 'RUNNING' : 'STOPPED',
                              style: TextStyle(
                                fontSize: 10,
                                fontWeight: FontWeight.w900,
                                color: serverVm.isRunning ? const Color(0xFF10B981) : const Color(0xFFEF4444),
                                letterSpacing: 1.0,
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Text(
                        serverVm.isRunning
                            ? 'Web portal accessible on LAN at ${serverVm.portalUrl}'
                            : 'Host files over HTTP for any phone, tablet, or PC browser without installing an app.',
                        style: const TextStyle(fontSize: 12, color: Color(0xFF94A3B8)),
                      ),
                    ],
                  ),
                ),
                ElevatedButton.icon(
                  onPressed: () => serverVm.toggleServer(),
                  icon: Icon(serverVm.isRunning ? Icons.stop_rounded : Icons.play_arrow_rounded, size: 18),
                  label: Text(serverVm.isRunning ? 'STOP SERVER' : 'START SERVER'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: serverVm.isRunning ? const Color(0xFFEF4444) : const Color(0xFF10B981),
                    padding: const EdgeInsets.symmetric(horizontal: 22, vertical: 14),
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(height: 24),

          // Portal URL & Mobile QR Code + Shared Folder Row
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Mobile QR Code Box
              Expanded(
                flex: 4,
                child: Container(
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    color: const Color(0xFF111827),
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: const Color(0xFF1E293B)),
                  ),
                  child: Column(
                    children: [
                      const Row(
                        children: [
                          Icon(Icons.qr_code_scanner_rounded, size: 18, color: Color(0xFF38BDF8)),
                          SizedBox(width: 8),
                          Text(
                            'MOBILE QR CODE',
                            style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: Color(0xFF94A3B8), letterSpacing: 1.0),
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: QrImageView(
                          data: serverVm.portalUrl,
                          version: QrVersions.auto,
                          size: 160.0,
                        ),
                      ),
                      const SizedBox(height: 14),
                      Text(
                        serverVm.portalUrl,
                        style: const TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w700,
                          color: Color(0xFF38BDF8),
                          fontFamily: 'monospace',
                        ),
                      ),
                      const SizedBox(height: 4),
                      const Text(
                        'Scan with phone camera to download / upload files',
                        style: TextStyle(fontSize: 11, color: Color(0xFF64748B)),
                        textAlign: TextAlign.center,
                      ),
                    ],
                  ),
                ),
              ),

              const SizedBox(width: 20),

              // Server Settings & Shared Files List
              Expanded(
                flex: 6,
                child: Column(
                  children: [
                    // Shared Directory Configuration
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
                              const Icon(Icons.folder_shared_rounded, size: 18, color: Color(0xFF38BDF8)),
                              const SizedBox(width: 8),
                              const Text(
                                'SHARED FOLDER',
                                style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: Color(0xFF94A3B8), letterSpacing: 1.0),
                              ),
                              const Spacer(),
                              OutlinedButton.icon(
                                onPressed: () => serverVm.pickSharedFolder(),
                                icon: const Icon(Icons.folder_open_rounded, size: 14),
                                label: const Text('CHANGE FOLDER', style: TextStyle(fontSize: 11)),
                              ),
                            ],
                          ),
                          const SizedBox(height: 10),
                          Text(
                            serverVm.sharedFolder,
                            style: const TextStyle(fontFamily: 'monospace', fontSize: 12, color: Colors.white),
                          ),
                          const SizedBox(height: 14),
                          Material(
                            type: MaterialType.transparency,
                            child: SwitchListTile(
                              contentPadding: EdgeInsets.zero,
                              title: const Text('Allow Mobile Uploads', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700)),
                              subtitle: const Text('Permit connected devices to upload files into your folder', style: TextStyle(fontSize: 11, color: Color(0xFF94A3B8))),
                              value: serverVm.allowUploads,
                              onChanged: (val) => serverVm.setAllowUploads(val),
                            ),
                          ),
                        ],
                      ),
                    ),

                    const SizedBox(height: 18),

                    // Shared Files List
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
                              const Icon(Icons.list_alt_rounded, size: 18, color: Color(0xFF38BDF8)),
                              const SizedBox(width: 8),
                              Text(
                                'FILES IN HOSTED FOLDER (${serverVm.sharedFiles.length})',
                                style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: Color(0xFF94A3B8), letterSpacing: 1.0),
                              ),
                              const Spacer(),
                              IconButton(
                                icon: const Icon(Icons.refresh_rounded, size: 18, color: Color(0xFF94A3B8)),
                                onPressed: () => serverVm.refreshFiles(),
                                tooltip: 'Refresh File List',
                              ),
                            ],
                          ),
                          const SizedBox(height: 10),
                          if (serverVm.sharedFiles.isEmpty)
                            Container(
                              height: 130,
                              alignment: Alignment.center,
                              child: const Text('No files currently in shared folder.', style: TextStyle(color: Color(0xFF64748B), fontSize: 12)),
                            )
                          else
                            Container(
                              height: 140,
                              decoration: BoxDecoration(
                                color: const Color(0xFF0F172A),
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: ListView.separated(
                                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                                itemCount: serverVm.sharedFiles.length,
                                separatorBuilder: (_, _) => const Divider(color: Color(0xFF1E293B), height: 1),
                                itemBuilder: (context, idx) {
                                  final file = serverVm.sharedFiles[idx];
                                  return ListTile(
                                    dense: true,
                                    leading: const Icon(Icons.insert_drive_file_rounded, color: Color(0xFF38BDF8), size: 16),
                                    title: Text(file.name, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
                                    trailing: Text(file.formattedSize, style: const TextStyle(fontSize: 11, color: Color(0xFF94A3B8))),
                                  );
                                },
                              ),
                            ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
