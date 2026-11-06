import 'package:flutter/material.dart';

class AppTheme {
  static const Color bgMain = Color(0xFF0B0F19);
  static const Color bgCard = Color(0xFF111827);
  static const Color bgCardHover = Color(0xFF1F2937);
  static const Color bgCardBorder = Color(0xFF1E293B);

  static const Color primary = Color(0xFF3B82F6);
  static const Color primaryHover = Color(0xFF2563EB);
  static const Color primaryGlow = Color(0x663B82F6);

  static const Color success = Color(0xFF10B981);
  static const Color successGlow = Color(0x5510B981);

  static const Color danger = Color(0xFFEF4444);
  static const Color dangerGlow = Color(0x55EF4444);

  static const Color warning = Color(0xFFF59E0B);
  static const Color cyan = Color(0xFF06B6D4);
  static const Color cyanGlow = Color(0x6606B6D4);
  static const Color purple = Color(0xFF8B5CF6);

  static const Color textMain = Color(0xFFF3F4F6);
  static const Color textMuted = Color(0xFF9CA3AF);
  static const Color textDim = Color(0xFF64748B);

  static ThemeData get darkTheme {
    return ThemeData(
      brightness: Brightness.dark,
      scaffoldBackgroundColor: bgMain,
      colorScheme: const ColorScheme.dark(
        primary: primary,
        secondary: cyan,
        surface: bgCard,
        error: danger,
      ),
      cardTheme: CardThemeData(
        color: bgCard,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(14),
          side: const BorderSide(color: bgCardBorder, width: 1),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: primary,
          foregroundColor: Colors.white,
          elevation: 0,
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(8),
          ),
          textStyle: const TextStyle(
            fontSize: 13,
            fontWeight: FontWeight.w700,
            letterSpacing: 0.5,
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: textMain,
          side: const BorderSide(color: bgCardBorder),
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(8),
          ),
          textStyle: const TextStyle(
            fontSize: 13,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: const Color(0xFF090D16),
        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: const BorderSide(color: bgCardBorder),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: const BorderSide(color: bgCardBorder),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: const BorderSide(color: primary, width: 1.5),
        ),
        hintStyle: const TextStyle(color: textDim, fontSize: 13),
      ),
      fontFamily: '-apple-system',
    );
  }
}
