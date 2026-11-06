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
                        color: AppTheme.themeTopBarBg,
                        border: Border(
                          bottom: BorderSide(color: AppTheme.themeTopBarBorder, width: 1),
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
                                  color: AppTheme.themeCardBgElevated,
                                  borderRadius: BorderRadius.circular(8),
                                  border: Border.all(color: AppTheme.themeCardBorder),
                                ),
                                child: const Icon(Icons.bolt_rounded, color: AppTheme.themeTextPrimary, size: 20),
                              ),
                              if (!isMobile) ...[
                                const SizedBox(width: 10),
                                const Text(
                                  'TSHARE',
                                  style: TextStyle(
                                    fontSize: 18,
                                    fontWeight: FontWeight.w900,
                                    letterSpacing: 2.0,
                                    color: AppTheme.themeTextPrimary,
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
                                          color: isSelected ? AppTheme.themeCardBgElevated : Colors.transparent,
                                          borderRadius: BorderRadius.circular(8),
                                          border: isSelected
                                              ? Border.all(color: AppTheme.themeCardBorder, width: 1)
                                              : null,
                                        ),
                                        child: Row(
                                          mainAxisSize: MainAxisSize.min,
                                          children: [
                                            Icon(
                                              item['icon'] as IconData,
                                              size: 16,
                                              color: isSelected ? AppTheme.themeTextPrimary : AppTheme.themeTextSecondary,
                                            ),
                                            const SizedBox(width: 8),
                                            Text(
                                              item['label'] as String,
                                              style: TextStyle(
                                                fontSize: 12.5,
                                                fontWeight: isSelected ? FontWeight.w900 : FontWeight.w600,
                                                color: isSelected ? AppTheme.themeTextPrimary : AppTheme.themeTextSecondary,
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
                              color: AppTheme.themePillBg,
                              borderRadius: BorderRadius.circular(6),
                              border: Border.all(color: AppTheme.themePillBorder),
                            ),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Container(
                                  width: 7,
                                  height: 7,
                                  decoration: BoxDecoration(
                                    shape: BoxShape.circle,
                                    color: _sharingVm.isTransferring ? AppTheme.themeTextPrimary : AppTheme.themeTextSecondary,
                                  ),
                                ),
                                const SizedBox(width: 6),
                                Text(
                                  _sharingVm.isTransferring ? 'STREAMING' : 'READY',
                                  style: TextStyle(
                                    fontSize: 10,
                                    fontWeight: FontWeight.w800,
                                    letterSpacing: 0.8,
                                    color: _sharingVm.isTransferring ? AppTheme.themeTextPrimary : AppTheme.themeTextSecondary,
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
