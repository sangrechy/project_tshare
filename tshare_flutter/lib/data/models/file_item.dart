class FileItem {
  final String path;
  final String name;
  final int size;
  final bool isDirectory;
  final int fileCount;

  FileItem({
    required this.path,
    required this.name,
    required this.size,
    this.isDirectory = false,
    this.fileCount = 1,
  });

  String get formattedSize {
    if (size <= 0) return '0.0 MB';
    final mb = size / (1024 * 1024);
    if (mb >= 1024) {
      return '${(mb / 1024).toStringAsFixed(2)} GB';
    }
    return '${mb.toStringAsFixed(1)} MB';
  }

  Map<String, dynamic> toJson() => {
    'path': path,
    'name': name,
    'size': size,
    'isDirectory': isDirectory,
    'fileCount': fileCount,
  };
}
