import 'dart:math';
import 'package:flutter/material.dart';

class CircularTelemetryGauge extends StatelessWidget {
  final double value; // 0.0 to maxValue
  final double maxValue;
  final String label;
  final String unit;
  final Color primaryColor;
  final double size;

  const CircularTelemetryGauge({
    super.key,
    required this.value,
    required this.maxValue,
    required this.label,
    required this.unit,
    this.primaryColor = Colors.white,
    this.size = 140,
  });

  @override
  Widget build(BuildContext context) {
    final ratio = (value / (maxValue <= 0 ? 1 : maxValue)).clamp(0.0, 1.0);

    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        alignment: Alignment.center,
        children: [
          CustomPaint(
            size: Size(size, size),
            painter: _GaugePainter(
              ratio: ratio,
              trackColor: const Color(0xFF1C1C1C),
              activeColor: primaryColor,
            ),
          ),
          Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                value.toStringAsFixed(1),
                style: TextStyle(
                  fontSize: size * 0.2,
                  fontWeight: FontWeight.w900,
                  color: Colors.white,
                  fontFamily: 'monospace',
                  letterSpacing: -0.5,
                ),
              ),
              Text(
                unit,
                style: TextStyle(
                  fontSize: size * 0.09,
                  fontWeight: FontWeight.w700,
                  color: primaryColor,
                  letterSpacing: 1.0,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                label.toUpperCase(),
                style: TextStyle(
                  fontSize: size * 0.08,
                  fontWeight: FontWeight.w600,
                  color: const Color(0xFFAAAAAA),
                  letterSpacing: 0.5,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _GaugePainter extends CustomPainter {
  final double ratio;
  final Color trackColor;
  final Color activeColor;

  _GaugePainter({
    required this.ratio,
    required this.trackColor,
    required this.activeColor,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = (size.width / 2) - 10;
    const strokeWidth = 8.0;

    // 240 degree sweep from 150 to 390 degrees
    const startAngle = 150 * (pi / 180);
    const totalSweep = 240 * (pi / 180);

    // Track arc
    final trackPaint = Paint()
      ..color = trackColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;

    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius),
      startAngle,
      totalSweep,
      false,
      trackPaint,
    );

    // Active arc (crisp monochrome stroke)
    if (ratio > 0) {
      final sweepAngle = totalSweep * ratio;

      final activePaint = Paint()
        ..color = activeColor
        ..style = PaintingStyle.stroke
        ..strokeWidth = strokeWidth
        ..strokeCap = StrokeCap.round;

      canvas.drawArc(
        Rect.fromCircle(center: center, radius: radius),
        startAngle,
        sweepAngle,
        false,
        activePaint,
      );
    }
  }

  @override
  bool shouldRepaint(covariant _GaugePainter oldDelegate) {
    return oldDelegate.ratio != ratio || oldDelegate.activeColor != activeColor;
  }
}
