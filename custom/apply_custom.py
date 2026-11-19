#!/usr/bin/env python3
"""
Apply RRRemote customizations to a checked-out upstream RustDesk source tree.

All sensitive values (rendezvous server, public key, API server) are read ONLY
from environment variables (e.g. GitHub Actions Secrets) at build time and are
never stored in this repository.
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
        # Optional default API server fallback when local option is empty.
        # Kept non-destructive so users can always override API server in Settings UI.
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
    """Redirect built-in update check to GitHub Releases of update_repo (owner/repo)."""
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
        print("[rrremote] Warning: release_id_from_update_url pattern not matched; skipping.")

    # 2. Patch do_check_software_update to query GitHub Releases latest API directly
    gh_api_url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
    fn_marker = "pub async fn do_check_software_update() -> hbb_common::ResultType<()> {"
    if fn_marker in content and gh_api_url not in content:
        start = content.index(fn_marker)
        # Find the next top-level function marker (#[inline] right after do_check_software_update)
        end_marker = "\n#[inline]\npub fn get_app_name()"
        end = content.index(end_marker, start)
        custom_fn = f'''pub async fn do_check_software_update() -> hbb_common::ResultType<()> {{
    let url = "{gh_api_url}";
    let proxy_conf = Config::get_socks();
    let tls_url = get_url_for_tls(url, &proxy_conf);
    let tls_type = get_cached_tls_type(tls_url);
    let is_tls_not_cached = tls_type.is_none();
    let tls_type = tls_type.unwrap_or(TlsType::Rustls);
    let client = create_http_client_async(tls_type, false);
    let resp_res: ResultType<_> = match client
        .get(url)
        .header("User-Agent", "RRRemote-Updater")
        .header("Accept", "application/vnd.github+json")
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
                    .header("Accept", "application/vnd.github+json")
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
                let body = response.bytes().await?;
                let json: serde_json::Value = serde_json::from_slice(&body)?;
                let html_url = json
                    .get("html_url")
                    .and_then(|v| v.as_str())
                    .unwrap_or_default()
                    .to_owned();
                if html_url.is_empty() {{
                    Err(anyhow!("GitHub release response missing html_url"))
                }} else {{
                    let payload = serde_json::to_vec(&hbb_common::VersionCheckResponse {{
                        url: html_url,
                    }})?;
                    process_software_update_check_response(Bytes::from(payload))
                }}
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
        print(f"[rrremote] Redirected built-in update checker to {gh_api_url}.")

    write_text(common_rs, content)


def patch_default_api_server_fallback(root: Path, api_server: str) -> None:
    """When user hasn't explicitly configured an API server, fall back to RR_API_SERVER."""
    if not api_server:
        return
    common_rs = root / "src" / "common.rs"
    content = read_text(common_rs)
    marker = 'pub fn get_api_server(custom: String) -> String {'
    if marker in content and "RRREMOTE_DEFAULT_API_SERVER" not in content:
        # Insert fallback right before returning empty string in get_api_server if present
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
    """Customize user-visible window title without breaking upstream packaging paths."""
    if not display_name or display_name == "RustDesk":
        return

    # Flutter desktop window title (macOS/Windows/Linux UI title)
    flutter_main = root / "flutter" / "lib" / "main.dart"
    if flutter_main.exists():
        txt = read_text(flutter_main)
        updated = txt.replace("title: 'RustDesk'", f"title: '{display_name}'")
        updated = updated.replace('title: "RustDesk"', f'title: "{display_name}"')
        if updated != txt:
            write_text(flutter_main, updated)
            print(f"[rrremote] Updated Flutter app title to {display_name}.")

    # Windows runner window title
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

    print("[rrremote] Customization complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
