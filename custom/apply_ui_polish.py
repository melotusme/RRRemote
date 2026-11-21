#!/usr/bin/env python3
"""
Apply RRRemote personal-edition UI & UX refactor to upstream RustDesk 1.5.3
Flutter sources across Desktop and Mobile.

Modular implementation under `custom/ui_patches/`:
- `tokens.py`: Verified WCAG 2.2 AA `RrColors` (Light/Dark) + `RrText` type scale &
  monospace tabular-nums/slashed-zero helpers + clean logo (Flutter 3.24.5 & 3.44.9 safe).
- `desktop_home.py`: Responsive 240px/<720px sidebar, `CallbackShortcuts` (Cmd/Ctrl+K,
  Cmd/Ctrl+1-3, Cmd/Ctrl+,), accessible This Device ID card, unified amber macOS TCC
  checklist, red service/server recovery banner, dismissible manual Update banner.
- `desktop_connect.py`: Concentric (14/6/8) focus-ringed Quick-Connect & Device Jump bar,
  platform-aware autocomplete, optical Connect button, RenderBox-anchored mode menu,
  non-color-only status bar with inline recovery CTA.
- `desktop_peers.py`: Favorites-first pill tabs with outline/filled icons, Online-only
  filter, actionable empty & no-match states, focusable 1-click PeerCard (Enter/Space),
  non-color-only Online/Offline badge, RenderBox-anchored overflow menus.
- `desktop_session.py`: Concentric (10/4/6) RemoteToolbar + live monospace P2P/Relay
  latency pill + refined QualityMonitor HUD.
- `desktop_settings.py`: Decluttered 5-tab personal Settings & clean About card.
- `mobile.py`: Mobile parity (>=16px mono inputs, 44x44px labeled touch targets, no clutter).

Zero hardcoded personal servers/keys/IPs. Idempotent and strictly verified.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from ui_patches.desktop_connect import patch_desktop_connection
from ui_patches.desktop_home import patch_desktop_home_page
from ui_patches.desktop_peers import patch_desktop_peers
from ui_patches.desktop_session import patch_desktop_session
from ui_patches.desktop_settings import patch_desktop_settings
from ui_patches.mobile import patch_mobile_ui
from ui_patches.tokens import patch_common_theme


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    update_repo = os.environ.get("UPDATE_REPO", "melotusme/RRRemote").strip()
    print(f"[rrremote-ui] Applying personal-edition UI refactor to {root}")
    patch_common_theme(root, update_repo)
    patch_desktop_home_page(root, update_repo)
    patch_desktop_connection(root)
    patch_desktop_peers(root)
    patch_desktop_session(root)
    patch_desktop_settings(root, update_repo)
    patch_mobile_ui(root, update_repo)
    print("[rrremote-ui] Personal-edition UI refactor complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
