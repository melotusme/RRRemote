#!/usr/bin/env python3
"""Generate rrremote-update.json with exact file sizes and SHA256 digests."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path


def main() -> int:
    assets_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/rr-assets")
    out_file = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("rrremote-update.json")

    tag = os.environ["TAG_NAME"]
    version = os.environ["VERSION"]
    repo = os.environ["REPO"]
    base_url = f"https://github.com/{repo}/releases/download/{tag}"

    rules = [
        ("windows", "x86_64", "exe", lambda n: n.endswith("-x86_64.exe")),
        ("windows", "x86_64", "msi", lambda n: n.endswith("-x86_64.msi")),
        ("macos", "aarch64", "dmg", lambda n: n.endswith("-aarch64.dmg")),
        ("macos", "x86_64", "dmg", lambda n: n.endswith("-x86_64.dmg")),
        ("linux", "x86_64", "pkg.tar.zst", lambda n: n.endswith("x86_64.pkg.tar.zst")),
        ("linux", "x86_64", "deb", lambda n: n.endswith("-x86_64.deb")),
        ("android", "aarch64", "apk", lambda n: n.endswith("-aarch64.apk")),
        ("ios", "aarch64", "ipa", lambda n: n.endswith(".ipa")),
    ]

    files = sorted(assets_dir.iterdir())
    artifacts = []
    for platform, arch, fmt, pred in rules:
        match = next((f for f in files if f.is_file() and pred(f.name)), None)
        if not match:
            continue
        h = hashlib.sha256()
        with match.open("rb") as fp:
            for chunk in iter(lambda: fp.read(1024 * 1024), b""):
                h.update(chunk)
        artifacts.append(
            {
                "platform": platform,
                "arch": arch,
                "format": fmt,
                "url": f"{base_url}/{match.name}",
                "file_name": match.name,
                "size": match.stat().st_size,
                "sha256": h.hexdigest(),
            }
        )

    manifest = {
        "schema_version": 1,
        "app": "rrremote",
        "version": version,
        "release_id": tag,
        "artifacts": artifacts,
    }
    out_file.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(out_file.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
