import 'package:flutter/material.dart';

class CustomProgressBar extends StatelessWidget {
  final double progress; // 0.0 to 1.0
  final double height;
  final String? leftLabel;
  final String? rightLabel;
  final Color primaryColor;

  const CustomProgressBar({
    super.key,
    required this.progress,
    this.height = 10,
    this.leftLabel,
    this.rightLabel,
    this.primaryColor = Colors.white,
  });

  @override
  Widget build(BuildContext context) {
    final clamped = progress.clamp(0.0, 1.0);
    final percent = (clamped * 100).toInt();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        if (leftLabel != null || rightLabel != null)
          Padding(
            padding: const EdgeInsets.only(bottom: 6),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                if (leftLabel != null)
                  Text(
                    leftLabel!,
                    style: const TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: Color(0xFFAAAAAA),
                    ),
                  ),
                if (rightLabel != null)
                  Text(
                    rightLabel!,
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                      color: primaryColor,
                      fontFamily: 'monospace',
                    ),
                  )
                else
                  Text(
                    '$percent%',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                      color: primaryColor,
                      fontFamily: 'monospace',
                    ),
                  ),
              ],
            ),
          ),
        Container(
          height: height,
          decoration: BoxDecoration(
            color: const Color(0xFF141414),
            borderRadius: BorderRadius.circular(height / 2),
            border: Border.all(color: const Color(0x20FFFFFF)),
          ),
          child: LayoutBuilder(
            builder: (context, constraints) {
              return Stack(
                children: [
                  AnimatedContainer(
                    duration: const Duration(milliseconds: 250),
                    curve: Curves.easeOut,
                    width: constraints.maxWidth * clamped,
                    height: height,
                    decoration: BoxDecoration(
                      color: primaryColor,
                      borderRadius: BorderRadius.circular(height / 2),
                    ),
                  ),
                ],
              );
            },
          ),
        ),
      ],
    );
  }
}
