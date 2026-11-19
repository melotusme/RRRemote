#!/usr/bin/env python3
"""
Apply RRRemote industrial-grade UI & multi-platform UX polish to upstream
RustDesk 1.5.3 Flutter sources.

Design principles:
- Compatible with both Flutter 3.24.5 (Win/Linux/Android/iOS/macOS-x64) and
  Flutter 3.44.9 (macOS-arm64).
- Zero hardcoded personal servers/keys/IPs.
- Idempotent and strictly verified: every critical patch reports hit/skip clearly.
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
    # Insert after first import line
    m = re.search(r"^import\s+['\"][^'\"]+['\"][^;]*;\s*$", content, flags=re.MULTILINE)
    if not m:
        return import_line + "\n" + content
    idx = m.end()
    return content[:idx] + "\n" + import_line + content[idx:]


def patch_common_theme(root: Path) -> None:
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

    # 4. Harmonize ListTile & Checkbox radii to 8px / 6px
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

    # 5. Polish Light Theme (crisp borders, 14px dialogs, 10px inputs, 8px buttons)
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

    # 6. Polish Dark Theme (Obsidian Slate surfaces, refined borders, 14px dialogs, 10px inputs)
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

    write_text(p, txt)


def patch_desktop_home_page(root: Path, update_repo: str) -> None:
    p = root / "flutter" / "lib" / "desktop" / "pages" / "desktop_home_page.dart"
    txt = read_text(p)
    txt = ensure_import(txt, "import 'dart:ui' show FontFeature;")

    # 1. Slightly wider, more breathable left host panel (200 -> 228)
    txt = replace_exact(
        txt,
        "width: isIncomingOnly ? 280.0 : 200.0,",
        "width: isIncomingOnly ? 288.0 : 228.0,",
        "Widen left host pane to 228px",
    )

    # 2. Tabular numerals + explicit one-click Copy ID button in buildIDBoard
    txt = replace_exact(
        txt,
        """                      child: TextFormField(
                        controller: model.serverId,
                        readOnly: true,
                        decoration: InputDecoration(
                          border: InputBorder.none,
                          contentPadding: EdgeInsets.only(top: 10, bottom: 10),
                        ),
                        style: TextStyle(
                          fontSize: 22,
                        ),
                      ).workaroundFreezeLinuxMint(),""",
        """                      child: Row(
                        children: [
                          Expanded(
                            child: TextFormField(
                              controller: model.serverId,
                              readOnly: true,
                              decoration: InputDecoration(
                                border: InputBorder.none,
                                enabledBorder: InputBorder.none,
                                focusedBorder: InputBorder.none,
                                filled: false,
                                contentPadding: EdgeInsets.only(top: 10, bottom: 10),
                              ),
                              style: TextStyle(
                                fontSize: 21,
                                fontWeight: FontWeight.w600,
                                letterSpacing: 0.6,
                                fontFeatures: const [FontFeature.tabularFigures()],
                              ),
                            ).workaroundFreezeLinuxMint(),
                          ),
                          Tooltip(
                            message: translate("Copy"),
                            child: InkWell(
                              borderRadius: BorderRadius.circular(6),
                              onTap: () {
                                Clipboard.setData(
                                    ClipboardData(text: model.serverId.text));
                                showToast(translate("Copied"));
                              },
                              child: Padding(
                                padding: const EdgeInsets.all(6),
                                child: Icon(
                                  Icons.copy_rounded,
                                  size: 16,
                                  color: Theme.of(context)
                                      .textTheme
                                      .titleLarge
                                      ?.color
                                      ?.withOpacity(0.65),
                                ),
                              ),
                            ),
                          ),
                        ],
                      ),""",
        "One-click Copy ID button & tabular numerals",
    )

    # 3. Clean password field borderless + tabular numerals
    txt = replace_exact(
        txt,
        """                            decoration: InputDecoration(
                              border: InputBorder.none,
                              contentPadding:
                                  EdgeInsets.only(top: 14, bottom: 10),
                            ),
                            style: TextStyle(fontSize: 15),""",
        """                            decoration: InputDecoration(
                              border: InputBorder.none,
                              enabledBorder: InputBorder.none,
                              focusedBorder: InputBorder.none,
                              filled: false,
                              contentPadding:
                                  EdgeInsets.only(top: 14, bottom: 10),
                            ),
                            style: TextStyle(
                              fontSize: 15,
                              fontWeight: FontWeight.w500,
                              fontFeatures: const [FontFeature.tabularFigures()],
                            ),""",
        "Tabular numerals for host password",
    )

    # 4. Redirect desktop update card links to RRRemote GitHub Releases
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

    # 5. Replace garish pink-magenta buildInstallCard with refined slate-indigo card
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
              12, marginTop, 12, bind.isIncomingOnly() ? marginTop : 0),
          child: Container(
              decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: Colors.white.withOpacity(0.14),
                    width: 1,
                  ),
                  gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [
                  Color(0xFF1E3A8A),
                  Color(0xFF2563EB),
                ],
              )),
              padding: EdgeInsets.all(14),""",
        "Refined slate-indigo status card (replaces pink gradient)",
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
                                      width: 144,
                                      padding: 7,
                                      isOutline: true,
                                      text: translate(btnText),
                                      textColor: Colors.white,
                                      borderColor: Colors.white70,
                                      textSize: 14,
                                      radius: 8,
                                      onTap: onPressed,
                                    )""",
        "Refined status card action button typography",
    )

    write_text(p, txt)


def patch_desktop_connection_page(root: Path) -> None:
    p = root / "flutter" / "lib" / "desktop" / "pages" / "connection_page.dart"
    txt = read_text(p)
    txt = ensure_import(txt, "import 'dart:ui' show FontFeature;")
    txt = ensure_import(
        txt, "import 'package:flutter_hbb/desktop/pages/desktop_setting_page.dart';"
    )

    # 1. Replace rustdesk.com/pricing link with direct jump to Network / Self-Hosted Server Settings
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

    # 2. Polish status indicator dot + add always-accessible Server Settings shortcut in status bar
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
              height: 9,
              width: 9,
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
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          Icons.dns_rounded,
                          size: 14,
                          color: Theme.of(context)
                              .textTheme
                              .bodySmall
                              ?.color
                              ?.withOpacity(0.7),
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
                                ?.withOpacity(0.75),
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

    # 3. Polish Remote ID input container border and tabular numerals
    txt = replace_exact(
        txt,
        """    var w = Container(
      width: 320 + 20 * 2,
      padding: const EdgeInsets.fromLTRB(20, 24, 20, 22),
      decoration: BoxDecoration(
          borderRadius: const BorderRadius.all(Radius.circular(13)),
          border: Border.all(color: Theme.of(context).colorScheme.background)),""",
        """    var w = Container(
      width: 360 + 20 * 2,
      padding: const EdgeInsets.fromLTRB(20, 20, 20, 18),
      decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.background.withOpacity(0.55),
          borderRadius: const BorderRadius.all(Radius.circular(12)),
          border: Border.all(
            color: MyTheme.color(context).border ?? Theme.of(context).colorScheme.background,
            width: 1,
          )),""",
        "Refined Remote ID container surface & border",
    )

    txt = replace_exact(
        txt,
        """                          style: const TextStyle(
                            fontFamily: 'WorkSans',
                            fontSize: 22,
                            height: 1.4,
                          ),""",
        """                          style: const TextStyle(
                            fontFamily: 'WorkSans',
                            fontSize: 21,
                            fontWeight: FontWeight.w500,
                            letterSpacing: 0.5,
                            height: 1.35,
                            fontFeatures: [FontFeature.tabularFigures()],
                          ),""",
        "Tabular numerals in Remote ID input",
    )

    write_text(p, txt)


def patch_peer_card(root: Path) -> None:
    p = root / "flutter" / "lib" / "common" / "widgets" / "peer_card.dart"
    txt = read_text(p)

    # 1. Refined radii & crisp 1.5px hover border
    txt = replace_exact(
        txt,
        """  final double _cardRadius = 16;
  final double _tileRadius = 5;
  final double _borderWidth = 2;""",
        """  final double _cardRadius = 12;
  final double _tileRadius = 8;
  final double _borderWidth = 1.5;
  final RxBool _isHovered = false.obs;""",
        "PeerCard radii & hover state",
    )

    # 2. Subtle resting border + crisp accent hover border + track hover for quick-connect pill
    txt = replace_exact(
        txt,
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

    # 3. Quick-connect floating pill button on desktop grid card hover (UU Remote style one-click)
    txt = replace_exact(
        txt,
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
                    color: MyTheme.accent.withOpacity(0.92),
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

    # 4. Upgrade online dot to soft-glow Emerald (online) / calm Slate (offline)
    txt = replace_exact(
        txt,
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
  final dotColor = online ? const Color(0xFF22C55E) : const Color(0xFF94A3B8);
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
    # 1. Mobile connection_page.dart: replace pinkAccent update banner & refine ID card
    conn_p = root / "flutter" / "lib" / "mobile" / "pages" / "connection_page.dart"
    txt = read_text(conn_p)

    txt = replace_exact(
        txt,
        "final url = 'https://rustdesk.com/download';",
        f"final url = 'https://github.com/{update_repo}/releases/latest';",
        "Redirect mobile update URL to RRRemote repo",
    )
    txt = replace_exact(
        txt,
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
    txt = replace_exact(
        txt,
        """          decoration: BoxDecoration(
            color: Theme.of(context).cardColor,
            borderRadius: BorderRadius.all(Radius.circular(13)),
          ),""",
        """          decoration: BoxDecoration(
            color: Theme.of(context).cardColor,
            borderRadius: const BorderRadius.all(Radius.circular(12)),
            border: Border.all(
              color: MyTheme.color(context).border ?? Colors.black12,
              width: 1,
            ),
          ),""",
        "Mobile Remote ID input card border & radius",
    )
    write_text(conn_p, txt)

    # 2. Mobile home_page.dart: crisp border on BottomNavigationBar
    home_p = root / "flutter" / "lib" / "mobile" / "pages" / "home_page.dart"
    htxt = read_text(home_p)
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


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    update_repo = os.environ.get("UPDATE_REPO", "melotusme/RRRemote").strip()
    print(f"[rrremote-ui] Applying industrial UI & UX polish to {root}")
    patch_common_theme(root)
    patch_desktop_home_page(root, update_repo)
    patch_desktop_connection_page(root)
    patch_peer_card(root)
    patch_remote_toolbar(root)
    patch_mobile_ui(root, update_repo)
    print("[rrremote-ui] Industrial UI & UX polish complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
