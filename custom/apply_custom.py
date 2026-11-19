#!/usr/bin/env python3
"""
Apply RRRemote customizations to a checked-out upstream RustDesk source tree.

1. Optional build-time server defaults (read ONLY from environment variables,
   never stored in this repository).
2. Zero-rate-limit built-in update checker using GitHub's `/releases/latest`
   HTTPS redirect (avoids anonymous api.github.com 403 rate limits) and
   supports `-rrN` custom release suffixes.
3. Display branding (RRRemote) + industrial-grade UI/UX polish via
   `apply_ui_polish.py`.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8", newline="\n")


def patch_hbb_common_config(root: Path, rendezvous: str, pub_key: str, api_server: str) -> None:
    config_rs = root / "libs" / "hbb_common" / "src" / "config.rs"
    if not config_rs.exists():
        raise FileNotFoundError(f"Expected {config_rs} (ensure git submodules are checked out)")

    content = read_text(config_rs)
    changed = False

    if rendezvous:
        new_content, count = re.subn(
            r'pub const RENDEZVOUS_SERVERS:\s*&\[&str\]\s*=\s*&\[[^\]]*\];',
            f'pub const RENDEZVOUS_SERVERS: &[&str] = &["{rendezvous}"];',
            content,
            count=1,
        )
        if count != 1:
            raise RuntimeError("Failed to patch RENDEZVOUS_SERVERS in libs/hbb_common/src/config.rs")
        content = new_content
        changed = True
        print("[rrremote] Injected default RENDEZVOUS_SERVERS from environment.")

    if pub_key:
        new_content, count = re.subn(
            r'pub const RS_PUB_KEY:\s*&str\s*=\s*"[^"]*";',
            f'pub const RS_PUB_KEY: &str = "{pub_key}";',
            content,
            count=1,
        )
        if count != 1:
            raise RuntimeError("Failed to patch RS_PUB_KEY in libs/hbb_common/src/config.rs")
        content = new_content
        changed = True
        print("[rrremote] Injected default RS_PUB_KEY from environment.")

    if api_server:
        pattern = r'pub const OPTION_API_SERVER:\s*&str\s*=\s*"api-server";'
        if re.search(pattern, content) and "RRREMOTE_DEFAULT_API_SERVER" not in content:
            replacement = (
                'pub const OPTION_API_SERVER: &str = "api-server";\n'
                f'pub const RRREMOTE_DEFAULT_API_SERVER: &str = "{api_server}";'
            )
            content = re.sub(pattern, replacement, content, count=1)
            changed = True
            print("[rrremote] Recorded default API server constant.")

    if changed:
        write_text(config_rs, content)


def patch_update_checker(root: Path, update_repo: str) -> None:
    """Redirect built-in update check to GitHub `/releases/latest` (zero API rate limit)."""
    if "/" not in update_repo:
        raise ValueError(f"Invalid UPDATE_REPO: {update_repo!r}, expected 'owner/repo'")
    owner, repo = update_repo.split("/", 1)

    common_rs = root / "src" / "common.rs"
    if not common_rs.exists():
        raise FileNotFoundError(f"Expected {common_rs}")

    content = read_text(common_rs)

    # 1. Allow update URLs from our custom GitHub repository in release_id_from_update_url
    old_match = (
        '        ["rustdesk", "rustdesk", "releases", "tag", release_id] => *release_id,\n'
        '        ["rustdesk", "rustdesk", "releases", "tag", release_id, ""] => *release_id,'
    )
    new_match = (
        f'        ["{owner}", "{repo}", "releases", "tag", release_id] => *release_id,\n'
        f'        ["{owner}", "{repo}", "releases", "tag", release_id, ""] => *release_id,\n'
        '        ["rustdesk", "rustdesk", "releases", "tag", release_id] => *release_id,\n'
        '        ["rustdesk", "rustdesk", "releases", "tag", release_id, ""] => *release_id,'
    )
    if old_match in content and f'["{owner}", "{repo}", "releases", "tag"' not in content:
        content = content.replace(old_match, new_match, 1)
        print(f"[rrremote] Updated release_id_from_update_url to accept {owner}/{repo}.")
    elif f'["{owner}", "{repo}", "releases", "tag"' in content:
        print(f"[rrremote] release_id_from_update_url already patched for {owner}/{repo}.")
    else:
        raise RuntimeError("release_id_from_update_url pattern not matched in src/common.rs")

    # 2. Strip optional -rrN suffix in display_version_from_release_id (e.g. v1.5.3-rr2 -> 1.5.3)
    old_strip = "let display_version = release_id.strip_prefix('v').unwrap_or(release_id);"
    new_strip = (
        "let display_version = release_id.strip_prefix('v').unwrap_or(release_id)\n"
        "        .split('-').next().unwrap_or(release_id);"
    )
    if old_strip in content and ".split('-').next()" not in content:
        content = content.replace(old_strip, new_strip, 1)
        print("[rrremote] Updated display_version_from_release_id to support -rrN suffixes.")

    # 3. Query https://github.com/<owner>/<repo>/releases/latest via HTTP redirect (no API 403 limit)
    latest_web_url = f"https://github.com/{owner}/{repo}/releases/latest"
    fn_marker = "pub async fn do_check_software_update() -> hbb_common::ResultType<()> {"
    if fn_marker in content and latest_web_url not in content:
        start = content.index(fn_marker)
        end_marker = "\n#[inline]\npub fn get_app_name()"
        end = content.index(end_marker, start)
        custom_fn = f'''pub async fn do_check_software_update() -> hbb_common::ResultType<()> {{
    let url = "{latest_web_url}";
    let proxy_conf = Config::get_socks();
    let tls_url = get_url_for_tls(url, &proxy_conf);
    let tls_type = get_cached_tls_type(tls_url);
    let is_tls_not_cached = tls_type.is_none();
    let tls_type = tls_type.unwrap_or(TlsType::Rustls);
    let client = create_http_client_async(tls_type, false);
    let resp_res: ResultType<_> = match client
        .get(url)
        .header("User-Agent", "RRRemote-Updater")
        .send()
        .await
    {{
        Ok(resp) => Ok((tls_type, resp)),
        Err(err) => {{
            if is_tls_not_cached && err.is_request() {{
                let tls_type = TlsType::NativeTls;
                let client = create_http_client_async(tls_type, false);
                match client
                    .get(url)
                    .header("User-Agent", "RRRemote-Updater")
                    .send()
                    .await
                {{
                    Ok(resp) => Ok((tls_type, resp)),
                    Err(err) => Err(err.into()),
                }}
            }} else {{
                Err(err.into())
            }}
        }}
    }};
    let result: ResultType<()> = match resp_res {{
        Ok((used_tls_type, response)) => {{
            upsert_tls_cache(tls_url, used_tls_type, false);
            let status = response.status();
            if !status.is_success() {{
                Err(anyhow!("RRRemote update check failed with HTTP status: {{status}}"))
            }} else {{
                let final_url = response.url().as_str().to_owned();
                let payload = serde_json::to_vec(&hbb_common::VersionCheckResponse {{
                    url: final_url,
                }})?;
                process_software_update_check_response(Bytes::from(payload))
            }}
        }}
        Err(err) => Err(err),
    }};
    if result.is_err() {{
        clear_software_update_url();
    }}
    result
}}
'''
        content = content[:start] + custom_fn + content[end:]
        print(f"[rrremote] Redirected built-in update checker to {latest_web_url} (zero API rate limit).")

    write_text(common_rs, content)


def patch_default_api_server_fallback(root: Path, api_server: str) -> None:
    if not api_server:
        return
    common_rs = root / "src" / "common.rs"
    content = read_text(common_rs)
    marker = 'pub fn get_api_server(custom: String) -> String {'
    if marker in content and "RRREMOTE_DEFAULT_API_SERVER" not in content:
        idx = content.index(marker)
        snippet = content[idx : idx + 1200]
        if 'return "".to_owned();' in snippet:
            patched_snippet = snippet.replace(
                'return "".to_owned();',
                'return hbb_common::config::RRREMOTE_DEFAULT_API_SERVER.to_owned();',
                1,
            )
            content = content[:idx] + patched_snippet + content[idx + 1200 :]
            write_text(common_rs, content)
            print("[rrremote] Wired default API server fallback in src/common.rs.")


def patch_display_branding(root: Path, display_name: str) -> None:
    if not display_name or display_name == "RustDesk":
        return

    flutter_main = root / "flutter" / "lib" / "main.dart"
    if flutter_main.exists():
        txt = read_text(flutter_main)
        updated = txt.replace("title: 'RustDesk'", f"title: '{display_name}'")
        updated = updated.replace('title: "RustDesk"', f'title: "{display_name}"')
        if updated != txt:
            write_text(flutter_main, updated)
            print(f"[rrremote] Updated Flutter app title to {display_name}.")

    win_main = root / "flutter" / "windows" / "runner" / "main.cpp"
    if win_main.exists():
        txt = read_text(win_main)
        updated = txt.replace('L"RustDesk"', f'L"{display_name}"')
        if updated != txt:
            write_text(win_main, updated)
            print(f"[rrremote] Updated Windows runner title to {display_name}.")


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    display_name = os.environ.get("APP_DISPLAY_NAME", "RRRemote").strip()
    update_repo = os.environ.get("UPDATE_REPO", "melotusme/RRRemote").strip()
    rendezvous = os.environ.get("RR_RENDEZVOUS_SERVER", "").strip()
    pub_key = os.environ.get("RR_PUB_KEY", "").strip()
    api_server = os.environ.get("RR_API_SERVER", "").strip()

    print(f"[rrremote] Applying customizations to {root}")
    print(f"[rrremote] Display name: {display_name}, Update repo: {update_repo}")
    print(
        "[rrremote] Build-time server preset:",
        "enabled" if (rendezvous or pub_key or api_server) else "disabled (configure in-app)",
    )

    patch_hbb_common_config(root, rendezvous, pub_key, api_server)
    patch_update_checker(root, update_repo)
    patch_default_api_server_fallback(root, api_server)
    patch_display_branding(root, display_name)

    ui_script = Path(__file__).resolve().parent / "apply_ui_polish.py"
    if ui_script.exists():
        env = os.environ.copy()
        env["UPDATE_REPO"] = update_repo
        subprocess.run([sys.executable, str(ui_script), str(root)], check=True, env=env)

    print("[rrremote] All customizations applied successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
