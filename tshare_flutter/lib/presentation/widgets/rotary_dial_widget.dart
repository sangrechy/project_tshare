import 'dart:math';
import 'package:flutter/material.dart';

class RotaryDialWidget extends StatefulWidget {
  final String selectedAction;
  final String selectedConnection;
  final ValueChanged<String> onActionChanged;
  final ValueChanged<String> onConnectionChanged;
  final VoidCallback onConfirm;

  const RotaryDialWidget({
    super.key,
    required this.selectedAction,
    required this.selectedConnection,
    required this.onActionChanged,
    required this.onConnectionChanged,
    required this.onConfirm,
  });

  @override
  State<RotaryDialWidget> createState() => _RotaryDialWidgetState();
}

class _RotaryDialWidgetState extends State<RotaryDialWidget> with SingleTickerProviderStateMixin {
  late AnimationController _animController;
  late Animation<double> _angleAnimation;
  double _currentAngle = 0.0;

  @override
  void initState() {
    super.initState();
    _animController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 450),
    );
    _angleAnimation = Tween<double>(begin: 0, end: 0).animate(
      CurvedAnimation(parent: _animController, curve: Curves.easeOutCubic),
    );
    _updateAngle(animate: false);
  }

  @override
  void didUpdateWidget(covariant RotaryDialWidget oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.selectedAction != widget.selectedAction ||
        oldWidget.selectedConnection != widget.selectedConnection) {
      _updateAngle(animate: true);
    }
  }

  void _updateAngle({required bool animate}) {
    double target = 0.0;
    if (widget.selectedAction == 'SEND') {
      target = -0.7; // ~ -40 deg
    } else if (widget.selectedAction == 'RECEIVE') {
      target = -1.6; // ~ -90 deg
    }

    if (widget.selectedConnection == 'WIFI') {
      target += 0.8;
    } else if (widget.selectedConnection == 'BLE') {
      target += 1.4;
    } else if (widget.selectedConnection == 'ETHERNET') {
      target += 2.0;
    }

    if (animate) {
      _angleAnimation = Tween<double>(begin: _currentAngle, end: target).animate(
        CurvedAnimation(parent: _animController, curve: Curves.easeOutBack),
      );
      _animController.forward(from: 0.0);
    }
    _currentAngle = target;
  }

  @override
  void dispose() {
    _animController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    const dialSize = 340.0;

    return Center(
      child: SizedBox(
        width: dialSize,
        height: dialSize,
        child: Stack(
          alignment: Alignment.center,
          children: [
            // 1. ROTATING OUTER RING
            AnimatedBuilder(
              animation: _animController,
              builder: (context, child) {
                final angle = _animController.isAnimating ? _angleAnimation.value : _currentAngle;
                return Transform.rotate(
                  angle: angle,
                  child: CustomPaint(
                    size: const Size(dialSize - 30, dialSize - 30),
                    painter: _OuterRingPainter(),
                  ),
                );
              },
            ),

            // 2. FIXED STATIONARY ELEMENTS (No rotation!)

            // Top: WIFI
            Positioned(
              top: 10,
              child: _StationaryOptionButton(
                label: 'WiFi',
                icon: Icons.wifi_rounded,
                isSelected: widget.selectedConnection == 'WIFI',
                onTap: () => widget.onConnectionChanged('WIFI'),
              ),
            ),

            // Left Upper: SEND
            Positioned(
              left: 10,
              top: 90,
              child: _StationaryOptionButton(
                label: 'SEND',
                icon: Icons.arrow_upward_rounded,
                isSelected: widget.selectedAction == 'SEND',
                onTap: () => widget.onActionChanged('SEND'),
              ),
            ),

            // Left Lower: RECEIVE
            Positioned(
              left: 10,
              bottom: 90,
              child: _StationaryOptionButton(
                label: 'RECEIVE',
                icon: Icons.arrow_downward_rounded,
                isSelected: widget.selectedAction == 'RECEIVE',
                onTap: () => widget.onActionChanged('RECEIVE'),
              ),
            ),

            // Right Upper: BLE
            Positioned(
              right: 10,
              top: 90,
              child: _StationaryOptionButton(
                label: 'BLE',
                icon: Icons.bluetooth_rounded,
                isSelected: widget.selectedConnection == 'BLE',
                onTap: () => widget.onConnectionChanged('BLE'),
              ),
            ),

            // Right Lower: ETHERNET
            Positioned(
              right: 10,
              bottom: 90,
              child: _StationaryOptionButton(
                label: 'ETHERNET',
                icon: Icons.settings_ethernet_rounded,
                isSelected: widget.selectedConnection == 'ETHERNET',
                onTap: () => widget.onConnectionChanged('ETHERNET'),
              ),
            ),

            // 3. CENTER STATIONARY SELECT BUTTON
            GestureDetector(
              onTap: widget.onConfirm,
              child: Container(
                width: 90,
                height: 90,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: const Color(0xFF0F172A),
                  border: Border.all(
                    color: const Color(0xFF38BDF8),
                    width: 2.5,
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: const Color(0xFF38BDF8).withAlpha(120),
                      blurRadius: 16,
                      spreadRadius: 2,
                    ),
                  ],
                ),
                child: const Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.check_circle_outline_rounded, color: Color(0xFF38BDF8), size: 24),
                    SizedBox(height: 3),
                    Text(
                      'SELECT',
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 1.2,
                        color: Colors.white,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _StationaryOptionButton extends StatelessWidget {
  final String label;
  final IconData icon;
  final bool isSelected;
  final VoidCallback onTap;

  const _StationaryOptionButton({
    required this.label,
    required this.icon,
    required this.isSelected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final activeBg = isSelected ? const Color(0xFF0284C7) : const Color(0xFF1E293B);
    final activeBorder = isSelected ? const Color(0xFF38BDF8) : const Color(0xFF334155);
    final activeText = isSelected ? Colors.white : const Color(0xFF94A3B8);

    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(10),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
        decoration: BoxDecoration(
          color: activeBg,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: activeBorder, width: isSelected ? 2 : 1),
          boxShadow: isSelected
              ? [
                  BoxShadow(
                    color: const Color(0xFF0284C7).withAlpha(140),
                    blurRadius: 12,
                    spreadRadius: 1,
                  ),
                ]
              : null,
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 16, color: activeText),
            const SizedBox(width: 6),
            Text(
              label,
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w800,
                color: activeText,
                letterSpacing: 0.5,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _OuterRingPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.width / 2;

    // Background track ring
    final ringPaint = Paint()
      ..color = const Color(0xFF1E293B)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 14;

    canvas.drawCircle(center, radius, ringPaint);

    // Rotary telephone style holes / notches around the perimeter
    const numHoles = 10;
    for (int i = 0; i < numHoles; i++) {
      final angle = (i * (2 * pi / numHoles));
      final hX = center.dx + (radius * cos(angle));
      final hY = center.dy + (radius * sin(angle));

      final holeBorder = Paint()
        ..color = const Color(0xFF334155)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2;
      canvas.drawCircle(Offset(hX, hY), 8, holeBorder);

      final holeFill = Paint()
        ..color = const Color(0xFF0B0F19)
        ..style = PaintingStyle.fill;
      canvas.drawCircle(Offset(hX, hY), 7, holeFill);
    }

    // Active Indicator Notch
    final notchX = center.dx + (radius * cos(0));
    final notchY = center.dy + (radius * sin(0));

    final glowPaint = Paint()
      ..color = const Color(0xFF38BDF8).withAlpha(160)
      ..style = PaintingStyle.fill
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 8);
    canvas.drawCircle(Offset(notchX, notchY), 10, glowPaint);

    final notchPaint = Paint()
      ..color = const Color(0xFF38BDF8)
      ..style = PaintingStyle.fill;
    canvas.drawCircle(Offset(notchX, notchY), 6, notchPaint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
