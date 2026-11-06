import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:tshare_flutter/main.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('TShare app navigation and rotary dial smoke test', (WidgetTester tester) async {
    // Set desktop screen size to fit desktop layouts comfortably
    tester.view.physicalSize = const Size(1280, 800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() => tester.view.resetPhysicalSize());

    await tester.pumpWidget(const TShareApp());
    await tester.pump(const Duration(milliseconds: 300));

    // Verify fixed top navigation bar elements
    expect(find.text('TSHARE'), findsOneWidget);
    expect(find.text('HOME'), findsOneWidget);
    expect(find.text('FILE SHARING'), findsWidgets);
    expect(find.text('FILE SERVER'), findsOneWidget);
    expect(find.text('VERIFY'), findsOneWidget);
    expect(find.text('SETTINGS'), findsOneWidget);

    // Switch to FILE SHARING tab
    await tester.tap(find.text('FILE SHARING').first);
    await tester.pump(const Duration(milliseconds: 300));

    // Verify State 1: Rotary selection interface options
    expect(find.text('ROTARY TELEPHONE SELECTOR'), findsOneWidget);
    expect(find.text('SEND'), findsWidgets);
    expect(find.text('RECEIVE'), findsWidgets);
    expect(find.text('WIFI'), findsWidgets);
    expect(find.text('BLE'), findsWidgets);
    expect(find.text('CONFIRM'), findsWidgets);

    // Tap CONFIRM to advance to State 2: Device Connection
    await tester.tap(find.text('CONFIRM').first);
    await tester.pump(const Duration(milliseconds: 300));

    // Verify State 2 elements
    expect(find.text('DEVICE CONNECTION'), findsOneWidget);
    expect(find.text('MANUAL CONNECT'), findsOneWidget);
    expect(find.text('AUTO FIND DEVICES'), findsOneWidget);

    // Switch to FILE SERVER tab
    await tester.tap(find.text('FILE SERVER'));
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.text('EMBEDDED LAN FILE SERVER'), findsOneWidget);
    expect(find.text('START SERVER'), findsOneWidget);

    // Switch to VERIFY tab
    await tester.tap(find.text('VERIFY'));
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.text('PAIRWISE SHA-256 AUDIT & VERIFICATION'), findsOneWidget);
    expect(find.text('SELECT ORIGINAL'), findsOneWidget);
    expect(find.text('SELECT RECEIVED'), findsOneWidget);

    // Switch to SETTINGS tab
    await tester.tap(find.text('SETTINGS'));
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.text('APPLICATION SETTINGS'), findsOneWidget);
    expect(find.text('DEFAULT DOWNLOAD DIRECTORY'), findsOneWidget);
  });
}
