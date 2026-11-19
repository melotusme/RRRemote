#!/usr/bin/env python3
"""
Cross-platform client configurator for RRRemote (RustDesk-compatible config).
Writes custom rendezvous/relay/API server & public key into RustDesk2.toml
without storing any sensitive values in git.

Examples:
  python3 scripts/configure-client.py --server 203.0.113.10 --key "<PUBKEY>" --api-server http://203.0.113.10:21114
"""

from __future__ import annotations

import argparse
import os
import platform
import re
from pathlib import Path


def candidate_config_paths() -> list[Path]:
    system = platform.system()
    home = Path.home()
    paths: list[Path] = []

    if system == "Windows":
        appdata = os.environ.get("APPDATA")
        if appdata:
            paths.append(Path(appdata) / "RustDesk" / "config" / "RustDesk2.toml")
        # Windows Service profiles (LocalSystem is the default service account, plus LocalService)
        for svc_cfg in (
            Path(r"C:\Windows\System32\config\systemprofile\AppData\Roaming\RustDesk\config\RustDesk2.toml"),
            Path(r"C:\Windows\ServiceProfiles\LocalService\AppData\Roaming\RustDesk\config\RustDesk2.toml"),
        ):
            if svc_cfg.parent.exists() or svc_cfg.parent.parent.exists():
                paths.append(svc_cfg)
    elif system == "Darwin":
        paths.append(home / "Library" / "Preferences" / "com.carriez.RustDesk" / "RustDesk2.toml")
    else:
        xdg = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config"))
        paths.append(xdg / "rustdesk" / "RustDesk2.toml")
        root_cfg = Path("/root/.config/rustdesk/RustDesk2.toml")
        if os.geteuid() == 0:
            paths.append(root_cfg)

    return paths


def upsert_toml_option(content: str, key: str, value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("'", "\\'")
    line_val = f"{key} = '{escaped}'"

    if "[options]" not in content:
        if content and not content.endswith("\n"):
            content += "\n"
        return content + f"\n[options]\n{line_val}\n"

    # Operate inside the [options] section
    parts = re.split(r"(^\[[^\]]+\]\s*$)", content, flags=re.MULTILINE)
    out: list[str] = []
    in_options = False
    replaced = False

    for chunk in parts:
        if re.match(r"^\[[^\]]+\]\s*$", chunk):
            if in_options and not replaced:
                if out and not out[-1].endswith("\n"):
                    out[-1] += "\n"
                out.append(f"{line_val}\n")
                replaced = True
            in_options = chunk.strip() == "[options]"
            out.append(chunk)
        elif in_options:
            pat = re.compile(rf"^{re.escape(key)}\s*=.*$", flags=re.MULTILINE)
            if pat.search(chunk):
                chunk = pat.sub(line_val, chunk, count=1)
                replaced = True
            out.append(chunk)
        else:
            out.append(chunk)

    if in_options and not replaced:
        if out and not out[-1].endswith("\n"):
            out[-1] += "\n"
        out.append(f"{line_val}\n")

    return "".join(out)


def upsert_top_level(content: str, key: str, value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("'", "\\'")
    line_val = f"{key} = '{escaped}'"
    # Only search before first [section]
    first_sec = re.search(r"^\[[^\]]+\]", content, flags=re.MULTILINE)
    head = content[: first_sec.start()] if first_sec else content
    tail = content[first_sec.start() :] if first_sec else ""
    pat = re.compile(rf"^{re.escape(key)}\s*=.*$", flags=re.MULTILINE)
    if pat.search(head):
        head = pat.sub(line_val, head, count=1)
    else:
        head = f"{line_val}\n" + head
    return head + tail


def update_file(path: Path, server: str, relay: str, key: str, api_server: str, direct_ip: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = path.read_text(encoding="utf-8") if path.exists() else ""

    content = upsert_top_level(content, "rendezvous_server", f"{server}:21116")
    content = upsert_toml_option(content, "custom-rendezvous-server", server)
    content = upsert_toml_option(content, "relay-server", relay or server)
    if key:
        content = upsert_toml_option(content, "key", key)
    if api_server:
        content = upsert_toml_option(content, "api-server", api_server)
    if direct_ip:
        content = upsert_toml_option(content, "direct-server", "Y")
    content = upsert_toml_option(content, "stop-service", "")
    content = upsert_toml_option(content, "av1-test", "N")
    # Optimal controller/host ergonomics out of the box
    content = upsert_toml_option(content, "view-style", "adaptive")
    content = upsert_toml_option(content, "show-quality-monitor", "Y")
    content = upsert_toml_option(content, "enable-audio", "Y")
    content = upsert_toml_option(content, "enable-clipboard", "Y")
    content = upsert_toml_option(content, "enable-file-transfer", "Y")

    path.write_text(content, encoding="utf-8", newline="\n")
    print(f"[rrremote] Updated config: {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Configure RRRemote client self-hosted server settings")
    parser.add_argument("--server", required=True, help="Rendezvous/ID server host or IP")
    parser.add_argument("--relay", default="", help="Relay server host or IP (defaults to --server)")
    parser.add_argument("--key", required=True, help="Ed25519 public key from server id_ed25519.pub")
    parser.add_argument("--api-server", default="", help="API server URL, e.g. http://<host>:21114")
    parser.add_argument("--direct-ip", action="store_true", default=True, help="Enable direct IP access for LAN/VPN speed")
    parser.add_argument("--config-path", default="", help="Explicit path to RustDesk2.toml")
    args = parser.parse_args()

    targets = [Path(args.config_path)] if args.config_path else candidate_config_paths()
    for p in targets:
        try:
            update_file(p, args.server.strip(), args.relay.strip(), args.key.strip(), args.api_server.strip(), args.direct_ip)
        except PermissionError:
            print(f"[rrremote] Skipped (permission denied): {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
