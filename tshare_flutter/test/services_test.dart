import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';
import 'package:flutter_test/flutter_test.dart';
import 'package:path/path.dart' as p;
import 'package:tshare_flutter/core/constants/app_constants.dart';
import 'package:tshare_flutter/data/models/file_item.dart';
import 'package:tshare_flutter/data/services/lan_file_server.dart';
import 'package:tshare_flutter/data/services/transfer_receiver.dart';
import 'package:tshare_flutter/data/services/transfer_sender.dart';
import 'package:tshare_flutter/data/services/verify_service.dart';
import 'package:tshare_flutter/data/services/wire_protocol.dart';

void main() {
  group('WireProtocol Tests', () {
    test('CRC32 calculation is deterministic and non-zero for test data', () {
      final data = Uint8List.fromList(utf8.encode('Hello TShare Network Protocol!'));
      final crc1 = WireProtocol.computeCrc32(data);
      final crc2 = WireProtocol.computeCrc32(data);
      expect(crc1, equals(crc2));
      expect(crc1, isNonZero);
    });

    test('Header encode and decode roundtrip matches exactly', () {
      final originalType = AppConstants.msgManifest;
      final originalSession = 884210;
      final originalLen = 1048576;

      final encoded = WireProtocol.encodeHeader(originalType, originalSession, originalLen);
      expect(encoded.length, equals(AppConstants.headerSize));

      final decoded = WireProtocol.decodeHeader(encoded);
      expect(decoded, isNotNull);
      expect(decoded!['msgType'], equals(originalType));
      expect(decoded['sessionId'], equals(originalSession));
      expect(decoded['payloadLen'], equals(originalLen));
    });

    test('Block header encode and decode roundtrip matches', () {
      final sessionId = 654321;
      final fileId = 42;
      final blockIdx = 3;
      final blockLen = 4096;
      final chk = WireProtocol.computeBlockChecksum(Uint8List.fromList([1, 2, 3, 4, 5]), 'crc32');

      final encoded = WireProtocol.encodeBlockHeader(sessionId, fileId, blockIdx, blockLen, chk);
      expect(encoded.length, equals(AppConstants.blockHeaderSize));

      final decoded = WireProtocol.decodeBlockHeader(encoded);
      expect(decoded, isNotNull);
      expect(decoded!['sessionId'], equals(sessionId));
      expect(decoded['fileId'], equals(fileId));
      expect(decoded['blockIndex'], equals(blockIdx));
      expect(decoded['blockSize'], equals(blockLen));
      expect(decoded['checksum'], equals(chk));
    });
  });

  group('VerifyService Tests', () {
    late Directory tempDir;

    setUp(() async {
      tempDir = await Directory.systemTemp.createTemp('tshare_verify_test_');
    });

    tearDown(() async {
      if (await tempDir.exists()) {
        await tempDir.delete(recursive: true);
      }
    });

    test('Pairwise file comparison accurately identifies matches and mismatches', () async {
      final verifier = VerifyService();

      final fileA = File(p.join(tempDir.path, 'file_a.txt'));
      await fileA.writeAsString('Identical content for verification check');

      final fileB = File(p.join(tempDir.path, 'file_b.txt'));
      await fileB.writeAsString('Identical content for verification check');

      final fileC = File(p.join(tempDir.path, 'file_c.txt'));
      await fileC.writeAsString('Different corrupted content');

      // Test identical files
      final matchResult = await verifier.verifyTwoFiles(fileA.path, fileB.path);
      expect(matchResult.success, isTrue);
      expect(matchResult.match, isTrue);
      expect(matchResult.status, equals('MATCH'));
      expect(matchResult.originalHash, equals(matchResult.receivedHash));

      // Test differing files
      final mismatchResult = await verifier.verifyTwoFiles(fileA.path, fileC.path);
      expect(mismatchResult.success, isTrue);
      expect(mismatchResult.match, isFalse);
      expect(mismatchResult.status, equals('MISMATCH'));
      expect(mismatchResult.originalHash, isNot(equals(mismatchResult.receivedHash)));
    });
  });

  group('Loopback Transfer Tests', () {
    late Directory sourceDir;
    late Directory destDir;

    setUp(() async {
      sourceDir = await Directory.systemTemp.createTemp('tshare_source_');
      destDir = await Directory.systemTemp.createTemp('tshare_dest_');
    });

    tearDown(() async {
      if (await sourceDir.exists()) await sourceDir.delete(recursive: true);
      if (await destDir.exists()) await destDir.delete(recursive: true);
    });

    test('Full loopback transfer with SHA-256 block verification', () async {
      final testFile1 = File(p.join(sourceDir.path, 'document.txt'));
      await testFile1.writeAsString('Hello from TShare full-stack test payload 1' * 200);

      final testFile2 = File(p.join(sourceDir.path, 'binary_sample.bin'));
      await testFile2.writeAsBytes(List.generate(20000, (i) => i % 256));

      const testPort = 52199;
      final receiver = TransferReceiver();
      final receiverStarted = await receiver.startServer(port: testPort, saveDir: destDir.path);
      expect(receiverStarted, isTrue);

      final sender = TransferSender();
      final items = [
        FileItem(path: testFile1.path, name: 'document.txt', size: await testFile1.length(), isDirectory: false),
        FileItem(path: testFile2.path, name: 'binary_sample.bin', size: await testFile2.length(), isDirectory: false),
      ];

      final transferSuccess = await sender.startTransfer(
        targetIp: '127.0.0.1',
        targetPort: testPort,
        items: items,
        hashMode: 'sha256',
      );

      if (!transferSuccess) {
        // ignore: avoid_print
        print('Transfer failed. Sender logs:\n${sender.logs.join('\n')}');
        // ignore: avoid_print
        print('Receiver logs:\n${receiver.logs.join('\n')}');
        // ignore: avoid_print
        print('Sender error: ${sender.errorMessage}');
      }

      expect(transferSuccess, isTrue);
      expect(sender.status, equals('completed'));

      // Verify files in destDir match exactly
      final received1 = File(p.join(destDir.path, 'document.txt'));
      final received2 = File(p.join(destDir.path, 'binary_sample.bin'));

      expect(await received1.exists(), isTrue);
      expect(await received2.exists(), isTrue);

      final verifier = VerifyService();
      final audit1 = await verifier.verifyTwoFiles(testFile1.path, received1.path);
      expect(audit1.match, isTrue);

      final audit2 = await verifier.verifyTwoFiles(testFile2.path, received2.path);
      expect(audit2.match, isTrue);

      await receiver.stopServer();
    });
  });

  group('LAN File Server Tests', () {
    late Directory shareDir;

    setUp(() async {
      shareDir = await Directory.systemTemp.createTemp('tshare_lan_server_');
    });

    tearDown(() async {
      if (await shareDir.exists()) await shareDir.delete(recursive: true);
    });

    test('Serves portal HTML and lists shared files on port 52205', () async {
      final sampleDoc = File(p.join(shareDir.path, 'test_portal_file.txt'));
      await sampleDoc.writeAsString('Web portal download verification');

      final server = LanFileServerService();
      const port = 52205;
      server.port = port;
      server.sharedFolder = shareDir.path;
      final started = await server.start();
      expect(started, isTrue);

      final client = HttpClient();

      // GET /
      final req = await client.getUrl(Uri.parse('http://127.0.0.1:$port/'));
      final res = await req.close();
      final body = await res.transform(utf8.decoder).join();
      expect(res.statusCode, equals(200));
      expect(body, contains('TShare LAN File Portal'));

      // GET /api/download
      final dlReq = await client.getUrl(Uri.parse('http://127.0.0.1:$port/api/download?file=test_portal_file.txt'));
      final dlRes = await dlReq.close();
      final dlBody = await dlRes.transform(utf8.decoder).join();
      expect(dlRes.statusCode, equals(200));
      expect(dlBody, equals('Web portal download verification'));

      client.close();
      await server.stop();
      expect(server.isRunning, isFalse);
    });
  });
}
