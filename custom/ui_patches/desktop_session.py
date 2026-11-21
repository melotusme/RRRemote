"""In-session Remote Toolbar & Quality Monitor refactor.

Targets:
- flutter/lib/desktop/widgets/remote_toolbar.dart:
  - Concentric menu radii (outer 10 = pad 4 + item 6) & 10px toolbar capsule
  - Live monospace tabular-nums P2P vs Relay + Latency pill (_RrTransportPill)
- flutter/lib/common/widgets/overlay.dart:
  - Crisp rounded QualityMonitor HUD with monospace tabular-nums values
"""

from __future__ import annotations

from pathlib import Path

from . import read_text, replace_exact, write_text


def patch_desktop_session(root: Path) -> None:
    # ------------------------------------------------------------------
    # 1. remote_toolbar.dart: concentric 10/4/6 radii + P2P/Relay transport pill
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
        final direct = ffi.ffiModel.direct;
        final delay = ffi.qualityMonitorModel.data.delay;
        final fps = ffi.qualityMonitorModel.data.fps;
        final codec = ffi.qualityMonitorModel.data.codecFormat;
        final bool isP2P = direct == true;
        final bool isRelay = direct == false;
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
        ].join(' · ');
        final Widget transportPill = Semantics(
          label: tip,
          child: Tooltip(
            message: tip,
            child: Container(
              height: 26,
              margin: const EdgeInsets.symmetric(horizontal: 4, vertical: 6),
              padding: const EdgeInsetsDirectional.fromSTEB(7, 0, 8, 0),
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
                ],
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
        "Define _RrTransportPill widget for P2P/Relay + monospace latency",
    )

    write_text(p, txt)

    # ------------------------------------------------------------------
    # 2. overlay.dart: crisp rounded QualityMonitor with monospace tabular-nums
    # ------------------------------------------------------------------
    ov_p = root / "flutter" / "lib" / "common" / "widgets" / "overlay.dart"
    otxt = read_text(ov_p)
    otxt = replace_exact(
        otxt,
        """  Widget _row(String info, String? value, {Color? rightColor}) {
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
                  color: MyTheme.canvasColor.withAlpha(150),""",
        """  Widget _row(String info, String? value, {Color? rightColor}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 1),
      child: Row(
        children: [
          Expanded(
              flex: 8,
              child: AutoSizeText(info,
                  style: const TextStyle(
                    fontSize: 12,
                    color: Color(0xFFCBD5E1),
                    height: 1.35,
                  ),
                  textAlign: TextAlign.right,
                  maxLines: 1)),
          const Spacer(flex: 1),
          Expanded(
              flex: 8,
              child: AutoSizeText(value ?? '',
                  style: RrText.mono(
                    size: 12,
                    weight: FontWeight.w600,
                    color: rightColor ?? const Color(0xFFF8FAFC),
                    height: 1.35,
                  ),
                  maxLines: 1)),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) => ChangeNotifierProvider.value(
      value: qualityMonitorModel,
      child: Consumer<QualityMonitorModel>(
          builder: (context, qualityMonitorModel, child) => qualityMonitorModel
                  .show
              ? Container(
                  constraints: const BoxConstraints(maxWidth: 216),
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: const Color(0xEB0B0E14),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(
                      color: const Color(0xFF2A3142),
                      width: 1,
                    ),
                  ),""",
        "Monospace tabular-nums QualityMonitor HUD with 10px radius",
    )
    write_text(ov_p, otxt)
