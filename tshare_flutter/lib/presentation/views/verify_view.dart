import 'package:flutter/material.dart';
import '../../core/theme/app_theme.dart';
import '../../data/models/audit_result.dart';
import '../viewmodels/verify_viewmodel.dart';

class VerifyView extends StatelessWidget {
  final VerifyViewModel verifyVm;

  const VerifyView({
    super.key,
    required this.verifyVm,
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
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppTheme.themeInnerBoxBg,
                    shape: BoxShape.circle,
                    border: Border.all(color: AppTheme.themeCardBorder),
                  ),
                  child: const Icon(Icons.verified_user_rounded, color: Colors.white, size: 32),
                ),
                const SizedBox(width: 16),
                const Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'PAIRWISE SHA-256 AUDIT & VERIFICATION',
                        style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800, color: Colors.white),
                      ),
                      SizedBox(height: 4),
                      Text(
                        'Compare two files chunk-by-chunk using cryptographic SHA-256 digests to verify 100% bit-for-bit authenticity.',
                        style: TextStyle(fontSize: 12, color: AppTheme.themeTextSecondary),
                      ),
                    ],
                  ),
                ),
                if (verifyVm.originalPath != null || verifyVm.receivedPath != null)
                  OutlinedButton.icon(
                    onPressed: () => verifyVm.reset(),
                    icon: const Icon(Icons.refresh_rounded, size: 16),
                    label: const Text('RESET'),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: Colors.white,
                      side: const BorderSide(color: Color(0x28FFFFFF)),
                    ),
                  ),
              ],
            ),
          ),

          const SizedBox(height: 24),

          // Side-by-side Selectors
          Row(
            children: [
              // Original File
              Expanded(
                child: _buildFilePickerCard(
                  title: '1. ORIGINAL FILE',
                  filename: verifyVm.originalName,
                  path: verifyVm.originalPath,
                  sizeBytes: verifyVm.originalSize,
                  icon: Icons.file_present_rounded,
                  accentColor: Colors.white,
                  buttonLabel: 'SELECT ORIGINAL',
                  onSelect: () => verifyVm.pickOriginalFile(),
                ),
              ),

              const SizedBox(width: 20),

              // Received File
              Expanded(
                child: _buildFilePickerCard(
                  title: '2. RECEIVED / TARGET FILE',
                  filename: verifyVm.receivedName,
                  path: verifyVm.receivedPath,
                  sizeBytes: verifyVm.receivedSize,
                  icon: Icons.download_done_rounded,
                  accentColor: AppTheme.themeAccentSilver,
                  buttonLabel: 'SELECT RECEIVED',
                  onSelect: () => verifyVm.pickReceivedFile(),
                ),
              ),
            ],
          ),

          const SizedBox(height: 24),

          // Verify Action Button
          Center(
            child: SizedBox(
              width: 280,
              height: 48,
              child: ElevatedButton.icon(
                onPressed: (verifyVm.originalPath == null || verifyVm.receivedPath == null || verifyVm.isVerifying)
                    ? null
                    : () => verifyVm.runVerification(),
                icon: verifyVm.isVerifying
                    ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black))
                    : const Icon(Icons.fingerprint_rounded, size: 20, color: Colors.black),
                label: Text(
                  verifyVm.isVerifying ? 'CALCULATING HASHES...' : 'VERIFY INTEGRITY',
                  style: const TextStyle(fontWeight: FontWeight.w800, letterSpacing: 0.8),
                ),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.white,
                  foregroundColor: Colors.black,
                  disabledBackgroundColor: const Color(0xFF222222),
                  disabledForegroundColor: const Color(0xFF666666),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                  elevation: 0,
                ),
              ),
            ),
          ),

          const SizedBox(height: 24),

          // Audit Results Banner
          if (verifyVm.result != null)
            _buildResultBanner(verifyVm.result!),
        ],
      ),
    );
  }

  Widget _buildFilePickerCard({
    required String title,
    required String? filename,
    required String? path,
    required int sizeBytes,
    required IconData icon,
    required Color accentColor,
    required String buttonLabel,
    required VoidCallback onSelect,
  }) {
    final hasFile = filename != null && path != null;

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppTheme.themeCardBg,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: hasFile ? Colors.white : AppTheme.themeCardBorder,
          width: hasFile ? 1.5 : 1,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, color: Colors.white, size: 20),
              const SizedBox(width: 8),
              Text(
                title,
                style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: Colors.white, letterSpacing: 1.0),
              ),
            ],
          ),
          const SizedBox(height: 14),
          if (hasFile) ...[
            Text(
              filename,
              style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: Colors.white),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 4),
            Text(
              '${(sizeBytes / (1024 * 1024)).toStringAsFixed(2)} MB • $path',
              style: const TextStyle(fontSize: 11, color: AppTheme.themeTextSecondary, fontFamily: 'monospace'),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 14),
            OutlinedButton.icon(
              onPressed: onSelect,
              icon: const Icon(Icons.sync_rounded, size: 14),
              label: const Text('CHANGE FILE', style: TextStyle(fontSize: 11)),
              style: OutlinedButton.styleFrom(
                foregroundColor: Colors.white,
                side: const BorderSide(color: Color(0x28FFFFFF)),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
              ),
            ),
          ] else ...[
            Container(
              height: 70,
              alignment: Alignment.center,
              child: const Text('No file selected', style: TextStyle(color: AppTheme.themeTextMuted, fontSize: 12)),
            ),
            ElevatedButton.icon(
              onPressed: onSelect,
              icon: const Icon(Icons.file_upload_outlined, size: 16),
              label: Text(buttonLabel),
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF161616),
                foregroundColor: Colors.white,
                side: const BorderSide(color: Color(0x28FFFFFF)),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildResultBanner(AuditResult result) {
    final isMatch = result.match;

    return Container(
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(
        color: AppTheme.themeCardBgElevated,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: isMatch ? Colors.white : const Color(0xFFCCCCCC), width: 1.5),
        boxShadow: const [
          BoxShadow(
            color: Colors.black54,
            blurRadius: 18,
            spreadRadius: 2,
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                isMatch ? Icons.verified_rounded : Icons.warning_amber_rounded,
                color: Colors.white,
                size: 28,
              ),
              const SizedBox(width: 12),
              Text(
                isMatch ? 'VERIFICATION VERDICT: MATCH' : 'VERIFICATION VERDICT: MISMATCH',
                style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w900,
                  color: Colors.white,
                  letterSpacing: 1.0,
                ),
              ),
              const Spacer(),
              Text(
                'Calculated in ${result.durationSec}s',
                style: const TextStyle(fontSize: 11, color: AppTheme.themeTextSecondary, fontFamily: 'monospace'),
              ),
            ],
          ),
          const SizedBox(height: 16),
          const Divider(color: AppTheme.themeCardBorder, height: 1),
          const SizedBox(height: 14),

          // Hashes
          _buildHashRow('Original SHA-256', result.originalHash, isMatch ? Colors.white : AppTheme.themeTextSecondary),
          const SizedBox(height: 10),
          _buildHashRow('Received SHA-256', result.receivedHash, isMatch ? Colors.white : const Color(0xFFE5E5E5)),
        ],
      ),
    );
  }

  Widget _buildHashRow(String label, String hash, Color textColor) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label.toUpperCase(), style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w800, color: AppTheme.themeTextMuted, letterSpacing: 0.8)),
        const SizedBox(height: 2),
        SelectableText(
          hash,
          style: TextStyle(fontSize: 12, fontFamily: 'monospace', color: textColor, fontWeight: FontWeight.w600),
        ),
      ],
    );
  }
}
