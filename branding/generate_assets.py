#!/usr/bin/env python3
"""
Generate original industrial-grade RRRemote brand icons & logos (SVG, PNG, ICO, ICNS, tray).
Uses 4x supersampling via Pillow for razor-sharp anti-aliased edges at every size.
"""

from __future__ import annotations

import struct
from pathlib import Path
from PIL import Image, ImageDraw

OUT_DIR = Path(__file__).resolve().parent


def write_svg() -> None:
    svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0F172A"/>
      <stop offset="48%" stop-color="#1D4ED8"/>
      <stop offset="100%" stop-color="#0EA5E9"/>
    </linearGradient>
    <linearGradient id="shine" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#FFFFFF" stop-opacity="0.28"/>
      <stop offset="50%" stop-color="#FFFFFF" stop-opacity="0.02"/>
      <stop offset="100%" stop-color="#000000" stop-opacity="0.18"/>
    </linearGradient>
    <linearGradient id="beam" x1="0%" y1="100%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#38BDF8"/>
      <stop offset="100%" stop-color="#F8FAFC"/>
    </linearGradient>
  </defs>
  <!-- Superellipse-style rounded background -->
  <rect x="44" y="44" width="936" height="936" rx="220" fill="url(#bg)"/>
  <rect x="52" y="52" width="920" height="920" rx="212" fill="none" stroke="url(#shine)" stroke-width="14"/>
  <!-- Back remote screen frame (top-right) -->
  <rect x="376" y="210" width="428" height="312" rx="56" fill="#FFFFFF" fill-opacity="0.16" stroke="#E0F2FE" stroke-width="34"/>
  <!-- Front local screen frame (bottom-left) -->
  <rect x="220" y="502" width="428" height="312" rx="56" fill="#0F172A" fill-opacity="0.34" stroke="#FFFFFF" stroke-width="38"/>
  <!-- P2P direct link beam & nodes -->
  <line x1="434" y1="658" x2="590" y2="366" stroke="url(#beam)" stroke-width="44" stroke-linecap="round"/>
  <circle cx="434" cy="658" r="56" fill="#FFFFFF"/>
  <circle cx="434" cy="658" r="24" fill="#2563EB"/>
  <circle cx="590" cy="366" r="56" fill="#38BDF8"/>
  <circle cx="590" cy="366" r="24" fill="#FFFFFF"/>
</svg>
"""
    (OUT_DIR / "icon.svg").write_text(svg, encoding="utf-8", newline="\n")
    print("[branding] Wrote icon.svg")


def render_app_icon(size: int = 1024) -> Image.Image:
    """Render high-precision RRRemote icon at 4x supersampling then downscale."""
    scale = 2 if size >= 512 else 4
    s = size * scale
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))

    # 1. Diagonal gradient background (#0F172A -> #1D4ED8 -> #0EA5E9)
    grad = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    px = grad.load()
    stops = [
        (0.0, (15, 23, 42)),
        (0.48, (29, 78, 216)),
        (1.0, (14, 165, 233)),
    ]
    denom = float(2 * (s - 1))
    for y in range(s):
        for x in range(s):
            t = (x + y) / denom
            if t <= 0.48:
                u = t / 0.48
                c0, c1 = stops[0][1], stops[1][1]
            else:
                u = (t - 0.48) / 0.52
                c0, c1 = stops[1][1], stops[2][1]
            r = int(c0[0] + (c1[0] - c0[0]) * u)
            g = int(c0[1] + (c1[1] - c0[1]) * u)
            b = int(c0[2] + (c1[2] - c0[2]) * u)
            px[x, y] = (r, g, b, 255)

    # Rounded square mask
    pad = int(s * (44 / 1024))
    radius = int(s * (220 / 1024))
    mask = Image.new("L", (s, s), 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.rounded_rectangle([pad, pad, s - pad, s - pad], radius=radius, fill=255)
    img.paste(grad, (0, 0), mask)

    # Subtle glossy inner rim
    rim = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    rdraw = ImageDraw.Draw(rim)
    rim_pad = int(s * (52 / 1024))
    rim_w = max(2, int(s * (14 / 1024)))
    rdraw.rounded_rectangle(
        [rim_pad, rim_pad, s - rim_pad, s - rim_pad],
        radius=int(s * (212 / 1024)),
        outline=(255, 255, 255, 58),
        width=rim_w,
    )
    img = Image.alpha_composite(img, rim)

    # Overlay layer for crisp alpha compositing
    ov = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(ov)

    def sc(v: float) -> int:
        return int(round(v * s / 1024.0))

    # Back remote screen frame (top-right)
    draw.rounded_rectangle(
        [sc(376), sc(210), sc(804), sc(522)],
        radius=sc(56),
        fill=(255, 255, 255, 42),
        outline=(224, 242, 254, 245),
        width=max(2, sc(34)),
    )

    # Front local screen frame (bottom-left)
    draw.rounded_rectangle(
        [sc(220), sc(502), sc(648), sc(814)],
        radius=sc(56),
        fill=(15, 23, 42, 92),
        outline=(255, 255, 255, 255),
        width=max(2, sc(38)),
    )

    # P2P high-speed link beam
    x1, y1 = sc(434), sc(658)
    x2, y2 = sc(590), sc(366)
    draw.line([(x1, y1), (x2, y2)], fill=(186, 230, 253, 255), width=max(2, sc(44)))

    # Bottom-left anchor node (local)
    r_out = sc(58)
    r_in = sc(24)
    draw.ellipse([x1 - r_out, y1 - r_out, x1 + r_out, y1 + r_out], fill=(255, 255, 255, 255))
    draw.ellipse([x1 - r_in, y1 - r_in, x1 + r_in, y1 + r_in], fill=(37, 99, 235, 255))

    # Top-right anchor node (remote)
    draw.ellipse([x2 - r_out, y2 - r_out, x2 + r_out, y2 + r_out], fill=(56, 189, 248, 255))
    draw.ellipse([x2 - r_in, y2 - r_in, x2 + r_in, y2 + r_in], fill=(255, 255, 255, 255))

    img = Image.alpha_composite(img, ov)
    return img.resize((size, size), Image.Resampling.LANCZOS)


def render_tray_icon(size: int, color: tuple[int, int, int, int]) -> Image.Image:
    s = size * 4
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    def sc(v: float) -> int:
        return int(round(v * s / 1024.0))

    draw.rounded_rectangle(
        [sc(360), sc(150), sc(890), sc(560)],
        radius=sc(76),
        outline=color,
        width=max(3, sc(64)),
    )
    draw.rounded_rectangle(
        [sc(134), sc(464), sc(664), sc(874)],
        radius=sc(76),
        outline=color,
        width=max(3, sc(68)),
    )
    draw.line([(sc(399), sc(669)), (sc(625), sc(355))], fill=color, width=max(3, sc(68)))
    for cx, cy in ((sc(399), sc(669)), (sc(625), sc(355))):
        r = sc(78)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
    return img.resize((size, size), Image.Resampling.LANCZOS)


def write_icns(base_img: Image.Image, dest: Path) -> None:
    """Write a valid modern macOS ICNS container with embedded PNG chunks."""
    # Standard macOS PNG-backed ICNS icon types
    types = [
        (b"icp4", 16),
        (b"icp5", 32),
        (b"icp6", 64),
        (b"ic07", 128),
        (b"ic08", 256),
        (b"ic09", 512),
        (b"ic10", 1024),
    ]
    from io import BytesIO

    chunks = []
    for ostype, sz in types:
        buf = BytesIO()
        resized = base_img if sz == base_img.width else base_img.resize((sz, sz), Image.Resampling.LANCZOS)
        resized.save(buf, format="PNG", optimize=True)
        png_bytes = buf.getvalue()
        chunks.append(ostype + struct.pack(">I", len(png_bytes) + 8) + png_bytes)

    body = b"".join(chunks)
    header = b"icns" + struct.pack(">I", len(body) + 8)
    dest.write_bytes(header + body)
    print(f"[branding] Wrote {dest.name} ({dest.stat().st_size} bytes)")


def main() -> int:
    write_svg()
    master = render_app_icon(1024)
    master.save(OUT_DIR / "icon-1024.png", optimize=True)
    master.resize((512, 512), Image.Resampling.LANCZOS).save(OUT_DIR / "icon-512.png", optimize=True)
    master.resize((256, 256), Image.Resampling.LANCZOS).save(OUT_DIR / "icon-256.png", optimize=True)
    master.save(
        OUT_DIR / "icon.ico",
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    write_icns(master, OUT_DIR / "AppIcon.icns")
    render_tray_icon(44, (255, 255, 255, 255)).save(OUT_DIR / "tray-dark.png", optimize=True)
    render_tray_icon(44, (15, 23, 42, 255)).save(OUT_DIR / "tray-light.png", optimize=True)
    print("[branding] Generated full RRRemote icon suite successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
