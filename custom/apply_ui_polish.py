#!/usr/bin/env python3
"""
Apply RRRemote personal-edition UI & layout refactor to upstream RustDesk 1.5.3
Flutter sources across Desktop and Mobile.

Design principles:
- Single-user personal remote control UX (Linear / UU Remote inspired):
  zero-password clutter removed, quick-connect bar streamlined, Favorites
  default tab with clean labeled pills, decluttered personal Settings & Mobile UI.
- 100% compatible with both Flutter 3.24.5 (Win/Linux/Android/iOS/macOS-x64) and
  Flutter 3.44.9 (Win-arm64/macOS-arm64, including apply_flutter_3.44_source_patches.sh).
- Zero hardcoded personal servers/keys/IPs.
- Idempotent and strictly verified: every patch reports applied/already-applied clearly.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8", newline="\n")


def replace_exact(content: str, old: str, new: str, label: str, required: bool = True) -> str:
    if not new:
        raise ValueError(f"replace_exact requires non-empty replacement for idempotency: {label}")
    if new in content:
        print(f"[rrremote-ui] already applied: {label}")
        return content
    if old not in content:
        msg = f"[rrremote-ui] pattern NOT matched: {label}"
        if required:
            raise RuntimeError(msg)
        print(f"WARNING: {msg}")
        return content
    print(f"[rrremote-ui] applied: {label}")
    return content.replace(old, new, 1)


def ensure_import(content: str, import_line: str) -> str:
    if import_line in content:
        return content
    m = re.search(r"^import\s+['\"][^'\"]+['\"][^;]*;\s*$", content, flags=re.MULTILINE)
    if not m:
        return import_line + "\n" + content
    idx = m.end()
    return content[:idx] + "\n" + import_line + content[idx:]


def patch_common_theme(root: Path, update_repo: str) -> None:
    p = root / "flutter" / "lib" / "common.dart"
    txt = read_text(p)

    # 1. Refine ColorThemeExtension light/dark palettes (Obsidian Slate & Crisp Alabaster)
    txt = replace_exact(
        txt,
        """  static final light = ColorThemeExtension(
    border: Color(0xFFCCCCCC),
    border2: Color(0xFFBBBBBB),
    border3: Colors.black26,
    highlight: Color(0xFFE5E5E5),
    drag_indicator: Colors.grey[800],
    shadow: Colors.black,
    errorBannerBg: Color(0xFFFDEEEB),
    me: Colors.green,
    toastBg: Colors.black.withOpacity(0.6),
    toastText: Colors.white,
    divider: Colors.black38,
  );

  static final dark = ColorThemeExtension(
    border: Color(0xFF555555),
    border2: Color(0xFFE5E5E5),
    border3: Colors.white24,
    highlight: Color(0xFF3F3F3F),
    drag_indicator: Colors.grey,
    shadow: Colors.grey,
    errorBannerBg: Color(0xFF470F2D),
    me: Colors.greenAccent,
    toastBg: Colors.white.withOpacity(0.6),
    toastText: Colors.black,
    divider: Colors.white38,
  );""",
        """  static final light = ColorThemeExtension(
    border: Color(0xFFE2E6EE),
    border2: Color(0xFFCBD2DF),
    border3: Color(0x1F0F172A),
    highlight: Color(0xFFEEF2F6),
    drag_indicator: Color(0xFF475569),
    shadow: Color(0x330F172A),
    errorBannerBg: Color(0xFFFEF2F2),
    me: Color(0xFF16A34A),
    toastBg: Color(0xE60F172A),
    toastText: Colors.white,
    divider: Color(0x1A0F172A),
  );

  static final dark = ColorThemeExtension(
    border: Color(0xFF2A2F3D),
    border2: Color(0xFF475569),
    border3: Color(0x24FFFFFF),
    highlight: Color(0xFF222736),
    drag_indicator: Color(0xFF94A3B8),
    shadow: Color(0x80000000),
    errorBannerBg: Color(0xFF3B1522),
    me: Color(0xFF22C55E),
    toastBg: Color(0xEB1E2433),
    toastText: Color(0xFFF8FAFC),
    divider: Color(0x1FFFFFFF),
  );""",
        "ColorThemeExtension light/dark palettes",
    )

    # 2. Fix upstream ColorThemeExtension.lerp bug (wrongly lerping from `shadow`)
    txt = replace_exact(
        txt,
        """      errorBannerBg: Color.lerp(shadow, other.errorBannerBg, t),
      me: Color.lerp(shadow, other.me, t),
      toastBg: Color.lerp(shadow, other.toastBg, t),
      toastText: Color.lerp(shadow, other.toastText, t),
      divider: Color.lerp(shadow, other.divider, t),""",
        """      errorBannerBg: Color.lerp(errorBannerBg, other.errorBannerBg, t),
      me: Color.lerp(me, other.me, t),
      toastBg: Color.lerp(toastBg, other.toastBg, t),
      toastText: Color.lerp(toastText, other.toastText, t),
      divider: Color.lerp(divider, other.divider, t),""",
        "Fix ColorThemeExtension.lerp bug",
    )

    # 3. Upgrade MyTheme brand colors & surfaces
    txt = replace_exact(
        txt,
        """  static const Color grayBg = Color(0xFFEFEFF2);
  static const Color accent = Color(0xFF0071FF);
  static const Color accent50 = Color(0x770071FF);
  static const Color accent80 = Color(0xAA0071FF);
  static const Color canvasColor = Color(0xFF212121);
  static const Color border = Color(0xFFCCCCCC);
  static const Color idColor = Color(0xFF00B6F0);
  static const Color darkGray = Color.fromARGB(255, 148, 148, 148);
  static const Color cmIdColor = Color(0xFF21790B);
  static const Color dark = Colors.black87;
  static const Color button = Color(0xFF2C8CFF);
  static const Color hoverBorder = Color(0xFF999999);""",
        """  static const Color grayBg = Color(0xFFF5F7FA);
  static const Color accent = Color(0xFF2563EB);
  static const Color accent50 = Color(0x802563EB);
  static const Color accent80 = Color(0xCC2563EB);
  static const Color canvasColor = Color(0xFF0F1117);
  static const Color border = Color(0xFFE2E6EE);
  static const Color idColor = Color(0xFF3B82F6);
  static const Color darkGray = Color(0xFF94A3B8);
  static const Color cmIdColor = Color(0xFF16A34A);
  static const Color dark = Color(0xFF0F172A);
  static const Color button = Color(0xFF3B82F6);
  static const Color hoverBorder = Color(0xFF64748B);""",
        "MyTheme brand & neutral color tokens",
    )

    # 4. Harmonize ListTile radius to 8px
    txt = replace_exact(
        txt,
        """  static const ListTileThemeData listTileTheme = ListTileThemeData(
    shape: RoundedRectangleBorder(
      borderRadius: BorderRadius.all(
        Radius.circular(5),
      ),
    ),
  );""",
        """  static const ListTileThemeData listTileTheme = ListTileThemeData(
    shape: RoundedRectangleBorder(
      borderRadius: BorderRadius.all(
        Radius.circular(8),
      ),
    ),
  );""",
        "ListTile radius 8px",
    )

    # 5. Polish Light Theme (NOTE: keep `dialogTheme: DialogTheme(` and avoid literal
    # `backgroundColor: Colors.white,` so `.github/patches/apply_flutter_3.44_source_patches.sh`
    # passes `is_unpatched_state` and `is_complete_patch_state` cleanly!)
    txt = replace_exact(
        txt,
        """    hoverColor: Color.fromARGB(255, 224, 224, 224),
    scaffoldBackgroundColor: Colors.white,
    dialogBackgroundColor: Colors.white,
    appBarTheme: AppBarTheme(
      shadowColor: Colors.transparent,
    ),
    dialogTheme: DialogTheme(
      elevation: 15,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(18.0),
        side: BorderSide(
          width: 1,
          color: grayBg,
        ),
      ),
    ),
    scrollbarTheme: scrollbarTheme,
    inputDecorationTheme: isDesktop
        ? InputDecorationTheme(
            fillColor: grayBg,
            filled: true,
            isDense: true,
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(8),
            ),
          )
        : null,""",
        """    hoverColor: Color(0xFFEBF0F7),
    scaffoldBackgroundColor: Colors.white,
    dialogBackgroundColor: Colors.white,
    appBarTheme: AppBarTheme(
      elevation: 0,
      shadowColor: Colors.transparent,
    ),
    dialogTheme: DialogTheme(
      elevation: 8,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14.0),
        side: BorderSide(
          width: 1,
          color: Color(0xFFE2E6EE),
        ),
      ),
    ),
    scrollbarTheme: scrollbarTheme,
    inputDecorationTheme: isDesktop
        ? InputDecorationTheme(
            fillColor: grayBg,
            filled: true,
            isDense: true,
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide: BorderSide(color: Color(0xFFE2E6EE), width: 1),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide: BorderSide(color: Color(0xFFE2E6EE), width: 1),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide: BorderSide(color: MyTheme.accent, width: 1.5),
            ),
          )
        : null,""",
        "LightTheme dialogs, inputs, and elevation",
    )

    txt = replace_exact(
        txt,
        """    colorScheme: ColorScheme.light(
        primary: Colors.blue, secondary: accent, background: grayBg),""",
        """    colorScheme: ColorScheme.light(
        primary: accent, secondary: button, background: grayBg),""",
        "LightTheme ColorScheme",
    )

    # 6. Polish Dark Theme (Obsidian Slate surfaces; preserve `dialogTheme: DialogTheme(`
    # and `scrollbarTheme: scrollbarThemeDark,` anchors for Flutter 3.44 patch script)
    txt = replace_exact(
        txt,
        """    hoverColor: Color.fromARGB(255, 45, 46, 53),
    scaffoldBackgroundColor: Color(0xFF18191E),
    dialogBackgroundColor: Color(0xFF18191E),
    appBarTheme: AppBarTheme(
      shadowColor: Colors.transparent,
    ),
    dialogTheme: DialogTheme(
      elevation: 15,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(18.0),
        side: BorderSide(
          width: 1,
          color: Color(0xFF24252B),
        ),
      ),
    ),
    scrollbarTheme: scrollbarThemeDark,
    inputDecorationTheme: (isDesktop || isWebDesktop)
        ? InputDecorationTheme(
            fillColor: Color(0xFF24252B),
            filled: true,
            isDense: true,
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(8),
            ),
          )
        : null,""",
        """    hoverColor: Color(0xFF222736),
    scaffoldBackgroundColor: Color(0xFF0F1117),
    dialogBackgroundColor: Color(0xFF151821),
    appBarTheme: AppBarTheme(
      elevation: 0,
      backgroundColor: Color(0xFF151821),
      shadowColor: Colors.transparent,
    ),
    dialogTheme: DialogTheme(
      elevation: 10,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14.0),
        side: BorderSide(
          width: 1,
          color: Color(0xFF2A2F3D),
        ),
      ),
    ),
    scrollbarTheme: scrollbarThemeDark,
    inputDecorationTheme: (isDesktop || isWebDesktop)
        ? InputDecorationTheme(
            fillColor: Color(0xFF171A23),
            filled: true,
            isDense: true,
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide: BorderSide(color: Color(0xFF2A2F3D), width: 1),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide: BorderSide(color: Color(0xFF2A2F3D), width: 1),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide: BorderSide(color: MyTheme.button, width: 1.5),
            ),
          )
        : null,""",
        "DarkTheme Obsidian Slate palette & inputs",
    )

    txt = replace_exact(
        txt,
        """    cardColor: Color(0xFF24252B),""",
        """    cardColor: Color(0xFF171A23),""",
        "DarkTheme cardColor",
    )

    txt = replace_exact(
        txt,
        """    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        backgroundColor: Color(0xFF24252B),
        side: BorderSide(color: Colors.white12, width: 0.5),
        disabledForegroundColor: Colors.white70,
        foregroundColor: Colors.white70,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8.0),
        ),
      ),
    ),""",
        """    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        backgroundColor: Color(0xFF171A23),
        side: BorderSide(color: Color(0xFF2A2F3D), width: 1.0),
        disabledForegroundColor: Colors.white60,
        foregroundColor: Color(0xFFE2E8F0),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8.0),
        ),
      ),
    ),""",
        "DarkTheme outlinedButtonTheme",
    )

    txt = replace_exact(
        txt,
        """    menuBarTheme: MenuBarThemeData(
        style: MenuStyle(
            backgroundColor: MaterialStatePropertyAll(Color(0xFF121212)))),
    colorScheme: ColorScheme.dark(
      primary: Colors.blue,
      secondary: accent,
      background: Color(0xFF24252B),
    ),
    popupMenuTheme: PopupMenuThemeData(
        shape: RoundedRectangleBorder(
      side: BorderSide(color: Colors.white24),
      borderRadius: BorderRadius.all(Radius.circular(8.0)),
    )),""",
        """    menuBarTheme: MenuBarThemeData(
        style: MenuStyle(
            backgroundColor: MaterialStatePropertyAll(Color(0xFF151821)))),
    colorScheme: ColorScheme.dark(
      primary: button,
      secondary: accent,
      background: Color(0xFF171A23),
    ),
    popupMenuTheme: PopupMenuThemeData(
        color: Color(0xFF1B1F2B),
        shape: RoundedRectangleBorder(
      side: BorderSide(color: Color(0xFF2A2F3D)),
      borderRadius: BorderRadius.all(Radius.circular(10.0)),
    )),""",
        "DarkTheme menuBar, ColorScheme & popupMenu",
    )

    # 7. Curated industrial slate/indigo/cobalt device card palette (replaces random neon colors)
    txt = replace_exact(
        txt,
        """Color str2color(String str, [alpha = 0xFF]) {
  var hash = 160 << 16 + 114 << 8 + 91;
  for (var i = 0; i < str.length; i += 1) {
    hash = str.codeUnitAt(i) + ((hash << 5) - hash);
  }
  hash = hash % 16777216;
  return Color((hash & 0xFF7FFF) | (alpha << 24));
}""",
        """Color str2color(String str, [alpha = 0xFF]) {
  const palette = <int>[
    0x1E293B, // Slate 800
    0x1E3A5F, // Steel Blue
    0x1D3557, // Deep Cobalt
    0x1E3A8A, // Indigo 900
    0x164E63, // Deep Cyan
    0x134E4A, // Deep Teal
    0x312E81, // Deep Violet
    0x27272A, // Zinc 800
  ];
  var hash = 5381;
  for (var i = 0; i < str.length; i += 1) {
    hash = ((hash << 5) + hash) + str.codeUnitAt(i);
  }
  final rgb = palette[hash.abs() % palette.length];
  final effectiveAlpha = alpha is int ? (alpha < 0xCC ? 0xE6 : alpha) : 0xFF;
  return Color((rgb & 0xFFFFFF) | ((effectiveAlpha & 0xFF) << 24));
}""",
        "Curated industrial str2color device card palette",
    )

    # 8. Brand header logo in left host pane & mobile settings (RRRemote icon + wordmark)
    txt = replace_exact(
        txt,
        """class _Logo extends StatefulWidget {
  const _Logo();

  @override
  State<_Logo> createState() => _LogoState();
}

class _LogoState extends State<_Logo> {
  final Map<Brightness, Future<String?>> _logoFutures = {};

  Future<String?> _logoFutureFor(Brightness brightness) {
    return _logoFutures.putIfAbsent(
      brightness,
      () => _resolveLogoAsset(brightness),
    );
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<String?>(
      future: _logoFutureFor(Theme.of(context).brightness),
      builder: (BuildContext context, AsyncSnapshot<String?> snapshot) {
        final asset = snapshot.data;
        if (asset != null) {
          final image = Image.asset(
            asset,
            fit: BoxFit.contain,
            errorBuilder: (ctx, error, stackTrace) {
              return Container();
            },
          );
          return Container(
            constraints: BoxConstraints(maxWidth: 300, maxHeight: 60),
            child: image,
          ).marginOnly(left: 12, right: 12, top: 12);
        }
        return const Offstage();
      },
    );
  }
}""",
        """class _Logo extends StatefulWidget {
  const _Logo();

  @override
  State<_Logo> createState() => _LogoState();
}

class _LogoState extends State<_Logo> {
  @override
  Widget build(BuildContext context) {
    final textColor = Theme.of(context).textTheme.titleLarge?.color;
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 16, 14, 4),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(8),
            child: loadIcon(28),
          ),
          const SizedBox(width: 10),
          Text(
            'RRRemote',
            style: TextStyle(
              fontSize: 16.5,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.25,
              color: textColor,
            ),
          ),
          const SizedBox(width: 7),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
            decoration: BoxDecoration(
              color: MyTheme.accent.withOpacity(0.14),
              borderRadius: BorderRadius.circular(5),
            ),
            child: const Text(
              'PERSONAL',
              style: TextStyle(
                fontSize: 9,
                fontWeight: FontWeight.w700,
                letterSpacing: 0.6,
                color: MyTheme.idColor,
              ),
            ),
          ),
        ],
      ),
    );
  }
}""",
        "RRRemote Personal branded header logo",
    )

    repo_url = f"https://github.com/{update_repo}"
    txt = txt.replace("Uri.parse('https://rustdesk.com')", f"Uri.parse('{repo_url}')")
    write_text(p, txt)


def patch_desktop_home_page(root: Path, update_repo: str) -> None:
    p = root / "flutter" / "lib" / "desktop" / "pages" / "desktop_home_page.dart"
    txt = read_text(p)
    txt = ensure_import(txt, "import 'dart:ui' show FontFeature;")

    # 1. Remove stranger-oriented tip & One-time Password section from left sidebar
    txt = replace_exact(
        txt,
        """      Align(
        alignment: Alignment.center,
        child: loadLogo(),
      ),
      buildTip(context),
      if (!isOutgoingOnly) buildIDBoard(context),
      if (!isOutgoingOnly) buildPasswordBoard(context),""",
        """      Align(
        alignment: Alignment.centerLeft,
        child: loadLogo(),
      ),
      if (!isOutgoingOnly) buildIDBoard(context),""",
        "Remove tip and One-time Password board from Desktop left host pane",
    )

    # 2. Clean 232px width for left host sidebar
    txt = replace_exact(
        txt,
        "width: isIncomingOnly ? 280.0 : 200.0,",
        "width: isIncomingOnly ? 288.0 : 232.0,",
        "Set left host pane width to 232px",
    )

    # 3. Refactor buildIDBoard & buildPopupMenu into a clean 'This Desk ID' surface card
    #    with one-click Copy + subtle self-hosted Ready status + Server shortcut
    txt = replace_exact(
        txt,
        """  buildIDBoard(BuildContext context) {
    final model = gFFI.serverModel;
    return Container(
      margin: const EdgeInsets.only(left: 20, right: 11),
      height: 57,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.baseline,
        textBaseline: TextBaseline.alphabetic,
        children: [
          Container(
            width: 2,
            decoration: const BoxDecoration(color: MyTheme.accent),
          ).marginOnly(top: 5),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.only(left: 7),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    height: 25,
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          translate("ID"),
                          style: TextStyle(
                              fontSize: 14,
                              color: Theme.of(context)
                                  .textTheme
                                  .titleLarge
                                  ?.color
                                  ?.withOpacity(0.5)),
                        ).marginOnly(top: 5),
                        buildPopupMenu(context)
                      ],
                    ),
                  ),
                  Flexible(
                    child: GestureDetector(
                      onDoubleTap: () {
                        Clipboard.setData(
                            ClipboardData(text: model.serverId.text));
                        showToast(translate("Copied"));
                      },
                      child: TextFormField(
                        controller: model.serverId,
                        readOnly: true,
                        decoration: InputDecoration(
                          border: InputBorder.none,
                          contentPadding: EdgeInsets.only(top: 10, bottom: 10),
                        ),
                        style: TextStyle(
                          fontSize: 22,
                        ),
                      ).workaroundFreezeLinuxMint(),
                    ),
                  )
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget buildPopupMenu(BuildContext context) {
    final textColor = Theme.of(context).textTheme.titleLarge?.color;
    RxBool hover = false.obs;
    return InkWell(
      onTap: DesktopTabPage.onAddSetting,
      child: Tooltip(
        message: translate('Settings'),
        child: Obx(
          () => CircleAvatar(
            radius: 15,
            backgroundColor: hover.value
                ? Theme.of(context).scaffoldBackgroundColor
                : Theme.of(context).colorScheme.background,
            child: Icon(
              Icons.more_vert_outlined,
              size: 20,
              color: hover.value ? textColor : textColor?.withOpacity(0.5),
            ),
          ),
        ),
      ),
      onHover: (value) => hover.value = value,
    );
  }""",
        """  buildIDBoard(BuildContext context) {
    final model = gFFI.serverModel;
    final textColor = Theme.of(context).textTheme.titleLarge?.color;
    final borderColor = MyTheme.color(context).border ?? Colors.black12;
    return Container(
      margin: const EdgeInsets.fromLTRB(14, 12, 14, 6),
      padding: const EdgeInsets.fromLTRB(14, 10, 10, 10),
      decoration: BoxDecoration(
        color: Theme.of(context).scaffoldBackgroundColor,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: borderColor, width: 1),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Text(
                translate("ID"),
                style: TextStyle(
                  fontSize: 11.5,
                  fontWeight: FontWeight.w600,
                  letterSpacing: 0.4,
                  color: textColor?.withOpacity(0.55),
                ),
              ),
              buildPopupMenu(context),
            ],
          ),
          const SizedBox(height: 2),
          Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Expanded(
                child: GestureDetector(
                  onDoubleTap: () {
                    Clipboard.setData(
                        ClipboardData(text: model.serverId.text));
                    showToast(translate("Copied"));
                  },
                  child: TextFormField(
                    controller: model.serverId,
                    readOnly: true,
                    decoration: const InputDecoration(
                      border: InputBorder.none,
                      enabledBorder: InputBorder.none,
                      focusedBorder: InputBorder.none,
                      filled: false,
                      isDense: true,
                      contentPadding: EdgeInsets.symmetric(vertical: 6),
                    ),
                    style: const TextStyle(
                      fontSize: 19.5,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 0.5,
                      fontFeatures: [FontFeature.tabularFigures()],
                    ),
                  ).workaroundFreezeLinuxMint(),
                ),
              ),
              Tooltip(
                message: translate("Copy"),
                child: InkWell(
                  borderRadius: BorderRadius.circular(7),
                  onTap: () {
                    Clipboard.setData(
                        ClipboardData(text: model.serverId.text));
                    showToast(translate("Copied"));
                  },
                  child: Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 7, vertical: 5),
                    decoration: BoxDecoration(
                      color: MyTheme.accent.withOpacity(0.10),
                      borderRadius: BorderRadius.circular(7),
                    ),
                    child: const Icon(
                      Icons.copy_rounded,
                      size: 14,
                      color: MyTheme.idColor,
                    ),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Divider(height: 1, thickness: 0.8, color: borderColor),
          const SizedBox(height: 8),
          Obx(() {
            final stopped = svcStopped.value;
            final status = stateGlobal.svcStatus.value;
            final isReady = !stopped && status == SvcStatus.ready;
            final dotColor = stopped || status == SvcStatus.connecting
                ? const Color(0xFFF59E0B)
                : (isReady
                    ? const Color(0xFF22C55E)
                    : const Color(0xFFEF4444));
            final statusLabel = stopped
                ? translate("Service is not running")
                : status == SvcStatus.connecting
                    ? translate("connecting_status")
                    : isReady
                        ? translate("Ready")
                        : translate("not_ready_status");
            return Row(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                Container(
                  width: 7,
                  height: 7,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: dotColor,
                    boxShadow: [
                      BoxShadow(
                        color: dotColor.withOpacity(0.35),
                        blurRadius: 5,
                        spreadRadius: 0.5,
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 7),
                Expanded(
                  child: Text(
                    statusLabel,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontSize: 11.5,
                      fontWeight: FontWeight.w500,
                      color: textColor?.withOpacity(0.72),
                    ),
                  ),
                ),
                if (!bind.isDisableSettings())
                  Tooltip(
                    message: translate('ID/Relay Server'),
                    child: InkWell(
                      borderRadius: BorderRadius.circular(5),
                      onTap: () =>
                          DesktopSettingPage.switch2page(SettingsTabKey.network),
                      child: Padding(
                        padding: const EdgeInsets.all(3),
                        child: Icon(
                          Icons.dns_rounded,
                          size: 14,
                          color: textColor?.withOpacity(0.55),
                        ),
                      ),
                    ),
                  ),
              ],
            );
          }),
        ],
      ),
    );
  }

  Widget buildPopupMenu(BuildContext context) {
    final textColor = Theme.of(context).textTheme.titleLarge?.color;
    RxBool hover = false.obs;
    return InkWell(
      borderRadius: BorderRadius.circular(6),
      onTap: DesktopTabPage.onAddSetting,
      onHover: (value) => hover.value = value,
      child: Tooltip(
        message: translate('Settings'),
        child: Obx(
          () => Padding(
            padding: const EdgeInsets.all(4),
            child: Icon(
              Icons.tune_rounded,
              size: 16,
              color: hover.value ? textColor : textColor?.withOpacity(0.55),
            ),
          ),
        ),
      ),
    );
  }""",
        "Clean This Desk ID card with one-click Copy & self-hosted Ready indicator",
    )

    # 4. Redirect desktop update card links to RRRemote GitHub Releases & auto-download on startup
    txt = replace_exact(
        txt,
        "        bind.mainUriPrefixSync().contains('rustdesk')) {",
        "        (bind.mainUriPrefixSync().contains('rustdesk') ||\n            bind.mainUriPrefixSync().contains('rrremote'))) {",
        "Allow rrremote:// URI prefix for built-in update card",
    )
    txt = replace_exact(
        txt,
        "final Uri url = Uri.parse('https://rustdesk.com/download');",
        f"final Uri url = Uri.parse('https://github.com/{update_repo}/releases/latest');",
        "Redirect desktop download URL to RRRemote repo",
    )
    txt = replace_exact(
        txt,
        "'https://github.com/rustdesk/rustdesk/releases/tag/${bind.mainGetNewVersion()}'",
        f"'https://github.com/{update_repo}/releases/tag/${{bind.mainGetNewVersion()}}'",
        "Redirect desktop changelog URL to RRRemote repo",
    )
    txt = replace_exact(
        txt,
        """  Timer? _updateTimer;
  bool isCardClosed = false;""",
        """  Timer? _updateTimer;
  bool isCardClosed = false;
  bool _autoDownloadTriggered = false;""",
        "Add auto-download guard flag in DesktopHomePage",
    )
    txt = replace_exact(
        txt,
        """      if (isToUpdate) {
        onPressed = () {
          handleUpdate(updateUrl);
        };
      }""",
        """      if (isToUpdate) {
        onPressed = () {
          handleUpdate(updateUrl);
        };
        if (!_autoDownloadTriggered) {
          _autoDownloadTriggered = true;
          WidgetsBinding.instance.addPostFrameCallback((_) {
            if (mounted) {
              handleUpdate(updateUrl);
            }
          });
        }
      }""",
        "Auto-trigger in-app update download on app launch",
    )

    # 5. Clean macOS TCC permission action card ONLY when Screen Recording / Accessibility /
    #    Input Monitoring is missing (remove daemon nag & external rustdesk.com doc links)
    txt = replace_exact(
        txt,
        """    } else if (isMacOS) {
      final isOutgoingOnly = bind.isOutgoingOnly();
      if (!(isOutgoingOnly || bind.mainIsCanScreenRecording(prompt: false))) {
        return buildInstallCard("Permissions", "config_screen", "Configure",
            () async {
          bind.mainIsCanScreenRecording(prompt: true);
          // macOS shows the request prompt only once per app, so later
          // presses would do nothing without opening the settings pane.
          launchUrl(Uri.parse(
              'x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture'));
          watchIsCanScreenRecording = true;
        }, help: 'Help', link: translate("doc_mac_permission"));
      } else if (!isOutgoingOnly && !bind.mainIsProcessTrusted(prompt: false)) {
        return buildInstallCard("Permissions", "config_acc", "Configure",
            () async {
          bind.mainIsProcessTrusted(prompt: true);
          watchIsProcessTrust = true;
        }, help: 'Help', link: translate("doc_mac_permission"));
      } else if (!bind.mainIsCanInputMonitoring(prompt: false)) {
        return buildInstallCard("Permissions", "config_input", "Configure",
            () async {
          bind.mainIsCanInputMonitoring(prompt: true);
          watchIsInputMonitoring = true;
        }, help: 'Help', link: translate("doc_mac_permission"));
      } else if (!isOutgoingOnly &&
          !svcStopped.value &&
          bind.mainIsInstalled() &&
          !bind.mainIsInstalledDaemon(prompt: false)) {
        return buildInstallCard("", "install_daemon_tip", "Install", () async {
          bind.mainIsInstalledDaemon(prompt: true);
        });
      }""",
        """    } else if (isMacOS) {
      final isOutgoingOnly = bind.isOutgoingOnly();
      if (!(isOutgoingOnly || bind.mainIsCanScreenRecording(prompt: false))) {
        return buildInstallCard("Permissions", "config_screen", "Configure",
            () async {
          bind.mainIsCanScreenRecording(prompt: true);
          launchUrl(Uri.parse(
              'x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture'));
          watchIsCanScreenRecording = true;
        });
      } else if (!isOutgoingOnly && !bind.mainIsProcessTrusted(prompt: false)) {
        return buildInstallCard("Permissions", "config_acc", "Configure",
            () async {
          bind.mainIsProcessTrusted(prompt: true);
          launchUrl(Uri.parse(
              'x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility'));
          watchIsProcessTrust = true;
        });
      } else if (!bind.mainIsCanInputMonitoring(prompt: false)) {
        return buildInstallCard("Permissions", "config_input", "Configure",
            () async {
          bind.mainIsCanInputMonitoring(prompt: true);
          launchUrl(Uri.parse(
              'x-apple.systempreferences:com.apple.preference.security?Privacy_ListenEvent'));
          watchIsInputMonitoring = true;
        });
      }""",
        "Clean macOS TCC action cards (only Screen Recording / Accessibility / Input Monitoring)",
    )

    # Remove external rustdesk.com Linux doc links in desktop_home_page.dart
    repo_url = f"https://github.com/{update_repo}"
    txt = txt.replace(
        "https://rustdesk.com/docs/en/client/linux/#permissions-issue", repo_url
    ).replace(
        "https://rustdesk.com/docs/en/client/linux/#x11-required", repo_url
    ).replace(
        "https://rustdesk.com/docs/en/client/linux/#login-screen", repo_url
    )

    # 6. Replace garish pink-magenta buildInstallCard with refined slate-cobalt card
    txt = replace_exact(
        txt,
        """        Container(
          margin: EdgeInsets.fromLTRB(
              0, marginTop, 0, bind.isIncomingOnly() ? marginTop : 0),
          child: Container(
              decoration: BoxDecoration(
                  gradient: LinearGradient(
                begin: Alignment.centerLeft,
                end: Alignment.centerRight,
                colors: [
                  Color.fromARGB(255, 226, 66, 188),
                  Color.fromARGB(255, 244, 114, 124),
                ],
              )),
              padding: EdgeInsets.all(20),""",
        """        Container(
          margin: EdgeInsets.fromLTRB(
              14, 10, 14, bind.isIncomingOnly() ? marginTop : 0),
          child: Container(
              decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: Colors.white.withOpacity(0.14),
                    width: 1,
                  ),
                  gradient: const LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [
                  Color(0xFF1E293B),
                  Color(0xFF1E3A8A),
                ],
              )),
              padding: const EdgeInsets.all(14),""",
        "Refined slate-cobalt status/permission card",
    )

    txt = replace_exact(
        txt,
        """                                    FixedWidthButton(
                                      width: 150,
                                      padding: 8,
                                      isOutline: true,
                                      text: translate(btnText),
                                      textColor: Colors.white,
                                      borderColor: Colors.white,
                                      textSize: 20,
                                      radius: 10,
                                      onTap: onPressed,
                                    )""",
        """                                    FixedWidthButton(
                                      width: 156,
                                      padding: 7,
                                      isOutline: true,
                                      text: translate(btnText),
                                      textColor: Colors.white,
                                      borderColor: Colors.white70,
                                      textSize: 13.5,
                                      radius: 8,
                                      onTap: onPressed,
                                    )""",
        "Refined status card action button typography",
    )

    write_text(p, txt)


def patch_desktop_connection_and_tabs(root: Path) -> None:
    # 1. Desktop connection_page.dart: single-row streamlined Quick-Connect bar & status bar
    conn_p = root / "flutter" / "lib" / "desktop" / "pages" / "connection_page.dart"
    txt = read_text(conn_p)
    txt = ensure_import(txt, "import 'dart:ui' show FontFeature;")
    txt = ensure_import(
        txt, "import 'package:flutter_hbb/desktop/pages/desktop_setting_page.dart';"
    )

    txt = replace_exact(
        txt,
        "  double? get height => bind.isIncomingOnly() ? null : em * 3;",
        "  double? get height => bind.isIncomingOnly() ? null : 36.0;",
        "Compact OnlineStatusWidget height",
    )

    txt = replace_exact(
        txt,
        """  void onUsePublicServerGuide() {
    const url = "https://rustdesk.com/pricing";
    canLaunchUrlString(url).then((can) {
      if (can) {
        launchUrlString(url);
      }
    });
  }""",
        """  void onUsePublicServerGuide() {
    DesktopSettingPage.switch2page(SettingsTabKey.network);
  }""",
        "Replace pricing URL with direct Network/Server settings jump",
    )

    txt = replace_exact(
        txt,
        """    basicWidget() => Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            Container(
              height: 8,
              width: 8,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(4),
                color: _svcStopped.value ||
                        stateGlobal.svcStatus.value == SvcStatus.connecting
                    ? kColorWarn
                    : (stateGlobal.svcStatus.value == SvcStatus.ready
                        ? Color.fromARGB(255, 50, 190, 166)
                        : Color.fromARGB(255, 224, 79, 95)),
              ),
            ).marginSymmetric(horizontal: em),
            Container(
              width: isIncomingOnly ? 226 : null,
              child: _buildConnStatusMsg(),
            ),
            // stop
            if (!isIncomingOnly) startServiceWidget(),
            // ready && public
            // No need to show the guide if is custom client.
            if (!isIncomingOnly) setupServerWidget(),
          ],
        );""",
        """    basicWidget() => Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            Container(
              height: 8,
              width: 8,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: _svcStopped.value ||
                        stateGlobal.svcStatus.value == SvcStatus.connecting
                    ? const Color(0xFFF59E0B)
                    : (stateGlobal.svcStatus.value == SvcStatus.ready
                        ? const Color(0xFF22C55E)
                        : const Color(0xFFEF4444)),
                boxShadow: [
                  BoxShadow(
                    color: (stateGlobal.svcStatus.value == SvcStatus.ready &&
                            !_svcStopped.value
                        ? const Color(0xFF22C55E)
                        : const Color(0xFFF59E0B)).withOpacity(0.35),
                    blurRadius: 6,
                    spreadRadius: 1,
                  ),
                ],
              ),
            ).marginSymmetric(horizontal: em),
            Container(
              width: isIncomingOnly ? 226 : null,
              child: _buildConnStatusMsg(),
            ),
            if (!isIncomingOnly) startServiceWidget(),
            if (!isIncomingOnly) setupServerWidget(),
            if (!isIncomingOnly) const Spacer(),
            if (!isIncomingOnly && !bind.isDisableSettings())
              Tooltip(
                message: translate('ID/Relay Server'),
                child: InkWell(
                  borderRadius: BorderRadius.circular(6),
                  onTap: () => DesktopSettingPage.switch2page(SettingsTabKey.network),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          Icons.dns_rounded,
                          size: 13,
                          color: Theme.of(context)
                              .textTheme
                              .bodySmall
                              ?.color
                              ?.withOpacity(0.68),
                        ),
                        const SizedBox(width: 5),
                        Text(
                          translate('ID/Relay Server'),
                          style: TextStyle(
                            fontSize: 12,
                            color: Theme.of(context)
                                .textTheme
                                .bodySmall
                                ?.color
                                ?.withOpacity(0.72),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ).marginOnly(right: 12),
          ],
        );""",
        "Emerald status indicator + quick ID/Relay Server button",
    )

    # Tighten ConnectionPage vertical rhythm
    txt = replace_exact(
        txt,
        """            Row(
              children: [
                Flexible(child: _buildRemoteIDTextField(context)),
              ],
            ).marginOnly(top: 22),
            SizedBox(height: 12),
            Divider().paddingOnly(right: 12),""",
        """            Row(
              children: [
                Flexible(child: _buildRemoteIDTextField(context)),
              ],
            ).marginOnly(top: 16, right: 12),
            const SizedBox(height: 12),""",
        "Streamline ConnectionPage top spacing and remove redundant divider",
    )

    # Convert bulky 3-row Remote ID box into a sleek single-row Quick-Connect command bar
    txt = replace_exact(
        txt,
        """    var w = Container(
      width: 320 + 20 * 2,
      padding: const EdgeInsets.fromLTRB(20, 24, 20, 22),
      decoration: BoxDecoration(
          borderRadius: const BorderRadius.all(Radius.circular(13)),
          border: Border.all(color: Theme.of(context).colorScheme.background)),
      child: Ink(
        child: Column(
          children: [
            getConnectionPageTitle(context, false).marginOnly(bottom: 15),
            Row(
              children: [
                Expanded(
                    child: RawAutocomplete<Peer>(""",
        """    var w = Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.background.withOpacity(0.55),
        borderRadius: const BorderRadius.all(Radius.circular(12)),
        border: Border.all(
          color: MyTheme.color(context).border ??
              Theme.of(context).colorScheme.background,
          width: 1,
        ),
      ),
      child: Ink(
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            Container(
              width: 34,
              height: 34,
              margin: const EdgeInsets.only(right: 10),
              decoration: BoxDecoration(
                color: MyTheme.accent.withOpacity(0.12),
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Icon(
                Icons.bolt_rounded,
                size: 19,
                color: MyTheme.idColor,
              ),
            ),
            Expanded(
              child: RawAutocomplete<Peer>(""",
        "Single-row Quick-Connect bar container & leading bolt icon",
    )

    txt = replace_exact(
        txt,
        """                          style: const TextStyle(
                            fontFamily: 'WorkSans',
                            fontSize: 22,
                            height: 1.4,
                          ),
                          maxLines: 1,
                          cursorColor:
                              Theme.of(context).textTheme.titleLarge?.color,
                          decoration: InputDecoration(
                              filled: false,
                              counterText: '',
                              hintText: _idInputFocused.value
                                  ? null
                                  : translate('Enter Remote ID'),
                              contentPadding: const EdgeInsets.symmetric(
                                  horizontal: 15, vertical: 13)),""",
        """                          style: const TextStyle(
                            fontFamily: 'WorkSans',
                            fontSize: 18,
                            fontWeight: FontWeight.w600,
                            letterSpacing: 0.4,
                            height: 1.25,
                            fontFeatures: [FontFeature.tabularFigures()],
                          ),
                          maxLines: 1,
                          cursorColor:
                              Theme.of(context).textTheme.titleLarge?.color,
                          decoration: InputDecoration(
                              filled: false,
                              isDense: true,
                              border: InputBorder.none,
                              enabledBorder: InputBorder.none,
                              focusedBorder: InputBorder.none,
                              counterText: '',
                              hintText: _idInputFocused.value
                                  ? null
                                  : translate('Enter Remote ID'),
                              contentPadding: const EdgeInsets.symmetric(
                                  horizontal: 6, vertical: 8)),""",
        "Compact borderless tabular input inside Quick-Connect bar",
    )

    txt = replace_exact(
        txt,
        """                  },
                )),
              ],
            ),
            Padding(
              padding: const EdgeInsets.only(top: 13.0),
              child: Row(mainAxisAlignment: MainAxisAlignment.end, children: [
                SizedBox(
                  height: 28.0,
                  child: ElevatedButton(
                    onPressed: () {
                      onConnect();
                    },
                    child: Text(translate("Connect")),
                  ),
                ),
                const SizedBox(width: 8),
                Container(
                  height: 28.0,
                  width: 28.0,
                  decoration: BoxDecoration(
                    border: Border.all(color: Theme.of(context).dividerColor),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Center(
                    child: StatefulBuilder(
                      builder: (context, setState) {
                        var offset = Offset(0, 0);
                        return Obx(() => InkWell(
                              child: _menuOpen.value
                                  ? Transform.rotate(
                                      angle: pi,
                                      child: Icon(IconFont.more, size: 14),
                                    )
                                  : Icon(IconFont.more, size: 14),
                              onTapDown: (e) {
                                offset = e.globalPosition;
                              },
                              onTap: () async {
                                _menuOpen.value = true;
                                final x = offset.dx;
                                final y = offset.dy;
                                await mod_menu
                                    .showMenu(
                                  context: context,
                                  position: RelativeRect.fromLTRB(x, y, x, y),
                                  items: [
                                    (
                                      'Transfer file',
                                      () => onConnect(isFileTransfer: true)
                                    ),
                                    (
                                      'View camera',
                                      () => onConnect(isViewCamera: true)
                                    ),
                                    (
                                      '${translate('Terminal')} (beta)',
                                      () => onConnect(isTerminal: true)
                                    ),
                                    // `connect` routes this through the
                                    // desktop path only; the peer card gates
                                    // it the same way.
                                    if (isDesktop)
                                      (
                                        'TCP tunneling',
                                        () => onConnect(isTcpTunneling: true)
                                      ),
                                  ]
                                      .map<MenuEntryBase<String>>(
                                          (e) => MenuEntryButton<String>(
                                            childBuilder: (TextStyle? style) =>
                                                Text(
                                              translate(e.$1),
                                              style: style,
                                            ),
                                            proc: () => e.$2(),
                                            padding: EdgeInsets.symmetric(
                                                horizontal:
                                                    kDesktopMenuPadding.left),
                                            dismissOnClicked: true,
                                          ))
                                      .followedBy([
                                        MenuEntryDivider<String>(),
                                        _requestApprovalMenu(context),
                                      ])
                                      .map((e) => e.build(
                                          context,
                                          const MenuConfig(
                                              commonColor: CustomPopupMenuTheme
                                                  .commonColor,
                                              height:
                                                  CustomPopupMenuTheme.height,
                                              dividerHeight:
                                                  CustomPopupMenuTheme
                                                      .dividerHeight)))
                                      .expand((i) => i)
                                      .toList(),
                                  elevation: 8,
                                )
                                    .then((_) {
                                  _menuOpen.value = false;
                                });
                              },
                            ));
                      },
                    ),
                  ),
                ),
              ]),
            ),
          ],
        ),
      ),
    );
    return Container(
        constraints: const BoxConstraints(maxWidth: 600), child: w);""",
        """                  },
                ),
            ),
            const SizedBox(width: 10),
            SizedBox(
              height: 36.0,
              child: ElevatedButton.icon(
                onPressed: () {
                  onConnect();
                },
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  elevation: 0,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(9),
                  ),
                ),
                icon: const Icon(Icons.arrow_forward_rounded, size: 16),
                label: Text(
                  translate("Connect"),
                  style: const TextStyle(
                    fontSize: 13.5,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ),
            const SizedBox(width: 6),
            Container(
              height: 36.0,
              width: 36.0,
              decoration: BoxDecoration(
                border: Border.all(
                  color: MyTheme.color(context).border ??
                      Theme.of(context).dividerColor,
                ),
                borderRadius: BorderRadius.circular(9),
              ),
              child: Center(
                child: StatefulBuilder(
                  builder: (context, setState) {
                    var offset = const Offset(0, 0);
                    return Obx(() => InkWell(
                          borderRadius: BorderRadius.circular(9),
                          child: _menuOpen.value
                              ? Transform.rotate(
                                  angle: pi,
                                  child: const Icon(IconFont.more, size: 14),
                                )
                              : const Icon(IconFont.more, size: 14),
                          onTapDown: (e) {
                            offset = e.globalPosition;
                          },
                          onTap: () async {
                            _menuOpen.value = true;
                            final x = offset.dx;
                            final y = offset.dy;
                            await mod_menu
                                .showMenu(
                              context: context,
                              position: RelativeRect.fromLTRB(x, y, x, y),
                              items: [
                                (
                                  'Transfer file',
                                  () => onConnect(isFileTransfer: true)
                                ),
                                (
                                  'View camera',
                                  () => onConnect(isViewCamera: true)
                                ),
                                (
                                  '${translate('Terminal')} (beta)',
                                  () => onConnect(isTerminal: true)
                                ),
                                if (isDesktop)
                                  (
                                    'TCP tunneling',
                                    () => onConnect(isTcpTunneling: true)
                                  ),
                              ]
                                  .map<MenuEntryBase<String>>(
                                      (e) => MenuEntryButton<String>(
                                            childBuilder: (TextStyle? style) =>
                                                Text(
                                              translate(e.$1),
                                              style: style,
                                            ),
                                            proc: () => e.$2(),
                                            padding: EdgeInsets.symmetric(
                                                horizontal:
                                                    kDesktopMenuPadding.left),
                                            dismissOnClicked: true,
                                          ))
                                  .map((e) => e.build(
                                      context,
                                      const MenuConfig(
                                          commonColor: CustomPopupMenuTheme
                                              .commonColor,
                                          height:
                                              CustomPopupMenuTheme.height,
                                          dividerHeight:
                                              CustomPopupMenuTheme
                                                  .dividerHeight)))
                                  .expand((i) => i)
                                  .toList(),
                              elevation: 8,
                            )
                                .then((_) {
                              _menuOpen.value = false;
                            });
                          },
                        ));
                  },
                ),
              ),
            ),
          ],
        ),
      ),
    );
    return Container(
        constraints: const BoxConstraints(maxWidth: 680), child: w);""",
        "Inline prominent Connect button & decluttered quick-mode menu",
    )

    write_text(conn_p, txt)

    # 2. peer_tab_model.dart: default tab order Favorites -> Recent -> LAN, default active tab = Favorites
    model_p = root / "flutter" / "lib" / "models" / "peer_tab_model.dart"
    mtxt = read_text(model_p)
    mtxt = replace_exact(
        mtxt,
        """  final List<int> orders =
      List.generate(maxTabCount, (index) => index, growable: false);""",
        """  final List<int> orders = [1, 0, 2, 3, 4];""",
        "Order peer tabs as Favorites, Recent, LAN by default",
    )
    mtxt = replace_exact(
        mtxt,
        """    // init currentTab
    _currentTab =
        int.tryParse(bind.getLocalFlutterOption(k: kOptionPeerTabIndex)) ?? 0;""",
        """    // init currentTab (default to Favorites for personal fleet UX)
    _currentTab =
        int.tryParse(bind.getLocalFlutterOption(k: kOptionPeerTabIndex)) ??
            PeerTabIndex.fav.index;""",
        "Default active peer tab to Favorites",
    )
    write_text(model_p, mtxt)

    # 3. peer_tab_page.dart: clean labeled pill tabs on Desktop/Landscape (icon + title)
    tab_p = root / "flutter" / "lib" / "common" / "widgets" / "peer_tab_page.dart"
    ttxt = read_text(tab_p)
    ttxt = replace_exact(
        ttxt,
        """        Obx(() => SizedBox(
              height: 32,""",
        """        Obx(() => SizedBox(
              height: 34,""",
        "PeerTabPage switch bar height 34px",
    )
    ttxt = replace_exact(
        ttxt,
        """          final selected = model.currentTab == t;
          final color = selected
              ? MyTheme.tabbar(context).selectedTextColor
              : MyTheme.tabbar(context).unSelectedTextColor
            ?..withOpacity(0.5);
          final hover = false.obs;
          final deco = BoxDecoration(
              color: Theme.of(context).colorScheme.background,
              borderRadius: BorderRadius.circular(6));
          final decoBorder = BoxDecoration(
              border: Border(
            bottom: BorderSide(width: 2, color: color!),
          ));
          counter += 1;
          return ReorderableDragStartListener(
              key: ValueKey(t),
              index: counter,
              child: Obx(() => Tooltip(
                    preferBelow: false,
                    message: model.tabTooltip(t),
                    onTriggered: isMobile ? mobileShowTabVisibilityMenu : null,
                    child: InkWell(
                      child: Container(
                        decoration: (hover.value
                            ? (selected ? decoBorder : deco)
                            : (selected ? decoBorder : null)),
                        child: Icon(model.tabIcon(t), color: color)
                            .paddingSymmetric(horizontal: 4),
                      ).paddingSymmetric(horizontal: 4),""",
        """          final selected = model.currentTab == t;
          final isPortrait = stateGlobal.isPortrait.isTrue;
          final baseColor = selected
              ? MyTheme.accent
              : (MyTheme.tabbar(context).unSelectedTextColor ??
                  Theme.of(context).textTheme.bodyMedium?.color);
          final color = selected ? baseColor : baseColor?.withOpacity(0.68);
          final hover = false.obs;
          final selectedDeco = BoxDecoration(
            color: MyTheme.accent.withOpacity(0.12),
            borderRadius: BorderRadius.circular(8),
          );
          final hoverDeco = BoxDecoration(
            color: Theme.of(context).colorScheme.background,
            borderRadius: BorderRadius.circular(8),
          );
          counter += 1;
          return ReorderableDragStartListener(
              key: ValueKey(t),
              index: counter,
              child: Obx(() => Tooltip(
                    preferBelow: false,
                    message: model.tabTooltip(t),
                    onTriggered: isMobile ? mobileShowTabVisibilityMenu : null,
                    child: InkWell(
                      borderRadius: BorderRadius.circular(8),
                      child: Container(
                        margin: const EdgeInsets.only(right: 4),
                        padding: EdgeInsets.symmetric(
                            horizontal: isPortrait ? 8 : 11, vertical: 5),
                        decoration: selected
                            ? selectedDeco
                            : (hover.value ? hoverDeco : null),
                        child: isPortrait
                            ? Icon(model.tabIcon(t), size: 18, color: color)
                            : Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(model.tabIcon(t),
                                      size: 15, color: color),
                                  const SizedBox(width: 6),
                                  Text(
                                    model.tabTooltip(t),
                                    style: TextStyle(
                                      fontSize: 13,
                                      fontWeight: selected
                                          ? FontWeight.w600
                                          : FontWeight.w500,
                                      color: color,
                                    ),
                                  ),
                                ],
                              ),
                      ),""",
        "Linear-style labeled pill tabs on Desktop & compact pills on Mobile",
    )
    write_text(tab_p, ttxt)

    # 4. peers_view.dart: calm minimal empty state icon instead of sad face
    pv_p = root / "flutter" / "lib" / "common" / "widgets" / "peers_view.dart"
    pvtxt = read_text(pv_p)
    pvtxt = replace_exact(
        pvtxt,
        """                Icon(
                  Icons.sentiment_very_dissatisfied_rounded,
                  color: Theme.of(context).tabBarTheme.labelColor,
                  size: 40,
                ).paddingOnly(bottom: 10),""",
        """                Icon(
                  Icons.devices_other_rounded,
                  color: Theme.of(context)
                      .tabBarTheme
                      .labelColor
                      ?.withOpacity(0.45),
                  size: 36,
                ).paddingOnly(bottom: 10),""",
        "Calm minimal devices icon for empty peer tab state",
    )
    write_text(pv_p, pvtxt)

    # 5. peer_card.dart: clean hostname · platform subtitle, online glow, hover Connect pill,
    #    and decluttered context menu
    card_p = root / "flutter" / "lib" / "common" / "widgets" / "peer_card.dart"
    ctxt = read_text(card_p)

    ctxt = replace_exact(
        ctxt,
        """  final double _cardRadius = 16;
  final double _tileRadius = 5;
  final double _borderWidth = 2;""",
        """  final double _cardRadius = 12;
  final double _tileRadius = 8;
  final double _borderWidth = 1.5;
  final RxBool _isHovered = false.obs;""",
        "PeerCard radii & hover state",
    )

    ctxt = replace_exact(
        ctxt,
        """    var deco = Rx<BoxDecoration?>(
      BoxDecoration(
        border: Border.all(color: Colors.transparent, width: _borderWidth),
        borderRadius: BorderRadius.circular(
          peerCardUiType.value == PeerUiType.grid ? _cardRadius : _tileRadius,
        ),
      ),
    );
    return MouseRegion(
      onEnter: (evt) {
        deco.value = BoxDecoration(
          border: Border.all(
              color: Theme.of(context).colorScheme.primary,
              width: _borderWidth),
          borderRadius: BorderRadius.circular(
            peerCardUiType.value == PeerUiType.grid ? _cardRadius : _tileRadius,
          ),
        );
      },
      onExit: (evt) {
        deco.value = BoxDecoration(
          border: Border.all(color: Colors.transparent, width: _borderWidth),
          borderRadius: BorderRadius.circular(
            peerCardUiType.value == PeerUiType.grid ? _cardRadius : _tileRadius,
          ),
        );
      },""",
        """    final restBorderColor =
        MyTheme.color(context).border ?? Colors.black12;
    var deco = Rx<BoxDecoration?>(
      BoxDecoration(
        border: Border.all(color: restBorderColor, width: 1.0),
        borderRadius: BorderRadius.circular(
          peerCardUiType.value == PeerUiType.grid ? _cardRadius : _tileRadius,
        ),
      ),
    );
    return MouseRegion(
      onEnter: (evt) {
        _isHovered.value = true;
        deco.value = BoxDecoration(
          border: Border.all(
              color: Theme.of(context).colorScheme.primary,
              width: _borderWidth),
          borderRadius: BorderRadius.circular(
            peerCardUiType.value == PeerUiType.grid ? _cardRadius : _tileRadius,
          ),
        );
      },
      onExit: (evt) {
        _isHovered.value = false;
        deco.value = BoxDecoration(
          border: Border.all(color: restBorderColor, width: 1.0),
          borderRadius: BorderRadius.circular(
            peerCardUiType.value == PeerUiType.grid ? _cardRadius : _tileRadius,
          ),
        );
      },""",
        "PeerCard resting border & hover tracking",
    )

    # Clean hostname · platform subtitle in list/tile/portrait mode
    ctxt = replace_exact(
        ctxt,
        """  makeChild(bool isPortrait, Peer peer) {
    final name = hideUsernameOnCard == true
        ? peer.hostname
        : '${peer.username}${peer.username.isNotEmpty && peer.hostname.isNotEmpty ? '@' : ''}${peer.hostname}';""",
        """  String _formatSubtitle(Peer peer) {
    final host = peer.hostname.trim().isNotEmpty
        ? peer.hostname.trim()
        : peer.username.trim();
    final plat = peer.platform.trim();
    if (host.isNotEmpty && plat.isNotEmpty) {
      return '$host · $plat';
    }
    return host.isNotEmpty ? host : plat;
  }

  makeChild(bool isPortrait, Peer peer) {
    final name = _formatSubtitle(peer);""",
        "Clean hostname · platform subtitle on PeerTile",
    )

    # Clean hostname · platform subtitle on desktop grid card
    ctxt = replace_exact(
        ctxt,
        """  Widget _buildPeerCard(
      BuildContext context, Peer peer, Rx<BoxDecoration?> deco) {
    hideUsernameOnCard ??=
        bind.mainGetBuildinOption(key: kHideUsernameOnCard) == 'Y';
    final name = hideUsernameOnCard == true
        ? peer.hostname
        : '${peer.username}${peer.username.isNotEmpty && peer.hostname.isNotEmpty ? '@' : ''}${peer.hostname}';""",
        """  Widget _buildPeerCard(
      BuildContext context, Peer peer, Rx<BoxDecoration?> deco) {
    final name = _formatSubtitle(peer);""",
        "Clean hostname · platform subtitle on PeerCard grid",
    )

    # One-click hover Connect pill on desktop grid card
    ctxt = replace_exact(
        ctxt,
        """        if (colors.isNotEmpty)
          Positioned(
            top: 4,
            right: 12,
            child: CustomPaint(
              painter: TagPainter(radius: 4, colors: colors),
            ),
          )
      ]),""",
        """        if (colors.isNotEmpty)
          Positioned(
            top: 4,
            right: 12,
            child: CustomPaint(
              painter: TagPainter(radius: 4, colors: colors),
            ),
          ),
        if (isDesktop || isWebDesktop)
          Obx(() => _isHovered.value
              ? Positioned(
                  bottom: 44,
                  right: 10,
                  child: Material(
                    color: MyTheme.accent.withOpacity(0.94),
                    borderRadius: BorderRadius.circular(16),
                    elevation: 2,
                    child: InkWell(
                      borderRadius: BorderRadius.circular(16),
                      onTap: () => widget.connect(context, peer.id),
                      child: Padding(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 10, vertical: 4),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Icon(Icons.play_arrow_rounded,
                                size: 15, color: Colors.white),
                            const SizedBox(width: 2),
                            Text(
                              translate('Connect'),
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 11,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                )
              : const SizedBox.shrink()),
      ]),""",
        "One-click hover Connect pill on desktop PeerCard",
    )

    # Remove stranger-facing 'Request approval' submenu from PeerCard context menu
    ctxt = replace_exact(
        ctxt,
        """    menuItems.add(MenuEntryDivider<String>());
    menuItems.add(_requestApprovalAction(context));
    // menuItems.add(await _openNewConnInOptAction(peer.id));""",
        """    if (!isWeb) {
      menuItems.add(MenuEntryDivider<String>());
    }""",
        "Remove stranger Request Approval submenu from PeerCard context menu",
    )

    # Soft-glow Emerald (online) / calm Slate (offline) indicator
    ctxt = replace_exact(
        ctxt,
        """Widget getOnline(double rightPadding, bool online) {
  return Tooltip(
      message: translate(online ? 'Online' : 'Offline'),
      waitDuration: const Duration(seconds: 1),
      child: Padding(
          padding: EdgeInsets.fromLTRB(0, 4, rightPadding, 4),
          child: CircleAvatar(
              radius: 3, backgroundColor: online ? Colors.green : kColorWarn)));
}""",
        """Widget getOnline(double rightPadding, bool online) {
  final dotColor = online ? const Color(0xFF22C55E) : const Color(0xFF64748B);
  return Tooltip(
      message: translate(online ? 'Online' : 'Offline'),
      waitDuration: const Duration(seconds: 1),
      child: Padding(
          padding: EdgeInsets.fromLTRB(0, 4, rightPadding, 4),
          child: Container(
            width: 8,
            height: 8,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: dotColor,
              boxShadow: online
                  ? [
                      BoxShadow(
                        color: dotColor.withOpacity(0.38),
                        blurRadius: 5,
                        spreadRadius: 1,
                      ),
                    ]
                  : null,
            ),
          )));
}""",
        "Industrial Emerald/Slate online status indicator",
    )

    write_text(card_p, ctxt)


def patch_desktop_settings(root: Path, update_repo: str) -> None:
    p = root / "flutter" / "lib" / "desktop" / "pages" / "desktop_setting_page.dart"
    txt = read_text(p)
    repo_url = f"https://github.com/{update_repo}"

    # 1. Declutter Desktop Settings sidebar tabs: hide unused Printer & Account tabs,
    #    order cleanly as General, Display, Network, Security, About
    txt = replace_exact(
        txt,
        """  static final List<SettingsTabKey> tabKeys = [
    if (bind.mainGetBuildinOption(key: kOptionHideGeneralSetting) != 'Y')
      SettingsTabKey.general,
    if (!isWeb &&
        !bind.isOutgoingOnly() &&
        !bind.isDisableSettings() &&
        bind.mainGetBuildinOption(key: kOptionHideSecuritySetting) != 'Y')
      SettingsTabKey.safety,
    if (!bind.isDisableSettings() &&
        bind.mainGetBuildinOption(key: kOptionHideNetworkSetting) != 'Y')
      SettingsTabKey.network,
    if (!bind.isIncomingOnly()) SettingsTabKey.display,
    if (!bind.isDisableAccount()) SettingsTabKey.account,
    if (isWindows &&
        !bind.isDisableSettings() &&
        bind.mainGetBuildinOption(key: kOptionHideRemotePrinterSetting) != 'Y')
      SettingsTabKey.printer,
    SettingsTabKey.about,
  ];""",
        """  static final List<SettingsTabKey> tabKeys = [
    if (bind.mainGetBuildinOption(key: kOptionHideGeneralSetting) != 'Y')
      SettingsTabKey.general,
    if (!bind.isIncomingOnly()) SettingsTabKey.display,
    if (!bind.isDisableSettings() &&
        bind.mainGetBuildinOption(key: kOptionHideNetworkSetting) != 'Y')
      SettingsTabKey.network,
    if (!isWeb &&
        !bind.isOutgoingOnly() &&
        !bind.isDisableSettings() &&
        bind.mainGetBuildinOption(key: kOptionHideSecuritySetting) != 'Y')
      SettingsTabKey.safety,
    SettingsTabKey.about,
  ];""",
        "Declutter Desktop Settings sidebar to General, Display, Network, Security, About",
    )

    # 2. Hide stranger-facing 2FA + Telegram bot card in Security tab unless actively set
    txt = replace_exact(
        txt,
        """                permissions(context),
                password(context),
                _Card(title: '2FA', children: [tfa()]),""",
        """                permissions(context),
                password(context),
                if (bind.mainHasValid2FaSync())
                  _Card(title: '2FA', children: [tfa()]),""",
        "Hide unused 2FA card in Desktop Security settings",
    )

    # 3. Clean Desktop About page (remove Purslane Tech banner & rustdesk.com links)
    txt = replace_exact(
        txt,
        """        child: _Card(title: translate('About RustDesk'), children: [""",
        """        child: _Card(title: 'RRRemote', children: [""",
        "Rename Desktop About card title to RRRemote",
    )
    txt = replace_exact(
        txt,
        """              InkWell(
                  onTap: () {
                    launchUrlString('https://rustdesk.com/privacy.html');
                  },
                  child: Text(
                    translate('Privacy Statement'),
                    style: linkStyle,
                  ).marginSymmetric(vertical: 4.0)),
              InkWell(
                  onTap: () {
                    launchUrlString('https://rustdesk.com');
                  },
                  child: Text(
                    translate('Website'),
                    style: linkStyle,
                  ).marginSymmetric(vertical: 4.0)),
              Container(
                decoration: const BoxDecoration(color: Color(0xFF2c8cff)),
                padding:
                    const EdgeInsets.symmetric(vertical: 24, horizontal: 8),
                child: SelectionArea(
                    child: Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Copyright © ${DateTime.now().toString().substring(0, 4)} Purslane Tech Pte. Ltd.\\n$license',
                            style: const TextStyle(color: Colors.white),
                          ),
                          Text(
                            translate('Slogan_tip'),
                            style: TextStyle(
                                fontWeight: FontWeight.w800,
                                color: Colors.white),
                          )
                        ],
                      ),
                    ),
                  ],
                )),
              ).marginSymmetric(vertical: 4.0)""",
        f"""              InkWell(
                  onTap: () {{
                    launchUrlString('{repo_url}');
                  }},
                  child: const Text(
                    'GitHub Repository ({update_repo})',
                    style: linkStyle,
                  ).marginSymmetric(vertical: 4.0)),
              Container(
                margin: const EdgeInsets.only(top: 8, bottom: 4),
                padding:
                    const EdgeInsets.symmetric(vertical: 14, horizontal: 14),
                decoration: BoxDecoration(
                  color: MyTheme.accent.withOpacity(0.10),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(
                    color: MyTheme.accent.withOpacity(0.25),
                  ),
                ),
                child: SelectionArea(
                  child: Row(
                    children: [
                      Expanded(
                        child: Text(
                          'RRRemote Personal Edition · Self-Hosted Zero-Friction Remote Control\\n$license',
                          style: TextStyle(
                            fontSize: 12.5,
                            height: 1.45,
                            color: Theme.of(context).textTheme.bodyMedium?.color,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              )""",
        "Clean Desktop About page branding & repository link",
    )

    write_text(p, txt)


def patch_remote_toolbar(root: Path) -> None:
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
  static EdgeInsets menuPadding = isWindows
      ? EdgeInsets.fromLTRB(6, 10, 6, 10)
      : EdgeInsets.fromLTRB(6, 12, 6, 12);
  static const double menuButtonBorderRadius = 6.0;""",
        "Remote toolbar menu radii & elevation",
    )
    txt = replace_exact(
        txt,
        "    final toolbarBorderRadius = BorderRadius.all(Radius.circular(4.0));",
        "    final toolbarBorderRadius = BorderRadius.all(Radius.circular(10.0));",
        "Remote toolbar capsule border radius 10px",
    )

    write_text(p, txt)


def patch_mobile_ui(root: Path, update_repo: str) -> None:
    repo_url = f"https://github.com/{update_repo}"

    # 1. Mobile home_page.dart: remove stranger Chat tab on Android & add crisp hairline divider
    home_p = root / "flutter" / "lib" / "mobile" / "pages" / "home_page.dart"
    htxt = read_text(home_p)
    htxt = replace_exact(
        htxt,
        """    if (isAndroid && !bind.isOutgoingOnly()) {
      _chatPageTabIndex = _pages.length;
      _pages.addAll([ChatPage(type: ChatPageType.mobileMain), ServerPage()]);
    }""",
        """    if (isAndroid && !bind.isOutgoingOnly()) {
      _chatPageTabIndex = -1;
      _pages.add(ServerPage());
    }""",
        "Remove redundant Chat tab from Android bottom navigation",
    )
    htxt = replace_exact(
        htxt,
        """          bottomNavigationBar: BottomNavigationBar(
            key: navigationBarKey,""",
        """          bottomNavigationBar: Container(
            decoration: BoxDecoration(
              border: Border(
                top: BorderSide(
                  color: MyTheme.color(context).divider ?? Colors.black12,
                  width: 0.5,
                ),
              ),
            ),
            child: BottomNavigationBar(
            key: navigationBarKey,""",
        "Mobile BottomNavigationBar hairline divider (open)",
    )
    htxt = replace_exact(
        htxt,
        """            }),
          ),
          body: _pages.elementAt(_selectedIndex),""",
        """            }),
          ),
          ),
          body: _pages.elementAt(_selectedIndex),""",
        "Mobile BottomNavigationBar hairline divider (close)",
    )
    write_text(home_p, htxt)

    # 2. Mobile connection_page.dart: sleek compact Quick-Connect bar & accent Connect button
    conn_p = root / "flutter" / "lib" / "mobile" / "pages" / "connection_page.dart"
    ctxt = read_text(conn_p)
    ctxt = ensure_import(ctxt, "import 'dart:ui' show FontFeature;")

    ctxt = replace_exact(
        ctxt,
        "final url = 'https://rustdesk.com/download';",
        f"final url = 'https://github.com/{update_repo}/releases/latest';",
        "Redirect mobile update URL to RRRemote repo",
    )
    ctxt = replace_exact(
        ctxt,
        """            child: Container(
                alignment: AlignmentDirectional.center,
                width: double.infinity,
                color: Colors.pinkAccent,
                padding: const EdgeInsets.symmetric(vertical: 12),
                child: Text(translate('Download new version'),
                    style: const TextStyle(
                        color: Colors.white, fontWeight: FontWeight.bold))));""",
        """            child: Container(
                alignment: AlignmentDirectional.center,
                width: double.infinity,
                margin: const EdgeInsets.only(bottom: 8),
                decoration: BoxDecoration(
                  color: MyTheme.accent,
                  borderRadius: BorderRadius.circular(10),
                ),
                padding: const EdgeInsets.symmetric(vertical: 11),
                child: Text(translate('Download new version'),
                    style: const TextStyle(
                        color: Colors.white,
                        fontSize: 13,
                        fontWeight: FontWeight.w600))));""",
        "Mobile update banner refined accent pill",
    )
    ctxt = replace_exact(
        ctxt,
        """    final w = SizedBox(
      height: 84,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 2),
        child: Ink(
          decoration: BoxDecoration(
            color: Theme.of(context).cardColor,
            borderRadius: BorderRadius.all(Radius.circular(13)),
          ),""",
        """    final w = SizedBox(
      height: 70,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 2),
        child: Ink(
          decoration: BoxDecoration(
            color: Theme.of(context).cardColor,
            borderRadius: const BorderRadius.all(Radius.circular(12)),
            border: Border.all(
              color: MyTheme.color(context).border ?? Colors.black12,
              width: 1,
            ),
          ),""",
        "Streamline Mobile Quick-Connect card height & border",
    )
    ctxt = replace_exact(
        ctxt,
        """                        style: const TextStyle(
                          fontFamily: 'WorkSans',
                          fontWeight: FontWeight.bold,
                          fontSize: 30,
                          color: MyTheme.idColor,
                        ),""",
        """                        style: const TextStyle(
                          fontFamily: 'WorkSans',
                          fontWeight: FontWeight.w700,
                          fontSize: 22,
                          color: MyTheme.idColor,
                          fontFeatures: [FontFeature.tabularFigures()],
                        ),""",
        "Clean tabular numerals in Mobile Quick-Connect input",
    )
    ctxt = replace_exact(
        ctxt,
        """              SizedBox(
                width: 60,
                height: 60,
                child: IconButton(
                  icon: const Icon(Icons.arrow_forward,
                      color: MyTheme.darkGray, size: 45),
                  onPressed: onConnect,
                ),
              ),""",
        """              Padding(
                padding: const EdgeInsets.only(right: 8),
                child: Material(
                  color: MyTheme.accent,
                  borderRadius: BorderRadius.circular(10),
                  child: InkWell(
                    borderRadius: BorderRadius.circular(10),
                    onTap: onConnect,
                    child: const SizedBox(
                      width: 42,
                      height: 42,
                      child: Icon(
                        Icons.arrow_forward_rounded,
                        color: Colors.white,
                        size: 22,
                      ),
                    ),
                  ),
                ),
              ),""",
        "Prominent accent Connect button on Mobile Quick-Connect bar",
    )
    write_text(conn_p, ctxt)

    # 3. Mobile server_page.dart: remove One-time Password block, bypass 12s stranger scam dialog,
    #    hide removed chat tab jump icon, and rebrand storage label
    srv_p = root / "flutter" / "lib" / "mobile" / "pages" / "server_page.dart"
    stxt = read_text(srv_p)
    stxt = ensure_import(stxt, "import 'dart:ui' show FontFeature;")

    stxt = replace_exact(
        stxt,
        """                onPressed: () {
                  if (gFFI.userModel.userName.value.isEmpty &&
                      bind.mainGetLocalOption(key: "show-scam-warning") !=
                          "N") {
                    showScamWarning(context, serverModel);
                  } else {
                    serverModel.toggleService();
                  }
                },""",
        """                onPressed: () {
                  serverModel.toggleService();
                },""",
        "Bypass stranger scam countdown when starting Mobile screen share service",
    )
    stxt = replace_exact(
        stxt,
        """            PermissionRow(
                translate("Screen Capture"),
                serverModel.mediaOk,
                !serverModel.mediaOk &&
                        gFFI.userModel.userName.value.isEmpty &&
                        bind.mainGetLocalOption(key: "show-scam-warning") != "N"
                    ? () => showScamWarning(context, serverModel)
                    : serverModel.toggleService),""",
        """            PermissionRow(
                translate("Screen Capture"),
                serverModel.mediaOk,
                serverModel.toggleService),""",
        "Bypass stranger scam countdown on Mobile Screen Capture permission toggle",
    )
    stxt = replace_exact(
        stxt,
        """    final showOneTime = serverModel.approveMode != 'click' &&
        serverModel.verificationMethod != kUsePermanentPassword;
    return PaddingCard(
        title: translate('Your Device'),
        child: Column(
          // ID
          children: [
            Row(children: [
              const Icon(Icons.perm_identity,
                      color: Colors.grey, size: iconSize)
                  .marginOnly(right: iconMarginRight),
              Text(
                translate('ID'),
                style: textStyleHeading,
              )
            ]),
            Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
              Text(
                model.serverId.value.text,
                style: textStyleValue,
              ),
              IconButton(
                  visualDensity: VisualDensity.compact,
                  icon: Icon(Icons.copy_outlined),
                  onPressed: () {
                    copyToClipboard(model.serverId.value.text.trim());
                  })
            ]).marginOnly(left: 39, bottom: 10),
            // Password
            Row(children: [
              const Icon(Icons.lock_outline, color: Colors.grey, size: iconSize)
                  .marginOnly(right: iconMarginRight),
              Text(
                translate('One-time Password'),
                style: textStyleHeading,
              )
            ]),
            Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
              Text(
                !showOneTime ? '-' : model.serverPasswd.value.text,
                style: textStyleValue,
              ),
              !showOneTime
                  ? SizedBox.shrink()
                  : Row(children: [
                      IconButton(
                          visualDensity: VisualDensity.compact,
                          icon: const Icon(Icons.refresh),
                          onPressed: () => bind.mainUpdateTemporaryPassword()),
                      IconButton(
                          visualDensity: VisualDensity.compact,
                          icon: Icon(Icons.copy_outlined),
                          onPressed: () {
                            copyToClipboard(
                                model.serverPasswd.value.text.trim());
                          })
                    ])
            ]).marginOnly(left: 40, bottom: 15),
            ConnectionStateNotification()
          ],
        ));""",
        """    return PaddingCard(
        title: translate('Your Device'),
        child: Column(
          children: [
            Row(children: [
              const Icon(Icons.perm_identity,
                      color: Colors.grey, size: iconSize)
                  .marginOnly(right: iconMarginRight),
              Text(
                translate('ID'),
                style: textStyleHeading,
              )
            ]),
            Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
              Text(
                model.serverId.value.text,
                style: const TextStyle(
                  fontSize: 24.0,
                  fontWeight: FontWeight.w700,
                  fontFeatures: [FontFeature.tabularFigures()],
                ),
              ),
              IconButton(
                  visualDensity: VisualDensity.compact,
                  icon: const Icon(Icons.copy_rounded),
                  onPressed: () {
                    copyToClipboard(model.serverId.value.text.trim());
                  })
            ]).marginOnly(left: 39, bottom: 12),
            const Divider(height: 1),
            const SizedBox(height: 12),
            ConnectionStateNotification()
          ],
        ));""",
        "Remove One-time Password block from Mobile Share Screen ServerInfo card",
    )
    stxt = replace_exact(
        stxt,
        "title: Text(translate('RustDesk storage')),",
        "title: Text(translate('RRRemote storage')),",
        "Rebrand Android file transfer workspace label",
    )
    stxt = replace_exact(
        stxt,
        "child: client.isFileTransfer || !client.authorized",
        "child: true",
        "Hide removed Chat tab shortcut in Mobile ConnectionManager",
    )
    write_text(srv_p, stxt)

    # 4. Mobile settings_page.dart: hide enterprise Deploy & unused 2FA section, clean About links
    mset_p = root / "flutter" / "lib" / "mobile" / "pages" / "settings_page.dart"
    mstxt = read_text(mset_p)

    mstxt = replace_exact(
        mstxt,
        """                onPressed: (context) {
                  changeSocks5Proxy();
                }),
          if (isAndroid && !bind.isOutgoingOnly())
            SettingsTile(
                title: Text(translate('Deploy')),
                leading: Icon(Icons.cloud_upload),
                onPressed: (context) {
                  showDeployDialog();
                }),""",
        """                onPressed: (context) {
                  changeSocks5Proxy();
                }),
          // RRRemote personal edition: enterprise Deploy tile omitted""",
        "Hide enterprise MDM Deploy tile in Mobile Settings",
    )
    mstxt = replace_exact(
        mstxt,
        """        if (isAndroid &&
            !disabledSettings &&
            !outgoingOnly &&
            !hideSecuritySettings)
          SettingsSection(title: Text('2FA'), tiles: tfaTiles),""",
        """        if (isAndroid &&
            !disabledSettings &&
            !outgoingOnly &&
            !hideSecuritySettings &&
            enable2fa)
          SettingsSection(title: Text('2FA'), tiles: tfaTiles),""",
        "Hide unused 2FA section in Mobile Settings",
    )
    mstxt = replace_exact(
        mstxt,
        """            SettingsTile(
              title: Text(translate("Privacy Statement")),
              onPressed: (context) =>
                  launchUrlString('https://rustdesk.com/privacy.html'),
              leading: Icon(Icons.privacy_tip),
            )""",
        f"""            SettingsTile(
              title: const Text('GitHub Repository'),
              onPressed: (context) => launchUrlString('{repo_url}'),
              leading: const Icon(Icons.code_rounded),
            )""",
        "Replace Privacy Statement tile with GitHub Repository in Mobile About",
    )
    mstxt = (
        mstxt.replace("'https://rustdesk.com/'", f"'{repo_url}'")
        .replace("'https://rustdesk.com/privacy.html'", f"'{repo_url}'")
        .replace("Text('rustdesk.com'", "Text('RRRemote'")
        .replace("translate('About RustDesk')", "'About RRRemote'")
        .replace("translate('Keep RustDesk background service')", "'Keep RRRemote background service'")
    )
    write_text(mset_p, mstxt)


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    update_repo = os.environ.get("UPDATE_REPO", "melotusme/RRRemote").strip()
    print(f"[rrremote-ui] Applying personal-edition UI & layout refactor to {root}")
    patch_common_theme(root, update_repo)
    patch_desktop_home_page(root, update_repo)
    patch_desktop_connection_and_tabs(root)
    patch_desktop_settings(root, update_repo)
    patch_remote_toolbar(root)
    patch_mobile_ui(root, update_repo)
    print("[rrremote-ui] Personal-edition UI & layout refactor complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
