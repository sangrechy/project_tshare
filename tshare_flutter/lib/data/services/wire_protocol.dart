import 'dart:convert';
import 'dart:typed_data';
import 'package:crypto/crypto.dart';
import '../../core/constants/app_constants.dart';

class WireProtocol {
  // Precomputed CRC32 Table
  static final List<int> _crc32Table = _generateCrc32Table();

  static List<int> _generateCrc32Table() {
    final table = List<int>.filled(256, 0);
    for (int i = 0; i < 256; i++) {
      int c = i;
      for (int k = 0; k < 8; k++) {
        c = (c & 1) != 0 ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1);
      }
      table[i] = c;
    }
    return table;
  }

  static int computeCrc32(Uint8List data) {
    int crc = 0xFFFFFFFF;
    for (int i = 0; i < data.length; i++) {
      crc = (crc >>> 8) ^ _crc32Table[(crc ^ data[i]) & 0xFF];
    }
    return (crc ^ 0xFFFFFFFF) >>> 0;
  }

  /// Computes 32-byte block checksum based on mode: 'sha256', 'crc32', or 'none'
  static Uint8List computeBlockChecksum(Uint8List data, String mode) {
    if (mode == 'sha256') {
      final digest = sha256.convert(data);
      return Uint8List.fromList(digest.bytes);
    } else if (mode == 'crc32') {
      final crc = computeCrc32(data);
      final out = Uint8List(32);
      ByteData.view(out.buffer).setUint32(0, crc, Endian.big);
      return out;
    } else {
      // Mode 'none' -> 32 zero bytes
      return Uint8List(32);
    }
  }

  static bool verifyBlockChecksum(Uint8List data, Uint8List expected, String mode) {
    if (mode == 'none') return true;
    final actual = computeBlockChecksum(data, mode);
    if (actual.length != expected.length) return false;
    for (int i = 0; i < actual.length; i++) {
      if (actual[i] != expected[i]) return false;
    }
    return true;
  }

  /// Encodes 16-byte protocol header: [MAGIC: 4B, MSG_TYPE: 2B, SESSION_ID: 6B, PAYLOAD_LEN: 4B]
  static Uint8List encodeHeader(int msgType, int sessionId, int payloadLen) {
    final bytes = Uint8List(AppConstants.headerSize);
    final bd = ByteData.view(bytes.buffer);
    bd.setUint32(0, AppConstants.magic, Endian.big);
    bd.setUint16(4, msgType, Endian.big);
    bd.setUint32(6, (sessionId >> 16) & 0xFFFFFFFF, Endian.big);
    bd.setUint16(10, sessionId & 0xFFFF, Endian.big);
    bd.setUint32(12, payloadLen, Endian.big);
    return bytes;
  }

  /// Decodes 16-byte protocol header
  static Map<String, int>? decodeHeader(Uint8List bytes) {
    if (bytes.length < AppConstants.headerSize) return null;
    final bd = ByteData.view(bytes.buffer);
    final magic = bd.getUint32(0, Endian.big);
    if (magic != AppConstants.magic) return null;

    final msgType = bd.getUint16(4, Endian.big);
    final hi = bd.getUint32(6, Endian.big);
    final lo = bd.getUint16(10, Endian.big);
    final sessionId = (hi << 16) | lo;
    final payloadLen = bd.getUint32(12, Endian.big);

    return {
      'msgType': msgType,
      'sessionId': sessionId,
      'payloadLen': payloadLen,
    };
  }

  /// Encodes 48-byte block header
  static Uint8List encodeBlockHeader(int sessionId, int fileId, int blockIdx, int blockLen, Uint8List checksum32) {
    final bytes = Uint8List(AppConstants.blockHeaderSize);
    final bd = ByteData.view(bytes.buffer);
    bd.setUint32(0, (sessionId >> 16) & 0xFFFFFFFF, Endian.big);
    bd.setUint16(4, sessionId & 0xFFFF, Endian.big);
    bd.setUint16(6, fileId, Endian.big);
    bd.setUint32(8, blockIdx, Endian.big);
    bd.setUint32(12, blockLen, Endian.big);
    bytes.setRange(16, 48, checksum32);
    return bytes;
  }

  /// Decodes 48-byte block header: [SESSION_ID: 6B, FILE_ID: 2B, BLOCK_IDX: 4B, BLOCK_LEN: 4B, CHECKSUM: 32B]
  static Map<String, dynamic>? decodeBlockHeader(Uint8List bytes) {
    if (bytes.length < AppConstants.blockHeaderSize) return null;
    final bd = ByteData.view(bytes.buffer);
    final hi = bd.getUint32(0, Endian.big);
    final lo = bd.getUint16(4, Endian.big);
    final sessionId = (hi << 16) | lo;
    final fileId = bd.getUint16(6, Endian.big);
    final blockIndex = bd.getUint32(8, Endian.big);
    final blockSize = bd.getUint32(12, Endian.big);
    final checksum = bytes.sublist(16, 48);

    return {
      'sessionId': sessionId,
      'fileId': fileId,
      'blockIndex': blockIndex,
      'blockSize': blockSize,
      'checksum': checksum,
    };
  }

  static Uint8List encodeJsonPayload(int msgType, int sessionId, Map<String, dynamic> data) {
    final jsonBytes = utf8.encode(jsonEncode(data));
    final header = encodeHeader(msgType, sessionId, jsonBytes.length);
    final builder = BytesBuilder(copy: false);
    builder.add(header);
    builder.add(jsonBytes);
    return builder.toBytes();
  }
}
