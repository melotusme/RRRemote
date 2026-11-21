"""Design tokens (RrColors, RrText), Light/Dark themes, and brand chrome in flutter/lib/common.dart.

Every color pair is verified against WCAG 2.2 AA (>= 4.5:1 normal text, >= 3.0:1 UI
boundaries/dots/focus rings) in both Light and Dark appearances, with >= 100 deg OKLCH
hue separation between accent and status ramps.

Flutter 3.24.5 + 3.44.9 dual-compatibility invariants:
- Preserve `dialogTheme: DialogTheme(` (2 occurrences) and `tabBarTheme: const TabBarTheme(`
  (2 occurrences) and `scrollbarTheme: scrollbarThemeDark,` so upstream
  `.github/patches/apply_flutter_3.44_source_patches.sh` passes `is_unpatched_state`
  and `is_complete_patch_state`.
- Never emit literal `backgroundColor: Colors.white,` or `backgroundColor: Color(0xFF18191E),`.
- Never use `Color.withValues()` (not available in Flutter 3.24.5).
"""

from __future__ import annotations

from pathlib import Path

from . import ensure_import, read_text, replace_exact, write_text


def patch_common_theme(root: Path, update_repo: str) -> None:
    p = root / "flutter" / "lib" / "common.dart"
    txt = read_text(p)
    txt = ensure_import(txt, "import 'dart:ui' show FontFeature;")

    # 1. Refine ColorThemeExtension light/dark palettes + append verified RrColors & RrText
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
    border: Color(0xFFCBD5E1),
    border2: Color(0xFF7C8BA1),
    border3: Color(0x1F0F172A),
    highlight: Color(0xFFF1F5F9),
    drag_indicator: Color(0xFF475569),
    shadow: Color(0x240F172A),
    errorBannerBg: Color(0xFFFEE2E2),
    me: Color(0xFF15803D),
    toastBg: Color(0xEB0F172A),
    toastText: Color(0xFFFFFFFF),
    divider: Color(0xFFCBD5E1),
  );

  static final dark = ColorThemeExtension(
    border: Color(0xFF2A3142),
    border2: Color(0xFF64748B),
    border3: Color(0x29FFFFFF),
    highlight: Color(0xFF1B202E),
    drag_indicator: Color(0xFF94A3B8),
    shadow: Color(0x73000000),
    errorBannerBg: Color(0xFF311319),
    me: Color(0xFF22C55E),
    toastBg: Color(0xF01B202E),
    toastText: Color(0xFFF8FAFC),
    divider: Color(0xFF2A3142),
  );""",
        "ColorThemeExtension light/dark palettes",
    )

    # 2. Fix upstream ColorThemeExtension.lerp bug (wrongly lerping from `shadow`)
    #    and inject RrColors (semantic WCAG AA tokens) + RrText (type scale & mono helpers)
    txt = replace_exact(
        txt,
        """      errorBannerBg: Color.lerp(shadow, other.errorBannerBg, t),
      me: Color.lerp(shadow, other.me, t),
      toastBg: Color.lerp(shadow, other.toastBg, t),
      toastText: Color.lerp(shadow, other.toastText, t),
      divider: Color.lerp(shadow, other.divider, t),
    );
  }
}""",
        """      errorBannerBg: Color.lerp(errorBannerBg, other.errorBannerBg, t),
      me: Color.lerp(me, other.me, t),
      toastBg: Color.lerp(toastBg, other.toastBg, t),
      toastText: Color.lerp(toastText, other.toastText, t),
      divider: Color.lerp(divider, other.divider, t),
    );
  }
}

/// Verified WCAG 2.2 AA semantic color tokens for RRRemote (Light & Dark).
class RrColors extends ThemeExtension<RrColors> {
  const RrColors({
    required this.bgCanvas,
    required this.bgSurface,
    required this.bgSubtle,
    required this.bgHover,
    required this.borderSubtle,
    required this.borderControl,
    required this.textPrimary,
    required this.textSecondary,
    required this.textMuted,
    required this.accentSolid,
    required this.accentHover,
    required this.accentText,
    required this.accentSoft,
    required this.focusRing,
    required this.successSolid,
    required this.successSoft,
    required this.successText,
    required this.warningSolid,
    required this.warningSoft,
    required this.warningText,
    required this.dangerSolid,
    required this.dangerSoft,
    required this.dangerText,
    required this.offlineSolid,
    required this.imageOutline,
  });

  final Color bgCanvas;
  final Color bgSurface;
  final Color bgSubtle;
  final Color bgHover;
  final Color borderSubtle;
  final Color borderControl;
  final Color textPrimary;
  final Color textSecondary;
  final Color textMuted;
  final Color accentSolid;
  final Color accentHover;
  final Color accentText;
  final Color accentSoft;
  final Color focusRing;
  final Color successSolid;
  final Color successSoft;
  final Color successText;
  final Color warningSolid;
  final Color warningSoft;
  final Color warningText;
  final Color dangerSolid;
  final Color dangerSoft;
  final Color dangerText;
  final Color offlineSolid;
  final Color imageOutline;

  static const light = RrColors(
    bgCanvas: Color(0xFFF8FAFC),
    bgSurface: Color(0xFFFFFFFF),
    bgSubtle: Color(0xFFF1F5F9),
    bgHover: Color(0xFFE2E8F0),
    borderSubtle: Color(0xFFCBD5E1),
    borderControl: Color(0xFF7C8BA1),
    textPrimary: Color(0xFF0F172A),
    textSecondary: Color(0xFF475569),
    textMuted: Color(0xFF5B687A),
    accentSolid: Color(0xFF2563EB),
    accentHover: Color(0xFF1D4ED8),
    accentText: Color(0xFF1D4ED8),
    accentSoft: Color(0xFFDBEAFE),
    focusRing: Color(0xFF2563EB),
    successSolid: Color(0xFF15803D),
    successSoft: Color(0xFFDCFCE7),
    successText: Color(0xFF166534),
    warningSolid: Color(0xFFB45309),
    warningSoft: Color(0xFFFEF3C7),
    warningText: Color(0xFF92400E),
    dangerSolid: Color(0xFFDC2626),
    dangerSoft: Color(0xFFFEE2E2),
    dangerText: Color(0xFFB91C1C),
    offlineSolid: Color(0xFF64748B),
    imageOutline: Color(0x1A000000),
  );

  static const dark = RrColors(
    bgCanvas: Color(0xFF0B0E14),
    bgSurface: Color(0xFF141822),
    bgSubtle: Color(0xFF1B202E),
    bgHover: Color(0xFF242B3D),
    borderSubtle: Color(0xFF2A3142),
    borderControl: Color(0xFF64748B),
    textPrimary: Color(0xFFF8FAFC),
    textSecondary: Color(0xFFCBD5E1),
    textMuted: Color(0xFF94A3B8),
    accentSolid: Color(0xFF2563EB),
    accentHover: Color(0xFF3B82F6),
    accentText: Color(0xFF60A5FA),
    accentSoft: Color(0xFF172540),
    focusRing: Color(0xFF60A5FA),
    successSolid: Color(0xFF22C55E),
    successSoft: Color(0xFF0F291E),
    successText: Color(0xFF4ADE80),
    warningSolid: Color(0xFFF59E0B),
    warningSoft: Color(0xFF2D200A),
    warningText: Color(0xFFFBBF24),
    dangerSolid: Color(0xFFDC2626),
    dangerSoft: Color(0xFF311319),
    dangerText: Color(0xFFF87171),
    offlineSolid: Color(0xFF94A3B8),
    imageOutline: Color(0x1AFFFFFF),
  );

  static RrColors of(BuildContext context) {
    final ext = Theme.of(context).extension<RrColors>();
    if (ext != null) return ext;
    return Theme.of(context).brightness == Brightness.dark ? dark : light;
  }

  List<BoxShadow> cardElevation(BuildContext context) {
    if (Theme.of(context).brightness == Brightness.dark) {
      return const <BoxShadow>[];
    }
    return const <BoxShadow>[
      BoxShadow(
        color: Color(0x0F000000),
        blurRadius: 2,
        offset: Offset(0, 1),
      ),
      BoxShadow(
        color: Color(0x0A000000),
        blurRadius: 4,
        offset: Offset(0, 2),
      ),
    ];
  }

  @override
  ThemeExtension<RrColors> copyWith({
    Color? bgCanvas,
    Color? bgSurface,
    Color? bgSubtle,
    Color? bgHover,
    Color? borderSubtle,
    Color? borderControl,
    Color? textPrimary,
    Color? textSecondary,
    Color? textMuted,
    Color? accentSolid,
    Color? accentHover,
    Color? accentText,
    Color? accentSoft,
    Color? focusRing,
    Color? successSolid,
    Color? successSoft,
    Color? successText,
    Color? warningSolid,
    Color? warningSoft,
    Color? warningText,
    Color? dangerSolid,
    Color? dangerSoft,
    Color? dangerText,
    Color? offlineSolid,
    Color? imageOutline,
  }) {
    return RrColors(
      bgCanvas: bgCanvas ?? this.bgCanvas,
      bgSurface: bgSurface ?? this.bgSurface,
      bgSubtle: bgSubtle ?? this.bgSubtle,
      bgHover: bgHover ?? this.bgHover,
      borderSubtle: borderSubtle ?? this.borderSubtle,
      borderControl: borderControl ?? this.borderControl,
      textPrimary: textPrimary ?? this.textPrimary,
      textSecondary: textSecondary ?? this.textSecondary,
      textMuted: textMuted ?? this.textMuted,
      accentSolid: accentSolid ?? this.accentSolid,
      accentHover: accentHover ?? this.accentHover,
      accentText: accentText ?? this.accentText,
      accentSoft: accentSoft ?? this.accentSoft,
      focusRing: focusRing ?? this.focusRing,
      successSolid: successSolid ?? this.successSolid,
      successSoft: successSoft ?? this.successSoft,
      successText: successText ?? this.successText,
      warningSolid: warningSolid ?? this.warningSolid,
      warningSoft: warningSoft ?? this.warningSoft,
      warningText: warningText ?? this.warningText,
      dangerSolid: dangerSolid ?? this.dangerSolid,
      dangerSoft: dangerSoft ?? this.dangerSoft,
      dangerText: dangerText ?? this.dangerText,
      offlineSolid: offlineSolid ?? this.offlineSolid,
      imageOutline: imageOutline ?? this.imageOutline,
    );
  }

  @override
  ThemeExtension<RrColors> lerp(ThemeExtension<RrColors>? other, double t) {
    if (other is! RrColors) return this;
    return RrColors(
      bgCanvas: Color.lerp(bgCanvas, other.bgCanvas, t) ?? bgCanvas,
      bgSurface: Color.lerp(bgSurface, other.bgSurface, t) ?? bgSurface,
      bgSubtle: Color.lerp(bgSubtle, other.bgSubtle, t) ?? bgSubtle,
      bgHover: Color.lerp(bgHover, other.bgHover, t) ?? bgHover,
      borderSubtle: Color.lerp(borderSubtle, other.borderSubtle, t) ?? borderSubtle,
      borderControl: Color.lerp(borderControl, other.borderControl, t) ?? borderControl,
      textPrimary: Color.lerp(textPrimary, other.textPrimary, t) ?? textPrimary,
      textSecondary: Color.lerp(textSecondary, other.textSecondary, t) ?? textSecondary,
      textMuted: Color.lerp(textMuted, other.textMuted, t) ?? textMuted,
      accentSolid: Color.lerp(accentSolid, other.accentSolid, t) ?? accentSolid,
      accentHover: Color.lerp(accentHover, other.accentHover, t) ?? accentHover,
      accentText: Color.lerp(accentText, other.accentText, t) ?? accentText,
      accentSoft: Color.lerp(accentSoft, other.accentSoft, t) ?? accentSoft,
      focusRing: Color.lerp(focusRing, other.focusRing, t) ?? focusRing,
      successSolid: Color.lerp(successSolid, other.successSolid, t) ?? successSolid,
      successSoft: Color.lerp(successSoft, other.successSoft, t) ?? successSoft,
      successText: Color.lerp(successText, other.successText, t) ?? successText,
      warningSolid: Color.lerp(warningSolid, other.warningSolid, t) ?? warningSolid,
      warningSoft: Color.lerp(warningSoft, other.warningSoft, t) ?? warningSoft,
      warningText: Color.lerp(warningText, other.warningText, t) ?? warningText,
      dangerSolid: Color.lerp(dangerSolid, other.dangerSolid, t) ?? dangerSolid,
      dangerSoft: Color.lerp(dangerSoft, other.dangerSoft, t) ?? dangerSoft,
      dangerText: Color.lerp(dangerText, other.dangerText, t) ?? dangerText,
      offlineSolid: Color.lerp(offlineSolid, other.offlineSolid, t) ?? offlineSolid,
      imageOutline: Color.lerp(imageOutline, other.imageOutline, t) ?? imageOutline,
    );
  }
}

/// Strict role-based typography & monospace numeric helpers for RRRemote.
class RrText {
  RrText._();

  static const List<String> monoFallback = <String>[
    'SF Mono',
    'JetBrains Mono',
    'Menlo',
    'Consolas',
    'monospace',
  ];

  static const List<FontFeature> numericFeatures = <FontFeature>[
    FontFeature.tabularFigures(),
    FontFeature.slashedZero(),
  ];

  static TextStyle mono({
    required double size,
    FontWeight weight = FontWeight.w600,
    Color? color,
    double height = 1.25,
    double letterSpacing = 0.0,
  }) {
    return TextStyle(
      fontFamily: 'SF Mono',
      fontFamilyFallback: monoFallback,
      fontSize: size,
      fontWeight: weight,
      height: height,
      letterSpacing: letterSpacing,
      color: color,
      fontFeatures: numericFeatures,
    );
  }

  static TextStyle title(Color color) => TextStyle(
        fontSize: 16,
        fontWeight: FontWeight.w600,
        height: 1.3,
        color: color,
      );

  static TextStyle label(Color color, {FontWeight weight = FontWeight.w500}) =>
      TextStyle(
        fontSize: 14,
        fontWeight: weight,
        height: 1.35,
        color: color,
      );

  static TextStyle body(Color color) => TextStyle(
        fontSize: 14,
        fontWeight: FontWeight.w400,
        height: 1.45,
        color: color,
      );

  static TextStyle caption(Color color, {FontWeight weight = FontWeight.w500}) =>
      TextStyle(
        fontSize: 12,
        fontWeight: weight,
        height: 1.4,
        color: color,
      );
}""",
        "Fix ColorThemeExtension.lerp bug and add RrColors + RrText tokens",
    )

    # 3. Upgrade MyTheme brand colors & neutral primitives (all AA-verified)
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
        """  static const Color grayBg = Color(0xFFF8FAFC);
  static const Color accent = Color(0xFF2563EB);
  static const Color accent50 = Color(0x802563EB);
  static const Color accent80 = Color(0xCC2563EB);
  static const Color canvasColor = Color(0xFF0B0E14);
  static const Color border = Color(0xFFCBD5E1);
  static const Color idColor = Color(0xFF1D4ED8);
  static const Color darkGray = Color(0xFF64748B);
  static const Color cmIdColor = Color(0xFF15803D);
  static const Color dark = Color(0xFF0F172A);
  static const Color button = Color(0xFF2563EB);
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

    # 5. Polish Light Theme (strictly preserve Flutter 3.44.9 anchors!)
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
        : null,
    textTheme: const TextTheme(
        titleLarge: TextStyle(fontSize: 19, color: Colors.black87),
        titleSmall: TextStyle(fontSize: 14, color: Colors.black87),
        bodySmall: TextStyle(fontSize: 12, color: Colors.black87, height: 1.25),
        bodyMedium:
            TextStyle(fontSize: 14, color: Colors.black87, height: 1.25),
        labelLarge: TextStyle(fontSize: 16.0, color: MyTheme.accent80)),
    cardColor: grayBg,
    hintColor: Color(0xFFAAAAAA),""",
        """    hoverColor: Color(0xFFE2E8F0),
    scaffoldBackgroundColor: Color(0xFFFFFFFF),
    dialogBackgroundColor: Color(0xFFFFFFFF),
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
          color: Color(0xFFCBD5E1),
        ),
      ),
    ),
    scrollbarTheme: scrollbarTheme,
    inputDecorationTheme: isDesktop
        ? InputDecorationTheme(
            fillColor: Color(0xFFFFFFFF),
            filled: true,
            isDense: true,
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(8),
              borderSide: BorderSide(color: Color(0xFF7C8BA1), width: 1),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(8),
              borderSide: BorderSide(color: Color(0xFF7C8BA1), width: 1),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(8),
              borderSide: BorderSide(color: Color(0xFF2563EB), width: 2),
            ),
          )
        : null,
    textTheme: const TextTheme(
        titleLarge: TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.w600,
            color: Color(0xFF0F172A),
            height: 1.3),
        titleSmall: TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w600,
            color: Color(0xFF0F172A),
            height: 1.35),
        bodySmall: TextStyle(
            fontSize: 12, color: Color(0xFF475569), height: 1.4),
        bodyMedium: TextStyle(
            fontSize: 14, color: Color(0xFF0F172A), height: 1.45),
        labelLarge: TextStyle(
            fontSize: 14.0,
            fontWeight: FontWeight.w600,
            color: Color(0xFF1D4ED8))),
    cardColor: Color(0xFFFFFFFF),
    hintColor: Color(0xFF5B687A),""",
        "LightTheme surfaces, WCAG 1.4.11 inputs, and type scale",
    )

    txt = replace_exact(
        txt,
        """    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: MyTheme.accent,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8.0),
        ),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        backgroundColor: grayBg,
        foregroundColor: Colors.black87,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8.0),
        ),
      ),
    ),""",
        """    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: Color(0xFF2563EB),
        foregroundColor: Color(0xFFFFFFFF),
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8.0),
        ),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        backgroundColor: Color(0xFFFFFFFF),
        foregroundColor: Color(0xFF0F172A),
        side: BorderSide(color: Color(0xFF7C8BA1), width: 1.0),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8.0),
        ),
      ),
    ),""",
        "LightTheme ElevatedButton & OutlinedButton WCAG AA styles",
    )

    txt = replace_exact(
        txt,
        """    colorScheme: ColorScheme.light(
        primary: Colors.blue, secondary: accent, background: grayBg),
    popupMenuTheme: PopupMenuThemeData(
        color: Colors.white,
        shape: RoundedRectangleBorder(
          side: BorderSide(
              color: (isDesktop || isWebDesktop)
                  ? Color(0xFFECECEC)
                  : Colors.transparent),
          borderRadius: BorderRadius.all(Radius.circular(8.0)),
        )),
  ).copyWith(
    extensions: <ThemeExtension<dynamic>>[
      ColorThemeExtension.light,
      TabbarTheme.light,
    ],
  );""",
        """    colorScheme: ColorScheme.light(
        primary: accent,
        onPrimary: Color(0xFFFFFFFF),
        secondary: accent,
        background: grayBg),
    popupMenuTheme: PopupMenuThemeData(
        color: Color(0xFFFFFFFF),
        shape: RoundedRectangleBorder(
          side: BorderSide(
              color: (isDesktop || isWebDesktop)
                  ? Color(0xFFCBD5E1)
                  : Colors.transparent),
          borderRadius: BorderRadius.all(Radius.circular(10.0)),
        )),
  ).copyWith(
    extensions: <ThemeExtension<dynamic>>[
      ColorThemeExtension.light,
      TabbarTheme.light,
      RrColors.light,
    ],
  );""",
        "LightTheme ColorScheme, popupMenu, and RrColors extension",
    )

    # 6. Polish Dark Theme (Obsidian Slate surfaces; preserve Flutter 3.44.9 anchors!)
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
        : null,
    textTheme: const TextTheme(
      titleLarge: TextStyle(fontSize: 19),
      titleSmall: TextStyle(fontSize: 14),
      bodySmall: TextStyle(fontSize: 12, height: 1.25),
      bodyMedium: TextStyle(fontSize: 14, height: 1.25),
      labelLarge: TextStyle(
        fontSize: 16.0,
        fontWeight: FontWeight.bold,
        color: accent80,
      ),
    ),
    cardColor: Color(0xFF24252B),""",
        """    hoverColor: Color(0xFF242B3D),
    scaffoldBackgroundColor: Color(0xFF0B0E14),
    dialogBackgroundColor: Color(0xFF141822),
    appBarTheme: AppBarTheme(
      elevation: 0,
      backgroundColor: Color(0xFF141822),
      shadowColor: Colors.transparent,
    ),
    dialogTheme: DialogTheme(
      elevation: 10,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14.0),
        side: BorderSide(
          width: 1,
          color: Color(0xFF2A3142),
        ),
      ),
    ),
    scrollbarTheme: scrollbarThemeDark,
    inputDecorationTheme: (isDesktop || isWebDesktop)
        ? InputDecorationTheme(
            fillColor: Color(0xFF141822),
            filled: true,
            isDense: true,
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(8),
              borderSide: BorderSide(color: Color(0xFF64748B), width: 1),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(8),
              borderSide: BorderSide(color: Color(0xFF64748B), width: 1),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(8),
              borderSide: BorderSide(color: Color(0xFF60A5FA), width: 2),
            ),
          )
        : null,
    textTheme: const TextTheme(
      titleLarge: TextStyle(
          fontSize: 18,
          fontWeight: FontWeight.w600,
          color: Color(0xFFF8FAFC),
          height: 1.3),
      titleSmall: TextStyle(
          fontSize: 14,
          fontWeight: FontWeight.w600,
          color: Color(0xFFF8FAFC),
          height: 1.35),
      bodySmall: TextStyle(
          fontSize: 12, color: Color(0xFFCBD5E1), height: 1.4),
      bodyMedium: TextStyle(
          fontSize: 14, color: Color(0xFFF8FAFC), height: 1.45),
      labelLarge: TextStyle(
        fontSize: 14.0,
        fontWeight: FontWeight.w600,
        color: Color(0xFF60A5FA),
      ),
    ),
    cardColor: Color(0xFF141822),
    hintColor: Color(0xFF94A3B8),""",
        "DarkTheme Obsidian Slate palette, inputs, and type scale",
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
        backgroundColor: Color(0xFF141822),
        side: BorderSide(color: Color(0xFF64748B), width: 1.0),
        disabledForegroundColor: Color(0xFF94A3B8),
        foregroundColor: Color(0xFFF8FAFC),
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
    )),
  ).copyWith(
    extensions: <ThemeExtension<dynamic>>[
      ColorThemeExtension.dark,
      TabbarTheme.dark,
    ],
  );""",
        """    menuBarTheme: MenuBarThemeData(
        style: MenuStyle(
            backgroundColor: MaterialStatePropertyAll(Color(0xFF141822)))),
    colorScheme: ColorScheme.dark(
      primary: accent,
      onPrimary: Color(0xFFFFFFFF),
      secondary: Color(0xFF60A5FA),
      background: Color(0xFF141822),
    ),
    popupMenuTheme: PopupMenuThemeData(
        color: Color(0xFF1B202E),
        shape: RoundedRectangleBorder(
      side: BorderSide(color: Color(0xFF2A3142)),
      borderRadius: BorderRadius.all(Radius.circular(10.0)),
    )),
  ).copyWith(
    extensions: <ThemeExtension<dynamic>>[
      ColorThemeExtension.dark,
      TabbarTheme.dark,
      RrColors.dark,
    ],
  );""",
        "DarkTheme menuBar, ColorScheme, popupMenu & RrColors extension",
    )

    # 7. Curated industrial slate/indigo/cobalt device card palette (all >= 9.1:1 with white text)
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
    0x1E293B, // Slate 800 (14.6:1 with white)
    0x1E3A5F, // Steel Blue (11.5:1 with white)
    0x1D3557, // Deep Cobalt (12.4:1 with white)
    0x1E3A8A, // Indigo 900 (10.4:1 with white)
    0x164E63, // Deep Cyan (9.1:1 with white)
    0x134E4A, // Deep Teal (9.5:1 with white)
    0x312E81, // Deep Violet (11.4:1 with white)
    0x27272A, // Zinc 800 (14.9:1 with white)
  ];
  var hash = 5381;
  for (var i = 0; i < str.length; i += 1) {
    hash = ((hash << 5) + hash) + str.codeUnitAt(i);
  }
  final rgb = palette[hash.abs() % palette.length];
  final effectiveAlpha = alpha is int ? (alpha < 0xE6 ? 0xF2 : alpha) : 0xFF;
  return Color((rgb & 0xFFFFFF) | ((effectiveAlpha & 0xFF) << 24));
}""",
        "Curated industrial str2color device card palette",
    )

    # 8. Remove commercial 'Powered by' watermark on custom personal client
    txt = replace_exact(
        txt,
        """Widget loadPowered(BuildContext context) {
  if (bind.mainGetBuildinOption(key: "hide-powered-by-me") == 'Y') {
    return SizedBox.shrink();
  }""",
        """Widget loadPowered(BuildContext context) {
  return const SizedBox.shrink();
  if (bind.mainGetBuildinOption(key: "hide-powered-by-me") == 'Y') {
    return SizedBox.shrink();
  }""",
        "Hide redundant Powered-by watermark on personal client",
    )

    # 9. Clean RRRemote brand header logo (no low-contrast 9px 'PERSONAL' badge)
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
    final c = RrColors.of(context);
    return Row(
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
            fontSize: 16,
            fontWeight: FontWeight.w700,
            height: 1.25,
            letterSpacing: -0.2,
            color: c.textPrimary,
          ),
        ),
      ],
    );
  }
}""",
        "Clean RRRemote header logo (no PERSONAL badge)",
    )

    repo_url = f"https://github.com/{update_repo}"
    txt = txt.replace(
        "Uri.parse('https://rustdesk.com')", f"Uri.parse('{repo_url}')"
    )
    write_text(p, txt)
