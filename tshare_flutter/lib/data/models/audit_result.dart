class AuditResult {
  final bool success;
  final bool match;
  final String status; // 'MATCH' or 'MISMATCH'
  final String originalPath;
  final String originalName;
  final String originalHash;
  final int originalSize;
  final String receivedPath;
  final String receivedName;
  final String receivedHash;
  final int receivedSize;
  final double durationSec;
  final String? error;

  AuditResult({
    required this.success,
    required this.match,
    required this.status,
    required this.originalPath,
    required this.originalName,
    required this.originalHash,
    required this.originalSize,
    required this.receivedPath,
    required this.receivedName,
    required this.receivedHash,
    required this.receivedSize,
    required this.durationSec,
    this.error,
  });

  factory AuditResult.error(String message) => AuditResult(
    success: false,
    match: false,
    status: 'ERROR',
    originalPath: '',
    originalName: '',
    originalHash: '',
    originalSize: 0,
    receivedPath: '',
    receivedName: '',
    receivedHash: '',
    receivedSize: 0,
    durationSec: 0,
    error: message,
  );
}
