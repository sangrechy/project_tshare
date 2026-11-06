import 'package:flutter/material.dart';
import 'core/theme/app_theme.dart';
import 'presentation/viewmodels/app_viewmodel.dart';
import 'presentation/viewmodels/server_viewmodel.dart';
import 'presentation/viewmodels/sharing_viewmodel.dart';
import 'presentation/viewmodels/verify_viewmodel.dart';
import 'presentation/views/file_server_view.dart';
import 'presentation/views/file_sharing_view.dart';
import 'presentation/views/home_view.dart';
import 'presentation/views/settings_view.dart';
import 'presentation/views/verify_view.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const TShareApp());
}

class TShareApp extends StatelessWidget {
  const TShareApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'TShare - High-Speed Cross-Platform File Sharing',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.darkTheme,
      home: const TShareShell(),
    );
  }
}

class TShareShell extends StatefulWidget {
  const TShareShell({super.key});

  @override
  State<TShareShell> createState() => _TShareShellState();
}

class _TShareShellState extends State<TShareShell> {
  late final AppViewModel _appVm;
  late final SharingViewModel _sharingVm;
  late final ServerViewModel _serverVm;
  late final VerifyViewModel _verifyVm;

  @override
  void initState() {
    super.initState();
    _appVm = AppViewModel();
    _sharingVm = SharingViewModel();
    _serverVm = ServerViewModel();
    _verifyVm = VerifyViewModel();
  }

  @override
  void dispose() {
    _appVm.dispose();
    _sharingVm.dispose();
    _serverVm.dispose();
    _verifyVm.dispose();
    super.dispose();
  }

  static const List<Map<String, dynamic>> _navItems = [
    {'label': 'HOME', 'icon': Icons.speed_rounded},
    {'label': 'FILE SHARING', 'icon': Icons.swap_horizontal_circle_outlined},
    {'label': 'FILE SERVER', 'icon': Icons.public_rounded},
    {'label': 'VERIFY', 'icon': Icons.verified_user_rounded},
    {'label': 'SETTINGS', 'icon': Icons.settings_rounded},
  ];

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: Listenable.merge([_appVm, _sharingVm, _serverVm, _verifyVm]),
      builder: (context, _) {
        return Scaffold(
          backgroundColor: AppTheme.bgMain,
          body: SafeArea(
            child: Column(
              children: [
                // ====================================================
                // 1. FIXED TOP NAVIGATION BAR
                // ====================================================
                LayoutBuilder(
                  builder: (context, constraints) {
                    final isMobile = constraints.maxWidth < 768;
                    return Container(
                      height: 64,
                      decoration: const BoxDecoration(
                        color: Color(0xFF0F172A),
                        border: Border(
                          bottom: BorderSide(color: Color(0xFF1E293B), width: 1.5),
                        ),
                      ),
                      padding: EdgeInsets.symmetric(horizontal: isMobile ? 12 : 24),
                      child: Row(
                        children: [
                          // Branding & Logo
                          Row(
                            children: [
                              Container(
                                padding: const EdgeInsets.all(7),
                                decoration: BoxDecoration(
                                  gradient: const LinearGradient(
                                    colors: [Color(0xFF0284C7), Color(0xFF38BDF8)],
                                  ),
                                  borderRadius: BorderRadius.circular(8),
                                ),
                                child: const Icon(Icons.bolt_rounded, color: Colors.white, size: 20),
                              ),
                              if (!isMobile) ...[
                                const SizedBox(width: 10),
                                const Text(
                                  'TSHARE',
                                  style: TextStyle(
                                    fontSize: 18,
                                    fontWeight: FontWeight.w900,
                                    letterSpacing: 2.0,
                                    color: Colors.white,
                                  ),
                                ),
                              ],
                            ],
                          ),

                          SizedBox(width: isMobile ? 12 : 36),

                          // Fixed 5 Top Menus (Scrollable on small screens)
                          Expanded(
                            child: SingleChildScrollView(
                              scrollDirection: Axis.horizontal,
                              physics: const BouncingScrollPhysics(),
                              child: Row(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: List.generate(_navItems.length, (index) {
                                  final item = _navItems[index];
                                  final isSelected = _appVm.currentNavIndex == index;

                                  return Padding(
                                    padding: EdgeInsets.symmetric(horizontal: isMobile ? 4 : 8),
                                    child: InkWell(
                                      onTap: () => _appVm.setNavIndex(index),
                                      borderRadius: BorderRadius.circular(8),
                                      child: Container(
                                        padding: EdgeInsets.symmetric(
                                          horizontal: isMobile ? 10 : 16,
                                          vertical: isMobile ? 8 : 10,
                                        ),
                                        decoration: BoxDecoration(
                                          color: isSelected ? const Color(0xFF0284C7).withAlpha(40) : Colors.transparent,
                                          borderRadius: BorderRadius.circular(8),
                                          border: isSelected
                                              ? Border.all(color: const Color(0xFF38BDF8), width: 1.5)
                                              : null,
                                        ),
                                        child: Row(
                                          mainAxisSize: MainAxisSize.min,
                                          children: [
                                            Icon(
                                              item['icon'] as IconData,
                                              size: 16,
                                              color: isSelected ? const Color(0xFF38BDF8) : const Color(0xFF94A3B8),
                                            ),
                                            const SizedBox(width: 8),
                                            Text(
                                              item['label'] as String,
                                              style: TextStyle(
                                                fontSize: 12.5,
                                                fontWeight: isSelected ? FontWeight.w900 : FontWeight.w700,
                                                color: isSelected ? Colors.white : const Color(0xFF94A3B8),
                                                letterSpacing: 1.0,
                                              ),
                                            ),
                                          ],
                                        ),
                                      ),
                                    ),
                                  );
                                }),
                              ),
                            ),
                          ),

                          if (!isMobile) const SizedBox(width: 16),

                      // Right Status Badge
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                        decoration: BoxDecoration(
                          color: (_sharingVm.isTransferring ? const Color(0xFF10B981) : const Color(0xFF1E293B)).withAlpha(40),
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(
                            color: _sharingVm.isTransferring ? const Color(0xFF10B981) : const Color(0xFF334155),
                          ),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Container(
                              width: 8,
                              height: 8,
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                color: _sharingVm.isTransferring ? const Color(0xFF10B981) : const Color(0xFF38BDF8),
                              ),
                            ),
                            const SizedBox(width: 6),
                            Text(
                              _sharingVm.isTransferring ? 'STREAMING' : 'READY',
                              style: TextStyle(
                                fontSize: 10,
                                fontWeight: FontWeight.w800,
                                letterSpacing: 0.8,
                                color: _sharingVm.isTransferring ? const Color(0xFF10B981) : const Color(0xFF38BDF8),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                );
              },
            ),

                // ====================================================
                // 2. ACTIVE PAGE CONTENT
                // ====================================================
                Expanded(
                  child: IndexedStack(
                    index: _appVm.currentNavIndex,
                    children: [
                      HomeView(appVm: _appVm, sharingVm: _sharingVm),
                      FileSharingView(appVm: _appVm, sharingVm: _sharingVm),
                      FileServerView(serverVm: _serverVm),
                      VerifyView(verifyVm: _verifyVm),
                      SettingsView(appVm: _appVm),
                    ],
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}
