import 'package:flutter/material.dart';

class TerminalLogView extends StatefulWidget {
  final List<String> logs;
  final double height;
  final VoidCallback? onClear;

  const TerminalLogView({
    super.key,
    required this.logs,
    this.height = 200,
    this.onClear,
  });

  @override
  State<TerminalLogView> createState() => _TerminalLogViewState();
}

class _TerminalLogViewState extends State<TerminalLogView> {
  final ScrollController _scrollController = ScrollController();

  @override
  void didUpdateWidget(covariant TerminalLogView oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.logs.length != oldWidget.logs.length) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (_scrollController.hasClients) {
          _scrollController.animateTo(
            _scrollController.position.maxScrollExtent,
            duration: const Duration(milliseconds: 200),
            curve: Curves.easeOut,
          );
        }
      });
    }
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      height: widget.height,
      decoration: BoxDecoration(
        color: const Color(0xFF050505),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0x28FFFFFF)),
      ),
      child: Column(
        children: [
          // Header Bar
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
            decoration: const BoxDecoration(
              color: Color(0xFF141414),
              borderRadius: BorderRadius.vertical(top: Radius.circular(9)),
              border: Border(bottom: BorderSide(color: Color(0x20FFFFFF))),
            ),
            child: Row(
              children: [
                const Icon(Icons.terminal_rounded, size: 16, color: Colors.white),
                const SizedBox(width: 8),
                const Text(
                  'TERMINAL LOGS',
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w800,
                    color: Color(0xFFAAAAAA),
                    letterSpacing: 1.0,
                    fontFamily: 'monospace',
                  ),
                ),
                const Spacer(),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(
                    color: const Color(0xFF1E1E1E),
                    borderRadius: BorderRadius.circular(4),
                    border: Border.all(color: const Color(0x26FFFFFF)),
                  ),
                  child: Text(
                    '${widget.logs.length} EVENTS',
                    style: const TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.w700,
                      color: Colors.white,
                      fontFamily: 'monospace',
                    ),
                  ),
                ),
              ],
            ),
          ),

          // Log Content List
          Expanded(
            child: widget.logs.isEmpty
                ? const Center(
                    child: Text(
                      'Ready. Waiting for transfer activity...',
                      style: TextStyle(
                        color: Color(0xFF707070),
                        fontFamily: 'monospace',
                        fontSize: 12,
                      ),
                    ),
                  )
                : ListView.builder(
                    controller: _scrollController,
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                    itemCount: widget.logs.length,
                    itemBuilder: (context, index) {
                      final line = widget.logs[index];
                      Color textColor = const Color(0xFFD4D4D4);
                      FontWeight weight = FontWeight.w400;
                      if (line.contains('error') || line.contains('MISMATCH') || line.contains('failed')) {
                        textColor = Colors.white;
                        weight = FontWeight.w700;
                      } else if (line.contains('verified') || line.contains('completed') || line.contains('saved')) {
                        textColor = Colors.white;
                        weight = FontWeight.w600;
                      } else if (line.contains('started') || line.contains('accepted')) {
                        textColor = const Color(0xFFAAAAAA);
                      }

                      return Padding(
                        padding: const EdgeInsets.only(bottom: 4),
                        child: Text(
                          line,
                          style: TextStyle(
                            fontFamily: 'monospace',
                            fontSize: 11.5,
                            color: textColor,
                            fontWeight: weight,
                            height: 1.35,
                          ),
                        ),
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }
}
