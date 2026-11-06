import 'dart:math';
import 'package:flutter/material.dart';
import '../../core/theme/app_theme.dart';

class RotaryDialWidget extends StatefulWidget {
  final String selectedAction;
  final String selectedConnection;
  final ValueChanged<String> onActionChanged;
  final ValueChanged<String> onConnectionChanged;
  final VoidCallback onConfirm;
  final double size;

  const RotaryDialWidget({
    super.key,
    required this.selectedAction,
    required this.selectedConnection,
    required this.onActionChanged,
    required this.onConnectionChanged,
    required this.onConfirm,
    this.size = 360,
  });

  @override
  State<RotaryDialWidget> createState() => _RotaryDialWidgetState();
}

class _RotaryDialWidgetState extends State<RotaryDialWidget> with SingleTickerProviderStateMixin {
  late AnimationController _springController;
  late Animation<double> _springAnimation;

  // The angle the wheel has been rotated from rest (in radians, >= 0 clockwise)
  double _rotationAngle = 0.0;
  double? _dragStartAngle;
  double _dragStartRotation = 0.0;

  // Fixed finger stop angle (at bottom right, ~140 degrees)
  static const double fingerStopAngle = 140.0 * (pi / 180.0);

  // 5 Dial Positions around the arc (angles in radians at rest)
  // Hole 1 to 5 going clockwise towards the stop
  static const List<double> holeRestAngles = [
    -130.0 * (pi / 180.0), // Hole 1: SEND (Top-left)
    -80.0 * (pi / 180.0),  // Hole 2: RECEIVE (Top)
    -30.0 * (pi / 180.0),  // Hole 3: WIFI (Top-right)
    20.0 * (pi / 180.0),   // Hole 4: ETHERNET (Right)
    70.0 * (pi / 180.0),   // Hole 5: BLE (Bottom-right, closest to stop)
  ];

  static const List<_DialOption> dialOptions = [
    _DialOption(type: 'ACTION', value: 'SEND', number: '1', icon: Icons.upload_rounded, label: 'SEND'),
    _DialOption(type: 'ACTION', value: 'RECEIVE', number: '2', icon: Icons.download_rounded, label: 'RECV'),
    _DialOption(type: 'CONN', value: 'WIFI', number: '3', icon: Icons.wifi_rounded, label: 'WIFI'),
    _DialOption(type: 'CONN', value: 'ETHERNET', number: '4', icon: Icons.settings_ethernet_rounded, label: 'ETH'),
    _DialOption(type: 'CONN', value: 'BLE', number: '5', icon: Icons.bluetooth_rounded, label: 'BLE'),
  ];

  @override
  void initState() {
    super.initState();
    _springController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 650),
    );
    _springController.addListener(() {
      setState(() {
        _rotationAngle = _springAnimation.value;
      });
    });
  }

  @override
  void dispose() {
    _springController.dispose();
    super.dispose();
  }

  // Dial a specific hole down to the finger stop, then spring back
  void _dialHole(int index) {
    if (_springController.isAnimating) return;

    final targetAngle = fingerStopAngle - holeRestAngles[index];
    if (targetAngle <= 0) return;

    final option = dialOptions[index];

    // Play forward rotate to stop, then spring rewind
    _springAnimation = Tween<double>(begin: _rotationAngle, end: targetAngle).animate(
      CurvedAnimation(parent: _springController, curve: Curves.easeOutQuad),
    );

    _springController.forward(from: 0.0).then((_) {
      // Trigger selection when reaching the stop
      if (option.type == 'ACTION') {
        widget.onActionChanged(option.value);
      } else {
        widget.onConnectionChanged(option.value);
      }

      // Spring-loaded rewind to 0
      Future.delayed(const Duration(milliseconds: 120), () {
        if (!mounted) return;
        _springAnimation = Tween<double>(begin: targetAngle, end: 0.0).animate(
          CurvedAnimation(parent: _springController, curve: Curves.easeOutBack),
        );
        _springController.forward(from: 0.0);
      });
    });
  }

  // Drag interaction around the wheel center
  void _onPanStart(DragStartDetails details, Offset center) {
    if (_springController.isAnimating) return;
    final touch = details.localPosition - center;
    _dragStartAngle = atan2(touch.dy, touch.dx);
    _dragStartRotation = _rotationAngle;
  }

  void _onPanUpdate(DragUpdateDetails details, Offset center) {
    if (_dragStartAngle == null) return;
    final touch = details.localPosition - center;
    final currentTouchAngle = atan2(touch.dy, touch.dx);

    var delta = currentTouchAngle - _dragStartAngle!;
    while (delta > pi) {
      delta -= 2 * pi;
    }
    while (delta < -pi) {
      delta += 2 * pi;
    }

    // Only allow clockwise rotation up to the maximum allowable stop (~280 degrees)
    final newAngle = (_dragStartRotation + delta).clamp(0.0, 280.0 * (pi / 180.0));
    setState(() {
      _rotationAngle = newAngle;
    });
  }

  void _onPanEnd(DragEndDetails details) {
    _dragStartAngle = null;

    // Check if any hole was dragged close to the finger stop (within 15 degrees)
    for (int i = 0; i < holeRestAngles.length; i++) {
      final currentHoleAngle = holeRestAngles[i] + _rotationAngle;
      final diff = (currentHoleAngle - fingerStopAngle).abs();
      if (diff < 0.28) { // ~16 degrees
        final option = dialOptions[i];
        if (option.type == 'ACTION') {
          widget.onActionChanged(option.value);
        } else {
          widget.onConnectionChanged(option.value);
        }
        break;
      }
    }

    // Spring return back to resting position
    _springAnimation = Tween<double>(begin: _rotationAngle, end: 0.0).animate(
      CurvedAnimation(parent: _springController, curve: Curves.easeOutBack),
    );
    _springController.forward(from: 0.0);
  }

  @override
  Widget build(BuildContext context) {
    final dialRadius = widget.size / 2;
    final holeRadius = widget.size * 0.082; // ~30px radius for finger hole
    final holeCenterRadius = dialRadius * 0.68; // orbit radius of finger holes

    return Center(
      child: SizedBox(
        width: widget.size,
        height: widget.size,
        child: LayoutBuilder(
          builder: (context, constraints) {
            final center = Offset(dialRadius, dialRadius);

            return Stack(
              alignment: Alignment.center,
              children: [
                // ====================================================
                // LAYER 1: STATIONARY BASE FACEPLATE (Beneath the shell)
                // ====================================================
                CustomPaint(
                  size: Size(widget.size, widget.size),
                  painter: _FaceplatePainter(
                    dialRadius: dialRadius,
                    holeRadius: holeRadius,
                    holeCenterRadius: holeCenterRadius,
                    holeRestAngles: holeRestAngles,
                    dialOptions: dialOptions,
                    selectedAction: widget.selectedAction,
                    selectedConnection: widget.selectedConnection,
                  ),
                ),

                // ====================================================
                // LAYER 2: THE ROTATING FINGER WHEEL SHELL (WITH HOLES)
                // This shell physically hides/covers underlying numbers
                // as it rotates around the center!
                // ====================================================
                GestureDetector(
                  onPanStart: (d) => _onPanStart(d, center),
                  onPanUpdate: (d) => _onPanUpdate(d, center),
                  onPanEnd: _onPanEnd,
                  child: CustomPaint(
                    size: Size(widget.size, widget.size),
                    painter: _RotatingShellPainter(
                      dialRadius: dialRadius,
                      holeRadius: holeRadius,
                      holeCenterRadius: holeCenterRadius,
                      holeRestAngles: holeRestAngles,
                      rotationAngle: _rotationAngle,
                    ),
                  ),
                ),

                // ====================================================
                // LAYER 3: TAP TARGETS FOR HOLES (Direct Tap to Dial)
                // ====================================================
                for (int i = 0; i < dialOptions.length; i++) ...[
                  Builder(
                    builder: (context) {
                      final currentAngle = holeRestAngles[i] + _rotationAngle;
                      final hx = dialRadius + holeCenterRadius * cos(currentAngle);
                      final hy = dialRadius + holeCenterRadius * sin(currentAngle);

                      return Positioned(
                        left: hx - holeRadius - 8,
                        top: hy - holeRadius - 8,
                        child: InkWell(
                          onTap: () => _dialHole(i),
                          borderRadius: BorderRadius.circular(holeRadius + 8),
                          child: Container(
                            width: (holeRadius + 8) * 2,
                            height: (holeRadius + 8) * 2,
                            alignment: Alignment.center,
                            decoration: const BoxDecoration(shape: BoxShape.circle),
                          ),
                        ),
                      );
                    },
                  ),
                ],

                // ====================================================
                // LAYER 4: FIXED METAL FINGER STOP BRACKET
                // ====================================================
                CustomPaint(
                  size: Size(widget.size, widget.size),
                  painter: _FingerStopPainter(
                    dialRadius: dialRadius,
                    stopAngle: fingerStopAngle,
                    holeCenterRadius: holeCenterRadius,
                    holeRadius: holeRadius,
                  ),
                ),

                // ====================================================
                // LAYER 5: CENTER ROTARY HUB (CONFIRM / DIAL BUTTON)
                // ====================================================
                InkWell(
                  onTap: widget.onConfirm,
                  borderRadius: BorderRadius.circular(dialRadius * 0.35),
                  child: Container(
                    width: dialRadius * 0.72,
                    height: dialRadius * 0.72,
                    decoration: BoxDecoration(
                      color: const Color(0xFF141414),
                      shape: BoxShape.circle,
                      border: Border.all(color: Colors.white, width: 2),
                      boxShadow: const [
                        BoxShadow(
                          color: Color(0xE3000000),
                          blurRadius: 14,
                          spreadRadius: 2,
                          offset: Offset(0, 4),
                        ),
                      ],
                    ),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(
                          widget.selectedAction,
                          style: const TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w900,
                            color: Colors.white,
                            letterSpacing: 1.0,
                          ),
                        ),
                        Container(
                          margin: const EdgeInsets.symmetric(vertical: 2),
                          width: 24,
                          height: 1.5,
                          color: AppTheme.themeCardBorder,
                        ),
                        Text(
                          widget.selectedConnection,
                          style: const TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w800,
                            color: AppTheme.themeTextSecondary,
                            letterSpacing: 0.8,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 2),
                          decoration: BoxDecoration(
                            color: Colors.white,
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: const Text(
                            'CONFIRM',
                            style: TextStyle(
                              fontSize: 9,
                              fontWeight: FontWeight.w900,
                              color: Colors.black,
                              letterSpacing: 0.8,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}

class _DialOption {
  final String type; // 'ACTION' or 'CONN'
  final String value;
  final String number;
  final IconData icon;
  final String label;

  const _DialOption({
    required this.type,
    required this.value,
    required this.number,
    required this.icon,
    required this.label,
  });
}

// -------------------------------------------------------------
// PAINTER 1: STATIONARY BASE FACEPLATE
// -------------------------------------------------------------
class _FaceplatePainter extends CustomPainter {
  final double dialRadius;
  final double holeRadius;
  final double holeCenterRadius;
  final List<double> holeRestAngles;
  final List<_DialOption> dialOptions;
  final String selectedAction;
  final String selectedConnection;

  _FaceplatePainter({
    required this.dialRadius,
    required this.holeRadius,
    required this.holeCenterRadius,
    required this.holeRestAngles,
    required this.dialOptions,
    required this.selectedAction,
    required this.selectedConnection,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(dialRadius, dialRadius);

    // 1. Base Housing Disc
    final basePaint = Paint()
      ..color = const Color(0xFF0A0A0A)
      ..style = PaintingStyle.fill;
    canvas.drawCircle(center, dialRadius - 2, basePaint);

    // Outer Chrome/Silver Bezel
    final bezelPaint = Paint()
      ..color = const Color(0x38FFFFFF)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.5;
    canvas.drawCircle(center, dialRadius - 2, bezelPaint);

    // Inner Rim Accent
    final innerRimPaint = Paint()
      ..color = const Color(0x18FFFFFF)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.0;
    canvas.drawCircle(center, dialRadius - 12, innerRimPaint);

    // 2. Dial Numbers & Indicators Underneath Each Hole Position
    for (int i = 0; i < dialOptions.length; i++) {
      final opt = dialOptions[i];
      final angle = holeRestAngles[i];
      final hx = dialRadius + holeCenterRadius * cos(angle);
      final hy = dialRadius + holeCenterRadius * sin(angle);
      final holeCenter = Offset(hx, hy);

      final isSelected = (opt.type == 'ACTION' && opt.value == selectedAction) ||
          (opt.type == 'CONN' && opt.value == selectedConnection);

      // Backing target disc for each number
      final targetDiscPaint = Paint()
        ..color = isSelected ? Colors.white : const Color(0xFF161616)
        ..style = PaintingStyle.fill;
      canvas.drawCircle(holeCenter, holeRadius - 2, targetDiscPaint);

      final targetBorder = Paint()
        ..color = isSelected ? Colors.white : const Color(0x28FFFFFF)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.2;
      canvas.drawCircle(holeCenter, holeRadius - 2, targetBorder);

      // Draw Number / Label in the center of the base hole spot
      final textPainter = TextPainter(
        text: TextSpan(
          text: opt.number,
          style: TextStyle(
            color: isSelected ? Colors.black : Colors.white,
            fontSize: 16,
            fontWeight: FontWeight.w900,
            fontFamily: 'monospace',
          ),
        ),
        textDirection: TextDirection.ltr,
      )..layout();

      textPainter.paint(
        canvas,
        Offset(hx - (textPainter.width / 2), hy - (textPainter.height / 2) - 4),
      );

      final labelPainter = TextPainter(
        text: TextSpan(
          text: opt.label,
          style: TextStyle(
            color: isSelected ? Colors.black : const Color(0xFFAAAAAA),
            fontSize: 8.5,
            fontWeight: FontWeight.w800,
            letterSpacing: 0.5,
          ),
        ),
        textDirection: TextDirection.ltr,
      )..layout();

      labelPainter.paint(
        canvas,
        Offset(hx - (labelPainter.width / 2), hy + 5),
      );
    }
  }

  @override
  bool shouldRepaint(covariant _FaceplatePainter oldDelegate) {
    return oldDelegate.selectedAction != selectedAction ||
        oldDelegate.selectedConnection != selectedConnection;
  }
}

// -------------------------------------------------------------
// PAINTER 2: ROTATING SHELL WITH CUTOUT HOLES (FINGER WHEEL)
// This rotates with rotationAngle and MASKS the underlying numbers!
// -------------------------------------------------------------
class _RotatingShellPainter extends CustomPainter {
  final double dialRadius;
  final double holeRadius;
  final double holeCenterRadius;
  final List<double> holeRestAngles;
  final double rotationAngle;

  _RotatingShellPainter({
    required this.dialRadius,
    required this.holeRadius,
    required this.holeCenterRadius,
    required this.holeRestAngles,
    required this.rotationAngle,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(dialRadius, dialRadius);
    final shellRadius = dialRadius - 8;

    // Use saveLayer to punch circular holes through the solid shell
    canvas.saveLayer(Rect.fromLTWH(0, 0, size.width, size.height), Paint());

    // 1. Draw the Semi-Opaque Solid Shell Disc
    // This is the solid surface that HIDES underlying options when rotated!
    final shellPaint = Paint()
      ..color = const Color(0xF0121212)
      ..style = PaintingStyle.fill;
    canvas.drawCircle(center, shellRadius, shellPaint);

    // Crisp shell outer border
    final shellBorder = Paint()
      ..color = const Color(0x33FFFFFF)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.0;
    canvas.drawCircle(center, shellRadius, shellBorder);

    // Inner center cutout (for the stationary hub)
    final hubCutoutPaint = Paint()..blendMode = BlendMode.clear;
    canvas.drawCircle(center, dialRadius * 0.40, hubCutoutPaint);

    // 2. Punch Out The Finger Holes through the shell (BlendMode.clear)
    final holePunchPaint = Paint()..blendMode = BlendMode.clear;

    for (int i = 0; i < holeRestAngles.length; i++) {
      final holeAngle = holeRestAngles[i] + rotationAngle;
      final hx = dialRadius + holeCenterRadius * cos(holeAngle);
      final hy = dialRadius + holeCenterRadius * sin(holeAngle);
      canvas.drawCircle(Offset(hx, hy), holeRadius, holePunchPaint);
    }

    canvas.restore();

    // 3. Draw Crisp Outer Rings Around Each Finger Hole on the Shell
    final holeRimPaint = Paint()
      ..color = Colors.white.withAlpha(200)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.0;

    for (int i = 0; i < holeRestAngles.length; i++) {
      final holeAngle = holeRestAngles[i] + rotationAngle;
      final hx = dialRadius + holeCenterRadius * cos(holeAngle);
      final hy = dialRadius + holeCenterRadius * sin(holeAngle);
      canvas.drawCircle(Offset(hx, hy), holeRadius, holeRimPaint);
    }
  }

  @override
  bool shouldRepaint(covariant _RotatingShellPainter oldDelegate) {
    return oldDelegate.rotationAngle != rotationAngle;
  }
}

// -------------------------------------------------------------
// PAINTER 3: VINTAGE METAL FINGER STOP BRACKET
// -------------------------------------------------------------
class _FingerStopPainter extends CustomPainter {
  final double dialRadius;
  final double stopAngle;
  final double holeCenterRadius;
  final double holeRadius;

  _FingerStopPainter({
    required this.dialRadius,
    required this.stopAngle,
    required this.holeCenterRadius,
    required this.holeRadius,
  });

  @override
  void paint(Canvas canvas, Size size) {
    // The stop sits just beyond the stop angle at the outer hole radius
    final sx = dialRadius + holeCenterRadius * cos(stopAngle);
    final sy = dialRadius + holeCenterRadius * sin(stopAngle);

    final stopPaint = Paint()
      ..color = Colors.white
      ..style = PaintingStyle.fill;

    // Draw metal finger stop wedge
    final path = Path();
    path.moveTo(sx - 4, sy - 14);
    path.lineTo(sx + 14, sy - 4);
    path.lineTo(sx + 18, sy + 14);
    path.lineTo(sx + 4, sy + 10);
    path.close();

    canvas.drawPath(path, stopPaint);

    final stopBorder = Paint()
      ..color = Colors.black
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.5;
    canvas.drawPath(path, stopBorder);
  }

  @override
  bool shouldRepaint(covariant _FingerStopPainter oldDelegate) => false;
}
