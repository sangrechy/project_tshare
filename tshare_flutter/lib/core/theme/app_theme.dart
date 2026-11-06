import 'package:flutter/material.dart';

/// Strict Black & White Monochrome Design System
/// Derived from project_dev_android_widgets UI theme
class AppTheme {
  // =============================================================================
  // UI Theme: Strict Black & White Monochrome (No light or glowing colors)
  // =============================================================================
  static const Color themeBgTop = Color(0xFF000000);
  static const Color themeBgMid = Color(0xFF080808);
  static const Color themeBgBottom = Color(0xFF040404);
  static const Color themeBgDark = Color(0xFF000000);

  static const Color themeCardBg = Color(0xF2101010);
  static const Color themeCardBgElevated = Color(0xF6161616);
  static const Color themeCardBorder = Color(0x28FFFFFF); // 16% crisp white border

  static const Color themeInnerBoxBg = Color(0xFF0C0C0C);
  static const Color themeInnerBoxBorder = Color(0x20FFFFFF);

  static const Color themeTextFieldBg = Color(0xFF121212);
  static const Color themeTextFieldBorder = Color(0xFF2C2C2C);
  static const Color themeTextEditorBg = Color(0xFF080808);
  static const Color themeCodeBlockBg = Color(0xFF050505);

  static const Color themeTopBarBg = Color(0xF2080808);
  static const Color themeTopBarBorder = Color(0x20FFFFFF);

  static const Color themeDrawerBg = Color(0xFA080808);
  static const Color themeDrawerHeaderBg = Color(0xFF141414);
  static const Color themeDrawerItemSelected = Color(0x26FFFFFF);

  static const Color themePillBg = Color(0xFF181818);
  static const Color themePillBorder = Color(0x26FFFFFF);

  static const Color themeTextPrimary = Color(0xFFFFFFFF);
  static const Color themeTextSecondary = Color(0xFFAAAAAA);
  static const Color themeTextMuted = Color(0xFF707070);

  static const Color themeAccentPrimary = Color(0xFFFFFFFF);  // Pure White
  static const Color themeAccentSilver = Color(0xFFD4D4D4);   // Crisp Silver
  static const Color themeAccentMedium = Color(0xFFA3A3A3);   // Medium Silver
  static const Color themeAccentMuted = Color(0xFF737373);    // Charcoal Gray

  // Compatibility aliases
  static const Color bgMain = themeBgDark;
  static const Color bgCard = themeCardBg;
  static const Color bgCardHover = themeCardBgElevated;
  static const Color bgCardBorder = themeCardBorder;

  static const Color primary = themeAccentPrimary;
  static const Color primaryHover = themeAccentSilver;
  static const Color primaryGlow = Colors.transparent;

  static const Color success = themeAccentSilver;
  static const Color successGlow = Colors.transparent;

  static const Color danger = Color(0xFFB0B0B0);
  static const Color dangerGlow = Colors.transparent;

  static const Color warning = themeAccentMedium;
  static const Color cyan = themeAccentSilver;
  static const Color cyanGlow = Colors.transparent;
  static const Color purple = themeAccentMuted;

  static const Color textMain = themeTextPrimary;
  static const Color textDim = themeTextMuted;

  static ThemeData get darkTheme {
    return ThemeData(
      brightness: Brightness.dark,
      scaffoldBackgroundColor: themeBgDark,
      canvasColor: themeBgDark,
      colorScheme: const ColorScheme.dark(
        primary: themeAccentPrimary,
        primaryContainer: themeCardBgElevated,
        secondary: themeAccentSilver,
        surface: themeCardBg,
        surfaceContainerHighest: themeInnerBoxBg,
        onSurface: themeTextPrimary,
        onPrimary: Color(0xFF000000),
        outline: themeCardBorder,
      ),
      cardTheme: CardThemeData(
        color: themeCardBg,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: const BorderSide(color: themeCardBorder, width: 1),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: themeAccentPrimary,
          foregroundColor: const Color(0xFF000000),
          elevation: 0,
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(10),
          ),
          textStyle: const TextStyle(
            fontSize: 13,
            fontWeight: FontWeight.w800,
            letterSpacing: 0.5,
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: themeTextPrimary,
          side: const BorderSide(color: themeCardBorder),
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(10),
          ),
          textStyle: const TextStyle(
            fontSize: 13,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: themeTextFieldBg,
        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: themeTextFieldBorder),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: themeTextFieldBorder),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: themeAccentPrimary, width: 1.5),
        ),
        hintStyle: const TextStyle(color: themeTextMuted, fontSize: 13),
        labelStyle: const TextStyle(color: themeTextSecondary, fontSize: 13),
      ),
    );
  }
}
