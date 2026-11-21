#!/usr/bin/env python3
"""
Cross-platform client configurator for RRRemote (RustDesk-compatible config).
Writes custom rendezvous/relay/API server & public key into RRRemote2.toml
and display defaults into RRRemote_default.toml without storing any sensitive
values in git.

Examples:
  python3 scripts/configure-client.py --server 203.0.113.10 --key "<PUBKEY>" --api-server http://203.0.113.10:21114
"""

from __future__ import annotations

import argparse
import os
import platform
import re
import shutil
from pathlib import Path


def migrate_legacy_dir(legacy_dir: Path, new_dir: Path) -> None:
    """Copy legacy RustDesk config & peers into RRRemote config directory once (per-file)."""
    if not legacy_dir.exists():
        return
    new_dir.mkdir(parents=True, exist_ok=True)
    for src_name, dst_name in (
        ("RustDesk.toml", "RRRemote.toml"),
        ("RustDesk2.toml", "RRRemote2.toml"),
        ("RustDesk_local.toml", "RRRemote_local.toml"),
        ("RustDesk_default.toml", "RRRemote_default.toml"),
        ("peers.toml", "peers.toml"),
    ):
        src = legacy_dir / src_name
        dst = new_dir / dst_name
        if src.exists() and not dst.exists():
            shutil.copy2(src, dst)
            print(f"[rrremote] Migrated {src} -> {dst}")
    src_peers = legacy_dir / "peers"
    dst_peers = new_dir / "peers"
    if src_peers.is_dir():
        dst_peers.mkdir(parents=True, exist_ok=True)
        for p in src_peers.iterdir():
            if p.is_file() and not (dst_peers / p.name).exists():
                shutil.copy2(p, dst_peers / p.name)


def candidate_config_paths() -> list[Path]:
    system = platform.system()
    home = Path.home()
    paths: list[Path] = []

    if system == "Windows":
        appdata = os.environ.get("APPDATA")
        if appdata:
            new_dir = Path(appdata) / "RRRemote" / "config"
            migrate_legacy_dir(Path(appdata) / "RustDesk" / "config", new_dir)
            paths.append(new_dir / "RRRemote2.toml")
        for legacy_dir, new_dir in (
            (
                Path(r"C:\Windows\System32\config\systemprofile\AppData\Roaming\RustDesk\config"),
                Path(r"C:\Windows\System32\config\systemprofile\AppData\Roaming\RRRemote\config"),
            ),
            (
                Path(r"C:\Windows\ServiceProfiles\LocalService\AppData\Roaming\RustDesk\config"),
                Path(r"C:\Windows\ServiceProfiles\LocalService\AppData\Roaming\RRRemote\config"),
            ),
        ):
            if new_dir.parent.exists() or legacy_dir.parent.exists():
                try:
                    migrate_legacy_dir(legacy_dir, new_dir)
                except PermissionError:
                    pass
                paths.append(new_dir / "RRRemote2.toml")
    elif system == "Darwin":
        legacy_dir = home / "Library" / "Preferences" / "com.carriez.RustDesk"
        new_dir = home / "Library" / "Preferences" / "com.carriez.RRRemote"
        migrate_legacy_dir(legacy_dir, new_dir)
        paths.append(new_dir / "RRRemote2.toml")
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            # Also sync the invoking user's prefs when run via sudo
            sudo_user = os.environ.get("SUDO_USER", "").strip()
            if sudo_user and sudo_user != "root":
                import pwd

                try:
                    user_home = Path(pwd.getpwnam(sudo_user).pw_dir)
                    u_legacy = user_home / "Library" / "Preferences" / "com.carriez.RustDesk"
                    u_new = user_home / "Library" / "Preferences" / "com.carriez.RRRemote"
                    migrate_legacy_dir(u_legacy, u_new)
                    u_path = u_new / "RRRemote2.toml"
                    if u_path not in paths:
                        paths.append(u_path)
                except KeyError:
                    pass
            # Sync root LaunchDaemon config (/var/root/Library/Preferences/com.carriez.RRRemote)
            root_legacy = Path("/var/root/Library/Preferences/com.carriez.RustDesk")
            root_new = Path("/var/root/Library/Preferences/com.carriez.RRRemote")
            migrate_legacy_dir(root_legacy, root_new)
            root_path = root_new / "RRRemote2.toml"
            if root_path not in paths:
                paths.append(root_path)
    else:
        xdg = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config"))
        migrate_legacy_dir(xdg / "rustdesk", xdg / "rrremote")
        paths.append(xdg / "rrremote" / "RRRemote2.toml")
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            migrate_legacy_dir(Path("/root/.config/rustdesk"), Path("/root/.config/rrremote"))
            paths.append(Path("/root/.config/rrremote/RRRemote2.toml"))

    return paths


def format_toml_string(value: str) -> str:
    """Format a valid TOML string literal (preferring single-quoted literals when safe)."""
    if "'" not in value and "\n" not in value and "\r" not in value:
        return f"'{value}'"
    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\r", "\\r")
        .replace("\n", "\\n")
        .replace("\t", "\\t")
    )
    return f'"{escaped}"'


def has_toml_option(content: str, key: str) -> bool:
    if "[options]" not in content:
        return False
    parts = re.split(r"(^\[[^\]]+\]\s*$)", content, flags=re.MULTILINE)
    in_options = False
    pat = re.compile(rf"^{re.escape(key)}\s*=", flags=re.MULTILINE)
    for chunk in parts:
        if re.match(r"^\[[^\]]+\]\s*$", chunk):
            in_options = chunk.strip() == "[options]"
        elif in_options and pat.search(chunk):
            return True
    return False


def remove_toml_option(content: str, key: str) -> str:
    if "[options]" not in content:
        return content
    parts = re.split(r"(^\[[^\]]+\]\s*$)", content, flags=re.MULTILINE)
    out: list[str] = []
    in_options = False
    pat = re.compile(rf"^{re.escape(key)}\s*=.*\r?\n?", flags=re.MULTILINE)
    for chunk in parts:
        if re.match(r"^\[[^\]]+\]\s*$", chunk):
            in_options = chunk.strip() == "[options]"
            out.append(chunk)
        elif in_options:
            out.append(pat.sub("", chunk))
        else:
            out.append(chunk)
    return "".join(out)


def upsert_toml_option(content: str, key: str, value: str) -> str:
    line_val = f"{key} = {format_toml_string(value)}"

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
                chunk = pat.sub(lambda _m: line_val, chunk, count=1)
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
    line_val = f"{key} = {format_toml_string(value)}"
    # Only search before first [section]
    first_sec = re.search(r"^\[[^\]]+\]", content, flags=re.MULTILINE)
    head = content[: first_sec.start()] if first_sec else content
    tail = content[first_sec.start() :] if first_sec else ""
    pat = re.compile(rf"^{re.escape(key)}\s*=.*$", flags=re.MULTILINE)
    if pat.search(head):
        head = pat.sub(lambda _m: line_val, head, count=1)
    else:
        head = f"{line_val}\n" + head
    return head + tail


def _has_port(addr: str) -> bool:
    if addr.startswith("["):
        return "]:" in addr
    return addr.count(":") == 1


def _derive_relay_from_server(server: str) -> str:
    if _has_port(server):
        host, port_s = server.rsplit(":", 1)
        if port_s.isdigit():
            return f"{host}:{int(port_s) + 1}"
    return server


def update_display_defaults(config2_path: Path) -> None:
    """Write display defaults (UserDefaultConfig) into sibling *_default.toml."""
    if not config2_path.name.endswith("2.toml"):
        return
    default_path = config2_path.with_name(config2_path.name[: -len("2.toml")] + "_default.toml")
    default_path.parent.mkdir(parents=True, exist_ok=True)
    content = default_path.read_text(encoding="utf-8") if default_path.exists() else ""
    for k, v in (
        ("view_style", "adaptive"),
        ("show_quality_monitor", "Y"),
    ):
        content = upsert_toml_option(content, k, v)
    default_path.write_text(content, encoding="utf-8", newline="\n")
    print(f"[rrremote] Updated display defaults: {default_path}")


def update_file(path: Path, server: str, relay: str, key: str, api_server: str, direct_ip: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = path.read_text(encoding="utf-8") if path.exists() else ""

    rendezvous_addr = server if _has_port(server) else f"{server}:21116"
    relay_addr = relay or _derive_relay_from_server(server)

    content = upsert_top_level(content, "rendezvous_server", rendezvous_addr)
    content = upsert_toml_option(content, "custom-rendezvous-server", server)
    content = upsert_toml_option(content, "relay-server", relay_addr)
    if key:
        content = upsert_toml_option(content, "key", key)
    if api_server:
        content = upsert_toml_option(content, "api-server", api_server)
    else:
        content = upsert_toml_option(content, "api-server", "")
    if direct_ip:
        content = upsert_toml_option(content, "direct-server", "Y")
    content = upsert_toml_option(content, "stop-service", "")
    content = upsert_toml_option(content, "av1-test", "N")
    # On macOS, default enable-hwcodec to 'N' only if unset so fresh installs avoid
    # VideoToolbox RAM encode -1 failures without clobbering an explicit user choice
    # (RRRemote's build also includes a frame-1 hardware encoder fallback to VP9/AV1).
    if platform.system() == "Darwin" and not has_toml_option(content, "enable-hwcodec"):
        content = upsert_toml_option(content, "enable-hwcodec", "N")
    # Clean up legacy misplaced display keys in RRRemote2.toml (they belong in RRRemote_default.toml)
    content = remove_toml_option(content, "view-style")
    content = remove_toml_option(content, "show-quality-monitor")
    # Personal full-access mode: enable all host/session capabilities by default
    for k, v in (
        ("approve-mode", "password"),
        ("verification-method", "use-both-passwords"),
        ("enable-keyboard", "Y"),
        ("enable-clipboard", "Y"),
        ("enable-audio", "Y"),
        ("enable-file-transfer", "Y"),
        ("enable-tunnel", "Y"),
        ("enable-remote-restart", "Y"),
        ("enable-record-session", "Y"),
        ("enable-terminal", "Y"),
        ("allow-remote-config-modification", "Y"),
    ):
        content = upsert_toml_option(content, k, v)

    path.write_text(content, encoding="utf-8", newline="\n")
    print(f"[rrremote] Updated config: {path}")
    update_display_defaults(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Configure RRRemote client self-hosted server settings")
    parser.add_argument("--server", required=True, help="Rendezvous/ID server host or IP")
    parser.add_argument("--relay", default="", help="Relay server host or IP (defaults to --server)")
    parser.add_argument("--key", required=True, help="Ed25519 public key from server id_ed25519.pub")
    parser.add_argument("--api-server", default="", help="API server URL, e.g. http://<host>:21114")
    parser.add_argument("--direct-ip", action="store_true", default=True, help="Enable direct IP access for LAN/VPN speed")
    parser.add_argument("--config-path", default="", help="Explicit path to RRRemote2.toml")
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
