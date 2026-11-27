"""In-session Remote Toolbar & collapsible Network Status HUD refactor.

Targets:
- flutter/lib/models/model.dart:
  - QualityMonitorModel collapsible state (_expanded), 24-sample RTT ring buffer
    (jitter, min/max RTT, health tier), connection/display accessors, and
    setConnectionType() listener notification.
- flutter/lib/desktop/widgets/remote_toolbar.dart:
  - Concentric menu radii (outer 10 = pad 4 + item 6) & 10px toolbar capsule
  - Clickable live monospace tabular-nums P2P/Relay + Latency pill (_RrTransportPill)
    that toggles the in-session Network Status HUD.
- flutter/lib/desktop/pages/remote_page.dart:
  - Unwrap _buildRawTouchAndPointerRegion around QualityMonitor so clicking the
    HUD to collapse/expand never forwards mouse events to the remote host.
- flutter/lib/common/widgets/overlay.dart:
  - Interactive collapsible QualityMonitor HUD: compact pill <-> detailed card
    with live 24-sample RTT sparkline, jitter, path/protocol, bandwidth, FPS,
    codec/chroma, and resolution (dual-compatible with Flutter 3.24.5 & 3.44.9).
"""

from __future__ import annotations

from pathlib import Path

from . import read_text, replace_exact, write_text


def patch_desktop_session(root: Path) -> None:
    # ------------------------------------------------------------------
    # 1. model.dart: QualityMonitorModel collapsible state, jitter/sparkline
    #    ring buffer, connection/resolution getters & connection_ready notify
    # ------------------------------------------------------------------
    model_p = root / "flutter" / "lib" / "models" / "model.dart"
    mtxt = read_text(model_p)

    mtxt = replace_exact(
        mtxt,
        """    try {
      var connectionType = ConnectionTypeState.find(peerId);
      connectionType.setSecure(secure);
      connectionType.setDirect(direct);
      connectionType.setStreamType(streamType);
    } catch (e) {
      //
    }
  }""",
        """    try {
      var connectionType = ConnectionTypeState.find(peerId);
      connectionType.setSecure(secure);
      connectionType.setDirect(direct);
      connectionType.setStreamType(streamType);
    } catch (e) {
      //
    }
    notifyListeners();
    parent.target?.qualityMonitorModel.notifyConnectionChanged();
  }""",
        "Notify FfiModel and QualityMonitorModel on setConnectionType",
    )

    mtxt = replace_exact(
        mtxt,
        """class QualityMonitorModel with ChangeNotifier {
  WeakReference<FFI> parent;

  QualityMonitorModel(this.parent);
  var _show = false;
  final _data = QualityMonitorData();

  bool get show => _show;
  QualityMonitorData get data => _data;""",
        """class QualityMonitorModel with ChangeNotifier {
  static const int _maxDelaySamples = 24;
  WeakReference<FFI> parent;

  QualityMonitorModel(this.parent);
  var _show = false;
  var _expanded = false;
  final _data = QualityMonitorData();
  final List<int> _delayHistory = <int>[];

  bool get show => _show;
  bool get expanded => _expanded;
  QualityMonitorData get data => _data;
  List<int> get delayHistory => List<int>.unmodifiable(_delayHistory);

  void toggleExpanded() {
    _expanded = !_expanded;
    notifyListeners();
  }

  void setExpanded(bool value) {
    if (_expanded != value) {
      _expanded = value;
      notifyListeners();
    }
  }

  void notifyConnectionChanged() {
    notifyListeners();
  }

  Future<void> toggleFromToolbar(SessionID sessionId) async {
    if (!_show) {
      await bind.sessionToggleOption(
          sessionId: sessionId, value: 'show-quality-monitor');
      _show = true;
      _expanded = true;
      notifyListeners();
    } else {
      toggleExpanded();
    }
  }

  bool? get isDirect => parent.target?.ffiModel.direct;
  bool? get isSecure => parent.target?.ffiModel.secure;

  String get streamType {
    final raw = parent.target?.ffiModel.cachedPeerData.streamType ?? '';
    if (raw == 'Relay') return 'TCP';
    return raw;
  }

  String? get resolutionText {
    final pi = parent.target?.ffiModel.pi;
    if (pi == null || pi.displays.isEmpty) return null;
    final idx = pi.currentDisplay;
    final d = (idx >= 0 && idx < pi.displays.length)
        ? pi.displays[idx]
        : pi.displays.first;
    if (d.width > 0 && d.height > 0) {
      return '${d.width}x${d.height}';
    }
    return null;
  }

  int? get currentDelayMs {
    final raw = _data.delay;
    if (raw == null || raw.trim().isEmpty) return null;
    return int.tryParse(raw.trim());
  }

  int? get minDelayMs {
    if (_delayHistory.isEmpty) return null;
    var m = _delayHistory.first;
    for (final v in _delayHistory) {
      if (v < m) m = v;
    }
    return m;
  }

  int? get maxDelayMs {
    if (_delayHistory.isEmpty) return null;
    var m = _delayHistory.first;
    for (final v in _delayHistory) {
      if (v > m) m = v;
    }
    return m;
  }

  int? get jitterMs {
    if (_delayHistory.length < 2) return null;
    var sumDiff = 0;
    for (var i = 1; i < _delayHistory.length; i++) {
      sumDiff += (_delayHistory[i] - _delayHistory[i - 1]).abs();
    }
    return (sumDiff / (_delayHistory.length - 1)).round();
  }

  String get healthLevel {
    final d = currentDelayMs;
    final direct = isDirect;
    if (d == null && direct == null) return 'unknown';
    if (d != null) {
      if (d >= 150) return 'poor';
      if (d >= 50 || direct == false) return 'fair';
      return 'good';
    }
    return direct == true ? 'good' : 'fair';
  }""",
        "Add collapsible state, RTT history/jitter/health & accessors to QualityMonitorModel",
    )

    mtxt = replace_exact(
        mtxt,
        """      if (evt.containsKey('delay') && (evt['delay'] as String).isNotEmpty) {
        _data.delay = evt['delay'];
      }""",
        """      if (evt.containsKey('delay') && (evt['delay'] as String).isNotEmpty) {
        _data.delay = evt['delay'];
        final parsed = int.tryParse((evt['delay'] as String).trim());
        if (parsed != null && parsed >= 0) {
          _delayHistory.add(parsed);
          if (_delayHistory.length > _maxDelaySamples) {
            _delayHistory.removeAt(0);
          }
        }
      }""",
        "Record rolling 24-sample RTT delay history in QualityMonitorModel",
    )

    write_text(model_p, mtxt)

    # ------------------------------------------------------------------
    # 2. remote_toolbar.dart: concentric 10/4/6 radii + clickable P2P/Relay pill
    # ------------------------------------------------------------------
    p = root / "flutter" / "lib" / "desktop" / "widgets" / "remote_toolbar.dart"
    txt = read_text(p)

    txt = replace_exact(
        txt,
        "  const r = Radius.circular(5);",
        "  const r = Radius.circular(8);",
        "Remote toolbar collapse handle radius 8px",
    )

    txt = replace_exact(
        txt,
        """  static const double iconRadius = 8;
  static const double elevation = 3;

  static double dividerSpaceToAction = isWindows ? 8 : 14;

  static double menuBorderRadius = isWindows ? 5.0 : 7.0;
  static EdgeInsets menuPadding = isWindows
      ? EdgeInsets.fromLTRB(4, 12, 4, 12)
      : EdgeInsets.fromLTRB(6, 14, 6, 14);
  static const double menuButtonBorderRadius = 3.0;""",
        """  static const double iconRadius = 8;
  static const double elevation = 6;

  static double dividerSpaceToAction = isWindows ? 8 : 14;

  static double menuBorderRadius = 10.0;
  static EdgeInsets menuPadding = const EdgeInsets.all(4);
  static const double menuButtonBorderRadius = 6.0;""",
        "Remote toolbar concentric menu radii (outer 10 = pad 4 + item 6)",
    )

    txt = replace_exact(
        txt,
        "    final toolbarBorderRadius = BorderRadius.all(Radius.circular(4.0));",
        "    final toolbarBorderRadius = BorderRadius.all(Radius.circular(10.0));",
        "Remote toolbar capsule border radius 10px",
    )

    # Inject live P2P / Relay + Latency transport pill in horizontal toolbar
    txt = replace_exact(
        txt,
        """    toolbarItems.add(_PinMenu(state: widget.state));""",
        """    toolbarItems.add(_PinMenu(state: widget.state));
    if (isHorizontal) {
      toolbarItems.add(_RrTransportPill(ffi: widget.ffi));
    }""",
        "Add live P2P/Relay transport & latency pill to RemoteToolbar",
    )

    txt = replace_exact(
        txt,
        """class RemoteMenuEntry {""",
        """class _RrTransportPill extends StatelessWidget {
  final FFI ffi;
  const _RrTransportPill({required this.ffi});

  @override
  Widget build(BuildContext context) {
    final c = RrColors.of(context);
    return AnimatedBuilder(
      animation: Listenable.merge([ffi.ffiModel, ffi.qualityMonitorModel]),
      builder: (context, _) {
        final qm = ffi.qualityMonitorModel;
        final direct = ffi.ffiModel.direct;
        final delay = qm.data.delay;
        final fps = qm.data.fps;
        final codec = qm.data.codecFormat;
        final bool isP2P = direct == true;
        final bool isRelay = direct == false;
        final bool isExpanded = qm.show && qm.expanded;
        final Color bg = isP2P
            ? c.successSoft
            : isRelay
                ? c.warningSoft
                : c.bgSubtle;
        final Color fg = isP2P
            ? c.successText
            : isRelay
                ? c.warningText
                : c.textSecondary;
        final IconData icon = isP2P
            ? Icons.bolt_rounded
            : isRelay
                ? Icons.cloud_queue_rounded
                : Icons.sync_rounded;
        final String mode = isP2P
            ? 'P2P'
            : isRelay
                ? 'Relay'
                : 'Link';
        final String delayPart = delay != null ? ' · ${delay}ms' : '';
        final bool isViewOnly = ffi.ffiModel.viewOnly;
        final bool inputDisabled = !ffi.ffiModel.keyboard;
        final String tip = [
          isP2P
              ? 'Direct P2P connection'
              : isRelay
                  ? 'Relayed via server'
                  : 'Checking connection path',
          if (delay != null) 'Latency: ${delay}ms',
          if (fps != null && fps.isNotEmpty) 'FPS: $fps',
          if (codec != null && codec.isNotEmpty) 'Codec: $codec',
          isExpanded
              ? 'Click to collapse network panel'
              : 'Click to expand network details',
        ].join(' · ');
        final Widget transportPill = Semantics(
          button: true,
          label: tip,
          child: Tooltip(
            message: tip,
            child: MouseRegion(
              cursor: SystemMouseCursors.click,
              child: GestureDetector(
                behavior: HitTestBehavior.opaque,
                onTap: () => qm.toggleFromToolbar(ffi.sessionId),
                child: Container(
                  height: 26,
                  margin:
                      const EdgeInsets.symmetric(horizontal: 4, vertical: 6),
                  padding: const EdgeInsetsDirectional.fromSTEB(7, 0, 6, 0),
                  decoration: BoxDecoration(
                    color: bg,
                    borderRadius: BorderRadius.circular(7),
                    border: Border.all(
                      color: isP2P
                          ? c.successSolid
                          : isRelay
                              ? c.warningSolid
                              : c.borderSubtle,
                      width: 1,
                    ),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(icon, size: 13, color: fg),
                      const SizedBox(width: 4),
                      Text(
                        '$mode$delayPart',
                        style: RrText.mono(
                          size: 12,
                          weight: FontWeight.w600,
                          color: fg,
                          height: 1.2,
                        ),
                      ),
                      const SizedBox(width: 2),
                      Icon(
                        isExpanded
                            ? Icons.expand_less_rounded
                            : Icons.expand_more_rounded,
                        size: 14,
                        color: fg,
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        );
        if (!isViewOnly && !inputDisabled) {
          return transportPill;
        }
        final bool showViewOnly = isViewOnly;
        final Color inputBg = showViewOnly ? c.warningSoft : c.dangerSoft;
        final Color inputBorder =
            showViewOnly ? c.warningSolid : c.dangerSolid;
        final Color inputFg = showViewOnly ? c.warningText : c.dangerText;
        final String inputLabel = showViewOnly ? 'View only' : 'Input disabled';
        final String inputTip = showViewOnly
            ? 'View-only mode is active. Disable View only in Display settings to restore mouse and keyboard control.'
            : 'Remote mouse and keyboard are disabled by the host. Enable keyboard & mouse permission on the remote device.';
        return Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            transportPill,
            Semantics(
              label: inputTip,
              child: Tooltip(
                message: inputTip,
                child: Container(
                  height: 26,
                  margin: const EdgeInsetsDirectional.only(
                      end: 4, top: 6, bottom: 6),
                  padding: const EdgeInsetsDirectional.fromSTEB(7, 0, 8, 0),
                  decoration: BoxDecoration(
                    color: inputBg,
                    borderRadius: BorderRadius.circular(7),
                    border: Border.all(color: inputBorder, width: 1),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        showViewOnly
                            ? Icons.visibility_rounded
                            : Icons.keyboard_hide_rounded,
                        size: 13,
                        color: inputFg,
                      ),
                      const SizedBox(width: 4),
                      Text(
                        inputLabel,
                        style: RrText.caption(inputFg, weight: FontWeight.w600),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ],
        );
      },
    );
  }
}

class RemoteMenuEntry {""",
        "Define clickable _RrTransportPill widget for P2P/Relay + monospace latency",
    )

    write_text(p, txt)

    # ------------------------------------------------------------------
    # 3. desktop/pages/remote_page.dart: unwrap pointer forwarding on HUD
    # ------------------------------------------------------------------
    rp_p = root / "flutter" / "lib" / "desktop" / "pages" / "remote_page.dart"
    rptxt = read_text(rp_p)

    rptxt = replace_exact(
        rptxt,
        """    paints.add(
      Positioned(
        top: 10,
        right: 10,
        child: _buildRawTouchAndPointerRegion(
            QualityMonitor(_ffi.qualityMonitorModel), null, null),
      ),
    );""",
        """    paints.add(
      Positioned(
        top: 10,
        right: 10,
        child: QualityMonitor(_ffi.qualityMonitorModel),
      ),
    );""",
        "Unwrap _buildRawTouchAndPointerRegion around QualityMonitor so HUD clicks do not leak to remote host",
    )

    write_text(rp_p, rptxt)

    # ------------------------------------------------------------------
    # 4. overlay.dart: interactive collapsible compact <-> detailed HUD
    #    with live 24-sample RTT sparkline & network diagnostics
    # ------------------------------------------------------------------
    ov_p = root / "flutter" / "lib" / "common" / "widgets" / "overlay.dart"
    otxt = read_text(ov_p)

    otxt = replace_exact(
        otxt,
        """class QualityMonitor extends StatelessWidget {
  final QualityMonitorModel qualityMonitorModel;
  QualityMonitor(this.qualityMonitorModel);

  Widget _row(String info, String? value, {Color? rightColor}) {
    return Row(
      children: [
        Expanded(
            flex: 8,
            child: AutoSizeText(info,
                style: TextStyle(color: Color.fromARGB(255, 210, 210, 210)),
                textAlign: TextAlign.right,
                maxLines: 1)),
        Spacer(flex: 1),
        Expanded(
            flex: 8,
            child: AutoSizeText(value ?? '',
                style: TextStyle(color: rightColor ?? Colors.white),
                maxLines: 1)),
      ],
    );
  }

  @override
  Widget build(BuildContext context) => ChangeNotifierProvider.value(
      value: qualityMonitorModel,
      child: Consumer<QualityMonitorModel>(
          builder: (context, qualityMonitorModel, child) => qualityMonitorModel
                  .show
              ? Container(
                  constraints: BoxConstraints(maxWidth: 200),
                  padding: const EdgeInsets.all(8),
                  color: MyTheme.canvasColor.withAlpha(150),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _row("Speed", qualityMonitorModel.data.speed ?? '-'),
                      _row("FPS", qualityMonitorModel.data.fps ?? '-'),
                      // let delay be 0 if fps is 0
                      _row(
                          "Delay",
                          "${qualityMonitorModel.data.delay == null ? '-' : (qualityMonitorModel.data.fps ?? "").replaceAll(' ', '').replaceAll('0', '').isEmpty ? 0 : qualityMonitorModel.data.delay}ms",
                          rightColor: Colors.green),
                      _row("Target Bitrate",
                          "${qualityMonitorModel.data.targetBitrate ?? '-'}kb"),
                      _row(
                          "Codec", qualityMonitorModel.data.codecFormat ?? '-'),
                      _row("Chroma", qualityMonitorModel.data.chroma ?? '-'),
                      if (qualityMonitorModel.webrtcTransport != null)
                        _row("Transport",
                            qualityMonitorModel.webrtcTransport!),
                    ],
                  ),
                )
              : const SizedBox.shrink()));
}""",
        """class _RrDelaySparklinePainter extends CustomPainter {
  final List<int> samples;
  final Color lineColor;

  const _RrDelaySparklinePainter({
    required this.samples,
    required this.lineColor,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (size.width <= 2 || size.height <= 2) return;
    final gridPaint = Paint()
      ..color = const Color(0xFF232B3B)
      ..strokeWidth = 1.0;
    final midY = size.height * 0.5;
    canvas.drawLine(Offset(0, midY), Offset(size.width, midY), gridPaint);

    if (samples.length < 2) {
      final flatPaint = Paint()
        ..color = lineColor.withOpacity(0.45)
        ..strokeWidth = 1.5
        ..strokeCap = StrokeCap.round;
      canvas.drawLine(
        Offset(2, size.height - 4),
        Offset(size.width - 2, size.height - 4),
        flatPaint,
      );
      return;
    }

    var maxVal = 20;
    for (final v in samples) {
      if (v > maxVal) maxVal = v;
    }
    final double usableH = size.height - 6.0;
    final double stepX =
        samples.length > 1 ? (size.width - 4.0) / (samples.length - 1) : 0.0;

    final path = Path();
    final fillPath = Path();
    Offset lastPt = Offset(2.0, size.height - 3.0);

    for (var i = 0; i < samples.length; i++) {
      final double x = 2.0 + i * stepX;
      final double ratio = (samples[i] / maxVal).clamp(0.0, 1.0).toDouble();
      final double y = size.height - 3.0 - (ratio * usableH);
      lastPt = Offset(x, y);
      if (i == 0) {
        path.moveTo(x, y);
        fillPath.moveTo(x, size.height - 1.0);
        fillPath.lineTo(x, y);
      } else {
        path.lineTo(x, y);
        fillPath.lineTo(x, y);
      }
    }
    fillPath.lineTo(lastPt.dx, size.height - 1.0);
    fillPath.close();

    final fillPaint = Paint()
      ..color = lineColor.withOpacity(0.16)
      ..style = PaintingStyle.fill;
    canvas.drawPath(fillPath, fillPaint);

    final strokePaint = Paint()
      ..color = lineColor
      ..strokeWidth = 1.6
      ..style = PaintingStyle.stroke
      ..strokeJoin = StrokeJoin.round
      ..strokeCap = StrokeCap.round;
    canvas.drawPath(path, strokePaint);

    final dotPaint = Paint()
      ..color = lineColor
      ..style = PaintingStyle.fill;
    canvas.drawCircle(lastPt, 2.4, dotPaint);
  }

  @override
  bool shouldRepaint(covariant _RrDelaySparklinePainter oldDelegate) {
    if (oldDelegate.lineColor != lineColor) return true;
    if (oldDelegate.samples.length != samples.length) return true;
    for (var i = 0; i < samples.length; i++) {
      if (oldDelegate.samples[i] != samples[i]) return true;
    }
    return false;
  }
}

class QualityMonitor extends StatelessWidget {
  final QualityMonitorModel qualityMonitorModel;
  QualityMonitor(this.qualityMonitorModel);

  static Color _healthColor(String level) {
    switch (level) {
      case 'good':
        return const Color(0xFF4ADE80);
      case 'fair':
        return const Color(0xFFFBBF24);
      case 'poor':
        return const Color(0xFFF87171);
      default:
        return const Color(0xFF94A3B8);
    }
  }

  static Color _healthBg(String level) {
    switch (level) {
      case 'good':
        return const Color(0xFF0F291E);
      case 'fair':
        return const Color(0xFF2D200A);
      case 'poor':
        return const Color(0xFF311319);
      default:
        return const Color(0xFF1B202E);
    }
  }

  static Color _delayColor(int? delayMs) {
    if (delayMs == null) return const Color(0xFF94A3B8);
    if (delayMs >= 150) return const Color(0xFFF87171);
    if (delayMs >= 50) return const Color(0xFFFBBF24);
    return const Color(0xFF4ADE80);
  }

  static String _healthLabel(String level) {
    switch (level) {
      case 'good':
        return 'Good';
      case 'fair':
        return 'Fair';
      case 'poor':
        return 'Poor';
      default:
        return 'Init';
    }
  }

  Widget _row(String label, String value, {Color? valueColor}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 1.5),
      child: Row(
        children: [
          SizedBox(
            width: 72,
            child: AutoSizeText(
              label,
              style: const TextStyle(
                fontSize: 11.5,
                fontWeight: FontWeight.w500,
                color: Color(0xFF94A3B8),
                height: 1.3,
              ),
              maxLines: 1,
              minFontSize: 10,
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: AutoSizeText(
              value,
              textAlign: TextAlign.right,
              style: RrText.mono(
                size: 11.5,
                weight: FontWeight.w600,
                color: valueColor ?? const Color(0xFFF8FAFC),
                height: 1.3,
              ),
              maxLines: 1,
              minFontSize: 10,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCompactPill(QualityMonitorModel qm) {
    final bool isP2P = qm.isDirect == true;
    final bool isRelay = qm.isDirect == false;
    final String health = qm.healthLevel;
    final Color dotColor = _healthColor(health);
    final Color modeColor = isP2P
        ? const Color(0xFF4ADE80)
        : isRelay
            ? const Color(0xFFFBBF24)
            : const Color(0xFFCBD5E1);
    final IconData modeIcon = isP2P
        ? Icons.bolt_rounded
        : isRelay
            ? Icons.cloud_queue_rounded
            : Icons.sync_rounded;
    final String modeText = isP2P
        ? 'P2P'
        : isRelay
            ? 'Relay'
            : 'Link';
    final int? delayMs = qm.currentDelayMs;
    final String delayText = delayMs != null ? '${delayMs}ms' : '--ms';
    final String fpsText = (qm.data.fps ?? '').trim();

    return Semantics(
      button: true,
      label: 'Network status: $modeText, $delayText. Click to expand details.',
      child: Tooltip(
        message: 'Click to expand network details',
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 6),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 7,
                height: 7,
                decoration: BoxDecoration(
                  color: dotColor,
                  shape: BoxShape.circle,
                ),
              ),
              const SizedBox(width: 6),
              Icon(modeIcon, size: 13, color: modeColor),
              const SizedBox(width: 3),
              Text(
                modeText,
                style: RrText.mono(
                  size: 11.5,
                  weight: FontWeight.w600,
                  color: modeColor,
                  height: 1.2,
                ),
              ),
              Container(
                width: 1,
                height: 11,
                margin: const EdgeInsets.symmetric(horizontal: 6),
                color: const Color(0xFF2A3142),
              ),
              Text(
                delayText,
                style: RrText.mono(
                  size: 11.5,
                  weight: FontWeight.w600,
                  color: _delayColor(delayMs),
                  height: 1.2,
                ),
              ),
              if (fpsText.isNotEmpty) ...[
                const SizedBox(width: 6),
                Text(
                  '${fpsText}fps',
                  style: RrText.mono(
                    size: 11.5,
                    weight: FontWeight.w500,
                    color: const Color(0xFFCBD5E1),
                    height: 1.2,
                  ),
                ),
              ],
              const SizedBox(width: 4),
              const Icon(
                Icons.expand_more_rounded,
                size: 15,
                color: Color(0xFF94A3B8),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildExpandedCard(QualityMonitorModel qm) {
    final bool isP2P = qm.isDirect == true;
    final bool isRelay = qm.isDirect == false;
    final bool? secure = qm.isSecure;
    final String proto = qm.streamType;
    final String health = qm.healthLevel;
    final Color healthColor = _healthColor(health);
    final Color healthBg = _healthBg(health);
    final Color modeColor = isP2P
        ? const Color(0xFF4ADE80)
        : isRelay
            ? const Color(0xFFFBBF24)
            : const Color(0xFFCBD5E1);
    final IconData modeIcon = isP2P
        ? Icons.bolt_rounded
        : isRelay
            ? Icons.cloud_queue_rounded
            : Icons.sync_rounded;
    final String modeTitle = isP2P
        ? (proto.isNotEmpty ? 'P2P · $proto' : 'P2P Direct')
        : isRelay
            ? (proto.isNotEmpty ? 'Relay · $proto' : 'Relay')
            : 'Connecting';

    final int? delayMs = qm.currentDelayMs;
    final int? minDelay = qm.minDelayMs;
    final int? maxDelay = qm.maxDelayMs;
    final int? jitter = qm.jitterMs;

    final String latencyValue = delayMs == null
        ? '-'
        : (minDelay != null && maxDelay != null && qm.delayHistory.length >= 2)
            ? '${delayMs}ms ($minDelay-$maxDelay)'
            : '${delayMs}ms';
    final String jitterValue = jitter != null ? '±${jitter}ms' : '-';
    final String pathValue = qm.webrtcTransport ??
        (isP2P
            ? 'Direct${proto.isNotEmpty ? ' ($proto)' : ''}'
            : isRelay
                ? 'Relayed${proto.isNotEmpty ? ' ($proto)' : ''}'
                : 'Detecting...');
    final String speedPart =
        (qm.data.speed != null && qm.data.speed!.trim().isNotEmpty)
            ? qm.data.speed!.trim()
            : '-';
    final String bitratePart =
        (qm.data.targetBitrate != null && qm.data.targetBitrate!.trim().isNotEmpty)
            ? '${qm.data.targetBitrate!.trim()}kb'
            : '-';
    final String bandwidthValue = '$speedPart / $bitratePart';
    final String fpsValue =
        (qm.data.fps != null && qm.data.fps!.trim().isNotEmpty)
            ? '${qm.data.fps!.trim()} fps'
            : '-';
    final String codecPart =
        (qm.data.codecFormat != null && qm.data.codecFormat!.trim().isNotEmpty)
            ? qm.data.codecFormat!.trim()
            : '-';
    final String chromaPart =
        (qm.data.chroma != null && qm.data.chroma!.trim().isNotEmpty)
            ? qm.data.chroma!.trim()
            : '';
    final String codecValue =
        chromaPart.isNotEmpty ? '$codecPart · $chromaPart' : codecPart;
    final String? resolution = qm.resolutionText;

    return Container(
      constraints: const BoxConstraints(minWidth: 224, maxWidth: 256),
      padding: const EdgeInsets.all(10),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Semantics(
            button: true,
            label: 'Collapse network status panel',
            child: Tooltip(
              message: 'Click to collapse',
              child: Row(
                children: [
                  Icon(modeIcon, size: 14, color: modeColor),
                  const SizedBox(width: 5),
                  Flexible(
                    child: AutoSizeText(
                      modeTitle,
                      style: RrText.mono(
                        size: 12,
                        weight: FontWeight.w700,
                        color: modeColor,
                        height: 1.2,
                      ),
                      maxLines: 1,
                      minFontSize: 10,
                    ),
                  ),
                  if (secure != null) ...[
                    const SizedBox(width: 5),
                    Icon(
                      secure ? Icons.lock_rounded : Icons.lock_open_rounded,
                      size: 12,
                      color: secure
                          ? const Color(0xFF4ADE80)
                          : const Color(0xFFFBBF24),
                    ),
                  ],
                  const Spacer(),
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(
                      color: healthBg,
                      borderRadius: BorderRadius.circular(5),
                      border: Border.all(
                        color: healthColor.withOpacity(0.6),
                        width: 0.8,
                      ),
                    ),
                    child: Text(
                      _healthLabel(health),
                      style: RrText.mono(
                        size: 10,
                        weight: FontWeight.w600,
                        color: healthColor,
                        height: 1.15,
                      ),
                    ),
                  ),
                  const SizedBox(width: 4),
                  const Icon(
                    Icons.expand_less_rounded,
                    size: 16,
                    color: Color(0xFF94A3B8),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 8),
          Container(
            height: 26,
            padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
            decoration: BoxDecoration(
              color: const Color(0xFF141822),
              borderRadius: BorderRadius.circular(6),
              border: Border.all(color: const Color(0xFF1F2636), width: 1),
            ),
            child: CustomPaint(
              painter: _RrDelaySparklinePainter(
                samples: qm.delayHistory,
                lineColor: _delayColor(delayMs),
              ),
            ),
          ),
          const SizedBox(height: 8),
          _row(
            'Path',
            pathValue,
            valueColor: isP2P
                ? const Color(0xFF4ADE80)
                : isRelay
                    ? const Color(0xFFFBBF24)
                    : const Color(0xFFCBD5E1),
          ),
          _row('Latency', latencyValue, valueColor: _delayColor(delayMs)),
          _row(
            'Jitter',
            jitterValue,
            valueColor: (jitter != null && jitter >= 20)
                ? const Color(0xFFFBBF24)
                : const Color(0xFFCBD5E1),
          ),
          _row('Bandwidth', bandwidthValue),
          _row('FPS', fpsValue),
          _row('Codec', codecValue),
          if (resolution != null) _row('Resolution', resolution),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) => ChangeNotifierProvider.value(
        value: qualityMonitorModel,
        child: Consumer<QualityMonitorModel>(
          builder: (context, qm, child) {
            if (!qm.show) return const SizedBox.shrink();
            return Material(
              type: MaterialType.transparency,
              child: MouseRegion(
                cursor: SystemMouseCursors.click,
                child: GestureDetector(
                  behavior: HitTestBehavior.opaque,
                  onTap: qm.toggleExpanded,
                  child: Container(
                    decoration: BoxDecoration(
                      color: const Color(0xEB0B0E14),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(
                        color: const Color(0xFF2A3142),
                        width: 1,
                      ),
                      boxShadow: const <BoxShadow>[
                        BoxShadow(
                          color: Color(0x52000000),
                          blurRadius: 10,
                          offset: Offset(0, 4),
                        ),
                      ],
                    ),
                    child: AnimatedSize(
                      duration: const Duration(milliseconds: 160),
                      curve: Curves.easeOutCubic,
                      alignment: Alignment.topRight,
                      child: qm.expanded
                          ? _buildExpandedCard(qm)
                          : _buildCompactPill(qm),
                    ),
                  ),
                ),
              ),
            );
          },
        ),
      );
}""",
        "Replace QualityMonitor with interactive collapsible compact/detailed Network Status HUD",
    )

    write_text(ov_p, otxt)
