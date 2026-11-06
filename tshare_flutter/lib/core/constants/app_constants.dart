class AppConstants {
  static const int magic = 0x54534852; // "TSHR"
  static const int defaultPort = 52001;
  static const int tcpTransferPort = 52001;
  static const int portalPort = 52003;
  static const int discoveryPort = 52002;
  static const int blockSize = 4 * 1024 * 1024; // 4 MB chunk size

  // Message Types
  static const int msgHello = 1;
  static const int msgHelloAck = 2;
  static const int msgManifest = 3;
  static const int msgAccept = 4;
  static const int msgReject = 5;
  static const int msgResumeQuery = 6;
  static const int msgResumeBitmap = 7;
  static const int msgBlock = 8;
  static const int msgBlockAck = 9;
  static const int msgBlockNack = 10;
  static const int msgFileDone = 11;
  static const int msgFileDoneAck = 15;
  static const int msgSessionDone = 12;
  static const int msgCancel = 13;
  static const int msgError = 14;

  // Header sizes
  static const int headerSize = 16;
  static const int blockHeaderSize = 48;
}
