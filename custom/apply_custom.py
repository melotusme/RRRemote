#!/usr/bin/env python3
"""
Apply RRRemote customizations to a checked-out upstream RustDesk source tree:
1. Disable account/login subsystem cleanly (`is_disable_account() -> true`) so no
   unwanted login/password screens appear (keeps Recent / Favorites / LAN Discovery).
2. Replace upstream RustDesk icons & logos across all platforms (Windows/macOS/
   Linux/Android/iOS/Tray) with the original RRRemote brand suite in `branding/`.
3. Zero-rate-limit built-in updater via GitHub `/releases/latest` redirect +
   `-rrN` revision comparison + SHA256-verified `rrremote-update.json` manifest
   so the app automatically downloads and installs updates upon launch.
4. Optional build-time server defaults via environment variables (never in git).
5. Industrial-grade UI & UX polish via `apply_ui_polish.py`.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8", newline="\n")


def patch_hbb_common_config(root: Path, display_name: str, rendezvous: str, pub_key: str, api_server: str) -> None:
    config_rs = root / "libs" / "hbb_common" / "src" / "config.rs"
    if not config_rs.exists():
        raise FileNotFoundError(f"Expected {config_rs} (ensure git submodules are checked out)")

    content = read_text(config_rs)
    changed = False

    # 0. Set native APP_NAME so config dirs, services, logs, tray, IPC, MSI, macOS & Linux
    #    packaging and i18n translations all natively identify as RRRemote.
    if display_name and display_name != "RustDesk":
        old_app_name = 'pub static ref APP_NAME: RwLock<String> = RwLock::new("RustDesk".to_owned());'
        new_app_name = f'pub static ref APP_NAME: RwLock<String> = RwLock::new("{display_name}".to_owned());'
        if old_app_name in content:
            content = content.replace(old_app_name, new_app_name, 1)
            changed = True
            print(f"[rrremote] Set hbb_common::config::APP_NAME = {display_name!r}.")
        elif new_app_name in content:
            print(f"[rrremote] hbb_common::config::APP_NAME already set to {display_name!r}.")
        else:
            raise RuntimeError("Failed to locate APP_NAME in libs/hbb_common/src/config.rs")

    # 1. Permanently disable account/login UI across all platforms (personal tool)
    old_disable_acc = (
        "pub fn is_disable_account() -> bool {\n"
        '    is_some_hard_opton("disable-account")\n'
        "}"
    )
    new_disable_acc = (
        "pub fn is_disable_account() -> bool {\n"
        "    true\n"
        "}"
    )
    if old_disable_acc in content:
        content = content.replace(old_disable_acc, new_disable_acc, 1)
        changed = True
        print("[rrremote] Disabled account/login subsystem globally (is_disable_account -> true).")
    elif new_disable_acc in content:
        print("[rrremote] is_disable_account already set to true.")
    else:
        raise RuntimeError("Failed to locate is_disable_account() in libs/hbb_common/src/config.rs")

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


def patch_update_checker(root: Path, update_repo: str, build_tag: str) -> None:
    """Redirect built-in update check to GitHub `/releases/latest` with -rrN revision support."""
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

    # 2. Support -rrN custom release suffixes in display_version_from_release_id
    old_strip = "let display_version = release_id.strip_prefix('v').unwrap_or(release_id);"
    new_strip = (
        "let display_version = release_id.strip_prefix('v').unwrap_or(release_id)\n"
        "        .split('-').next().unwrap_or(release_id);"
    )
    if old_strip in content and ".split('-').next()" not in content:
        content = content.replace(old_strip, new_strip, 1)
        print("[rrremote] Updated display_version_from_release_id to support -rrN suffixes.")

    # 3. Compare (base_version_number, rr_revision) against compile-time RRREMOTE_BUILD_TAG
    old_proc_marker = "fn process_software_update_check_response(bytes: Bytes) -> ResultType<()> {"
    if old_proc_marker in content and "RRREMOTE_BUILD_TAG" not in content:
        start = content.index(old_proc_marker)
        end = content.index("\n// No need to check", start)
        safe_tag = build_tag.replace('"', "")
        custom_proc = f'''const RRREMOTE_BUILD_TAG: &str = "{safe_tag}";

fn parse_rr_revision(tag: &str) -> u32 {{
    if let Some((_, suffix)) = tag.split_once("-rr") {{
        if let Ok(n) = suffix.parse::<u32>() {{
            return n;
        }}
    }}
    0
}}

fn process_software_update_check_response(bytes: Bytes) -> ResultType<()> {{
    let resp: hbb_common::VersionCheckResponse = serde_json::from_slice(&bytes)?;
    let response_url = resp.url;
    let release_id = release_id_from_update_url(&response_url)?;
    let latest_release_version = display_version_from_release_id(&release_id)?;

    let latest_base = get_version_number(&latest_release_version);
    let current_base = get_version_number(crate::VERSION);
    let latest_rev = parse_rr_revision(&release_id);
    let current_rev = parse_rr_revision(RRREMOTE_BUILD_TAG);
    let is_newer = (latest_base > current_base)
        || (latest_base == current_base && latest_rev > current_rev);

    if is_newer {{
        #[cfg(feature = "flutter")]
        {{
            let mut m = HashMap::new();
            m.insert("name", "check_software_update_finish");
            m.insert("url", &response_url);
            if let Ok(data) = serde_json::to_string(&m) {{
                let _ = crate::flutter::push_global_event(crate::flutter::APP_TYPE_MAIN, data);
            }}
        }}
        *SOFTWARE_UPDATE_URL.lock().unwrap() = response_url;
    }} else {{
        clear_software_update_url();
    }}
    Ok(())
}}
'''
        content = content[:start] + custom_proc + content[end:]
        print(f"[rrremote] Wired revision-aware update comparison (current tag: {safe_tag}).")

    # 4. Query https://github.com/<owner>/<repo>/releases/latest via HTTP redirect (zero API 403 limit)
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


def patch_updater_artifact_resolver(root: Path, update_repo: str) -> None:
    """Resolve platform installers from rrremote-update.json on GitHub Releases with SHA256."""
    artifact_rs = root / "src" / "updater" / "artifact.rs"
    if not artifact_rs.exists():
        raise FileNotFoundError(f"Expected {artifact_rs}")

    content = read_text(artifact_rs)
    if "rrremote-update.json" in content:
        print("[rrremote] src/updater/artifact.rs already patched for rrremote-update.json.")
        return

    old_fn = '''pub(super) fn verified_update_artifact_from_release_page_url(
    update_url: &str,
    query: &UpdateArtifactQuery<'_>,
) -> ResultType<VerifiedUpdateArtifact> {
    let release_id = release_id_from_update_url(update_url)?;
    let display_version = display_version_from_release_id(&release_id)?;
    let expected_artifact_url_prefix =
        format!("https://github.com/rustdesk/rustdesk/releases/download/{release_id}/");
    let metadata_url = format!("{expected_artifact_url_prefix}rustdesk-update.json");
    let signature_url = format!("{metadata_url}.sig");
    let metadata_bytes = fetch_update_sidecar_bytes(&metadata_url)?;
    let signature_bytes = fetch_update_sidecar_bytes(&signature_url)?;
    let requirements = UpdateMetadataRequirements {
        expected_version: display_version.as_str(),
        expected_release_id: release_id.as_str(),
        expected_artifact_url_prefix: expected_artifact_url_prefix.as_str(),
        artifact: *query,
    };
    crate::update_metadata::verify_update_metadata(&metadata_bytes, &signature_bytes, requirements)
}'''

    new_fn = f'''#[derive(serde_derive::Deserialize)]
struct RrManifest {{
    version: String,
    artifacts: Vec<RrManifestArtifact>,
}}

#[derive(serde_derive::Deserialize)]
struct RrManifestArtifact {{
    platform: String,
    arch: String,
    format: String,
    url: String,
    file_name: String,
    size: u64,
    sha256: String,
}}

pub(super) fn verified_update_artifact_from_release_page_url(
    update_url: &str,
    query: &UpdateArtifactQuery<'_>,
) -> ResultType<VerifiedUpdateArtifact> {{
    let release_id = release_id_from_update_url(update_url)?;
    let _display_version = display_version_from_release_id(&release_id)?;
    let expected_prefix =
        format!("https://github.com/{update_repo}/releases/download/{{release_id}}/");
    let manifest_url = format!("{{expected_prefix}}rrremote-update.json");
    let manifest_bytes = fetch_update_sidecar_bytes(&manifest_url)?;
    let manifest: RrManifest = serde_json::from_slice(&manifest_bytes)?;
    let Some(item) = manifest.artifacts.into_iter().find(|a| {{
        a.platform == query.platform && a.arch == query.arch && a.format == query.format
    }}) else {{
        bail!(
            "No RRRemote update artifact for {{}}/{{}}/{{}} in {{}}",
            query.platform,
            query.arch,
            query.format,
            release_id
        );
    }};
    if !item.url.starts_with(&expected_prefix) {{
        bail!("Unexpected RRRemote update artifact URL: {{}}", item.url);
    }}
    Ok(VerifiedUpdateArtifact {{
        version: manifest.version,
        url: item.url,
        #[cfg(target_os = "macos")]
        file_name: item.file_name,
        size: item.size,
        sha256: item.sha256,
    }})
}}'''

    if old_fn not in content:
        raise RuntimeError("Failed to match verified_update_artifact_from_release_page_url in src/updater/artifact.rs")

    content = content.replace(old_fn, new_fn, 1)
    # Silence unused import warning for UpdateMetadataRequirements
    content = content.replace(
        "update_metadata::{UpdateArtifactQuery, UpdateMetadataRequirements, VerifiedUpdateArtifact},",
        "update_metadata::{UpdateArtifactQuery, VerifiedUpdateArtifact},",
        1,
    )
    write_text(artifact_rs, content)
    print(f"[rrremote] Wired SHA256-verified in-app update manifest resolver for {update_repo}.")


def patch_default_api_server_fallback(root: Path, api_server: str) -> None:
    common_rs = root / "src" / "common.rs"
    content = read_text(common_rs)
    if api_server:
        marker = 'pub fn get_api_server(api: String, custom: String) -> String {'
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
        return

    # Account/login disabled and no explicit API server: avoid pointless :21114/:31114 HTTP timeouts
    old_api_fn = """pub fn get_api_server(api: String, custom: String) -> String {
    if Config::no_register_device() {
        return "".to_owned();
    }"""
    new_api_fn = """pub fn get_api_server(api: String, custom: String) -> String {
    if Config::no_register_device() || (api.is_empty() && config::is_disable_account()) {
        return "".to_owned();
    }"""
    if old_api_fn in content:
        content = content.replace(old_api_fn, new_api_fn, 1)
        write_text(common_rs, content)
        print("[rrremote] Disabled implicit API server fallback when account login is disabled.")


def apply_brand_icons(root: Path) -> None:
    """Replace upstream logos & icons across all platforms with RRRemote brand assets."""
    branding_dir = Path(__file__).resolve().parent.parent / "branding"
    if not branding_dir.exists():
        print("[rrremote] No branding/ directory found; skipping icon replacement.")
        return

    copy_map = [
        ("icon.svg", "flutter/assets/icon.svg"),
        ("icon.svg", "res/icon.svg"),
        ("icon.svg", "res/logo.svg"),
        ("icon.svg", "res/logo-header.svg"),
        ("icon.svg", "res/scalable.svg"),
        ("icon-256.png", "res/128x128@2x.png"),
        ("icon-512.png", "flutter/assets/icon.png"),
        ("icon-512.png", "res/icon.png"),
        ("icon-512.png", "res/mac-icon.png"),
        ("icon.ico", "res/icon.ico"),
        ("icon.ico", "res/tray-icon.ico"),
        ("icon.ico", "flutter/windows/runner/resources/app_icon.ico"),
        ("AppIcon.icns", "flutter/macos/Runner/AppIcon.icns"),
        ("tray-dark.png", "res/mac-tray-dark-x2.png"),
        ("tray-light.png", "res/mac-tray-light-x2.png"),
    ]
    copied = 0
    for src_name, dst_rel in copy_map:
        src = branding_dir / src_name
        dst = root / dst_rel
        if src.exists() and dst.parent.exists():
            shutil.copy2(src, dst)
            copied += 1
    print(f"[rrremote] Applied {copied} desktop/SVG/ICO/ICNS brand assets.")

    # Resize & replace Android mipmap and iOS AppIcon PNGs if Pillow is available
    master_png = branding_dir / "icon-1024.png"
    if master_png.exists():
        try:
            from PIL import Image

            master = Image.open(master_png).convert("RGBA")
            mobile_targets = []
            android_res = root / "flutter" / "android" / "app" / "src" / "main" / "res"
            if android_res.exists():
                for p in android_res.rglob("*.png"):
                    if p.name in ("ic_launcher.png", "ic_launcher_round.png", "ic_stat_logo.png"):
                        mobile_targets.append(p)
            ios_icons = root / "flutter" / "ios" / "Runner" / "Assets.xcassets" / "AppIcon.appiconset"
            if ios_icons.exists():
                for p in ios_icons.glob("*.png"):
                    mobile_targets.append(p)

            replaced_mobile = 0
            for target in mobile_targets:
                with Image.open(target) as orig:
                    sz = orig.size
                resized = master.resize(sz, Image.Resampling.LANCZOS)
                # iOS AppIcon must not contain transparency (composite over deep slate #0F172A)
                if "AppIcon.appiconset" in str(target):
                    bg = Image.new("RGB", sz, (15, 23, 42))
                    bg.paste(resized, (0, 0), resized)
                    bg.save(target, format="PNG", optimize=True)
                else:
                    resized.save(target, format="PNG", optimize=True)
                replaced_mobile += 1
            print(f"[rrremote] Replaced {replaced_mobile} Android/iOS app icon PNGs.")
        except ImportError:
            print("[rrremote] Pillow not installed on runner; skipping mobile PNG resizing.")


def patch_display_branding(root: Path, display_name: str) -> None:
    if not display_name or display_name == "RustDesk":
        return

    lower_name = display_name.lower()

    # 1. Flutter Dart window title
    flutter_main = root / "flutter" / "lib" / "main.dart"
    if flutter_main.exists():
        txt = read_text(flutter_main)
        updated = txt.replace("title: 'RustDesk'", f"title: '{display_name}'")
        updated = updated.replace('title: "RustDesk"', f'title: "{display_name}"')
        if updated != txt:
            write_text(flutter_main, updated)
            print(f"[rrremote] Updated Flutter app title to {display_name}.")

    # 2. Ensure ALL i18n strings replace "RustDesk" -> display_name (including powered_by_me)
    lang_rs = root / "src" / "lang.rs"
    if lang_rs.exists():
        txt = read_text(lang_rs)
        old_lang_guard = """            if s.contains("RustDesk")
                && !name.starts_with("upgrade_rustdesk_server_pro")
                && name != "powered_by_me"
            {"""
        new_lang_guard = """            if s.contains("RustDesk") {"""
        if old_lang_guard in txt:
            txt = txt.replace(old_lang_guard, new_lang_guard, 1)
            write_text(lang_rs, txt)
            print(f"[rrremote] Enabled 100% i18n RustDesk -> {display_name} substitution in src/lang.rs.")

    # 3. Windows binary name (RRRemote.exe), runner title & file version metadata
    win_cmake = root / "flutter" / "windows" / "CMakeLists.txt"
    if win_cmake.exists():
        txt = read_text(win_cmake)
        updated = txt.replace('set(BINARY_NAME "rustdesk")', f'set(BINARY_NAME "{display_name}")')
        if updated != txt:
            write_text(win_cmake, updated)
            print(f"[rrremote] Set Windows BINARY_NAME to {display_name}.exe.")

    win_main = root / "flutter" / "windows" / "runner" / "main.cpp"
    if win_main.exists():
        txt = read_text(win_main)
        updated = txt.replace('L"RustDesk"', f'L"{display_name}"')
        if updated != txt:
            write_text(win_main, updated)
            print(f"[rrremote] Updated Windows runner title to {display_name}.")

    win_rc = root / "flutter" / "windows" / "runner" / "Runner.rc"
    if win_rc.exists():
        txt = read_text(win_rc)
        updated = (
            txt.replace('VALUE "CompanyName", "Purslane Tech Pte. Ltd."', f'VALUE "CompanyName", "{display_name}"')
            .replace('VALUE "FileDescription", "RustDesk Remote Desktop"', f'VALUE "FileDescription", "{display_name} Remote Desktop"')
            .replace('VALUE "InternalName", "rustdesk"', f'VALUE "InternalName", "{display_name}"')
            .replace('VALUE "OriginalFilename", "rustdesk.exe"', f'VALUE "OriginalFilename", "{display_name}.exe"')
            .replace('VALUE "ProductName", "RustDesk"', f'VALUE "ProductName", "{display_name}"')
            .replace('Copyright © 2026 Purslane Tech Pte. Ltd.', f'Copyright © 2026 {display_name}.')
        )
        if updated != txt:
            write_text(win_rc, updated)
            print(f"[rrremote] Updated Windows Runner.rc product metadata to {display_name}.")

    # 4. macOS app bundle name (RRRemote.app), DisplayName, Menu Bar & URL scheme
    mac_xcconfig = root / "flutter" / "macos" / "Runner" / "Configs" / "AppInfo.xcconfig"
    if mac_xcconfig.exists():
        txt = read_text(mac_xcconfig)
        updated = txt.replace("PRODUCT_NAME = RustDesk", f"PRODUCT_NAME = {display_name}")
        updated = updated.replace(
            "PRODUCT_COPYRIGHT = Copyright © 2026 Purslane Tech Pte. Ltd. All rights reserved.",
            f"PRODUCT_COPYRIGHT = Copyright © 2026 {display_name}. All rights reserved.",
        )
        if updated != txt:
            write_text(mac_xcconfig, updated)
            print(f"[rrremote] Updated macOS AppInfo.xcconfig PRODUCT_NAME to {display_name}.")

    mac_plist = root / "flutter" / "macos" / "Runner" / "Info.plist"
    if mac_plist.exists():
        txt = read_text(mac_plist)
        updated = txt
        if "<key>CFBundleDisplayName</key>" not in updated:
            updated = updated.replace(
                "\t<key>CFBundleExecutable</key>",
                f"\t<key>CFBundleDisplayName</key>\n\t<string>{display_name}</string>\n\t<key>CFBundleExecutable</key>",
                1,
            )
        updated = updated.replace(
            "<string>rustdesk</string>",
            f"<string>{lower_name}</string>",
        )
        if updated != txt:
            write_text(mac_plist, updated)
            print(f"[rrremote] Updated macOS Info.plist display name & URL scheme to {display_name}.")

    mac_menu = root / "flutter" / "macos" / "Runner" / "Base.lproj" / "MainMenu.xib"
    if mac_menu.exists():
        txt = read_text(mac_menu)
        updated = txt.replace('customModule="RustDesk"', f'customModule="{display_name}"').replace(
            "APP_NAME", display_name
        )
        if updated != txt:
            write_text(mac_menu, updated)
            print(f"[rrremote] Updated macOS MainMenu.xib menu bar & customModule to {display_name}.")

    mac_pbxproj = root / "flutter" / "macos" / "Runner.xcodeproj" / "project.pbxproj"
    if mac_pbxproj.exists():
        txt = read_text(mac_pbxproj)
        updated = txt.replace("/* RustDesk.app */", f"/* {display_name}.app */").replace(
            "path = RustDesk.app;", f"path = {display_name}.app;"
        )
        if updated != txt:
            write_text(mac_pbxproj, updated)
            print(f"[rrremote] Updated macOS project.pbxproj product reference to {display_name}.app.")

    # 5. Linux binary name (rrremote), desktop entries, systemd service, GTK title & packaging
    linux_cmake = root / "flutter" / "linux" / "CMakeLists.txt"
    if linux_cmake.exists():
        txt = read_text(linux_cmake)
        updated = txt.replace('set(BINARY_NAME "rustdesk")', f'set(BINARY_NAME "{lower_name}")')
        if updated != txt:
            write_text(linux_cmake, updated)
            print(f"[rrremote] Set Linux BINARY_NAME to {lower_name}.")

    linux_app = root / "flutter" / "linux" / "my_application.cc"
    if linux_app.exists():
        txt = read_text(linux_app)
        updated = (
            txt.replace(
                'gtk_header_bar_set_title(header_bar, "rustdesk");',
                f'gtk_header_bar_set_title(header_bar, "{display_name}");',
            )
            .replace(
                'gtk_window_set_title(window, "rustdesk");',
                f'gtk_window_set_title(window, "{display_name}");',
            )
            .replace(
                'gtk_icon_theme_load_icon(theme, "rustdesk",',
                f'gtk_icon_theme_load_icon(theme, "{lower_name}",',
            )
        )
        if updated != txt:
            write_text(linux_app, updated)
            print(f"[rrremote] Updated Linux GTK window title & icon name to {display_name}/{lower_name}.")

    desktop_file = root / "res" / "rustdesk.desktop"
    if desktop_file.exists():
        txt = read_text(desktop_file)
        updated = (
            txt.replace("Name=RustDesk", f"Name={display_name}")
            .replace("Comment=Remote Desktop", f"Comment={display_name} Remote Desktop")
            .replace("Exec=rustdesk %u", f"Exec={lower_name} %u")
            .replace("Icon=rustdesk", f"Icon={lower_name}")
            .replace("StartupWMClass=rustdesk", f"StartupWMClass={lower_name}")
        )
        write_text(desktop_file, updated)
        print(f"[rrremote] Updated res/rustdesk.desktop for {display_name}.")

    link_desktop = root / "res" / "rustdesk-link.desktop"
    if link_desktop.exists():
        txt = read_text(link_desktop)
        updated = (
            txt.replace("Name=RustDesk", f"Name={display_name}")
            .replace("MimeType=x-scheme-handler/rustdesk;", f"MimeType=x-scheme-handler/{lower_name};")
            .replace("TryExec=rustdesk", f"TryExec={lower_name}")
            .replace("Exec=rustdesk %u", f"Exec={lower_name} %u")
            .replace("Icon=rustdesk", f"Icon={lower_name}")
            .replace("StartupWMClass=rustdesk", f"StartupWMClass={lower_name}")
        )
        write_text(link_desktop, updated)
        print(f"[rrremote] Updated res/rustdesk-link.desktop for {display_name}.")

    svc_file = root / "res" / "rustdesk.service"
    if svc_file.exists():
        txt = read_text(svc_file)
        updated = (
            txt.replace("Description=RustDesk", f"Description={display_name}")
            .replace("ExecStart=/usr/bin/rustdesk --service", f"ExecStart=/usr/bin/{lower_name} --service")
            .replace('ExecStop=pkill -f "rustdesk --"', f'ExecStop=pkill -f "{lower_name} --"')
            .replace("PIDFile=/run/rustdesk.pid", f"PIDFile=/run/{lower_name}.pid")
        )
        write_text(svc_file, updated)
        print(f"[rrremote] Updated res/rustdesk.service for {display_name}.")

    pkgbuild = root / "res" / "PKGBUILD"
    if pkgbuild.exists():
        txt = read_text(pkgbuild)
        updated = (
            txt.replace("pkgname=rustdesk", f"pkgname={lower_name}")
            .replace("provides=()", "provides=('rustdesk')")
            .replace("conflicts=()", "conflicts=('rustdesk')")
            .replace("replaces=()", "replaces=('rustdesk')")
            .replace("/usr/share/rustdesk", f"/usr/share/{lower_name}")
            .replace("usr/bin/rustdesk", f"usr/bin/{lower_name}")
            .replace(f"/usr/share/{lower_name}/rustdesk", f"/usr/share/{lower_name}/{lower_name}")
            .replace(
                f'install -Dm 644 $HBB/res/rustdesk.service -t "${{pkgdir}}/usr/share/{lower_name}/files"',
                f'install -Dm 644 $HBB/res/rustdesk.service "${{pkgdir}}/usr/share/{lower_name}/files/{lower_name}.service"',
            )
            .replace(
                f'install -Dm 644 $HBB/res/rustdesk.desktop -t "${{pkgdir}}/usr/share/{lower_name}/files"',
                f'install -Dm 644 $HBB/res/rustdesk.desktop "${{pkgdir}}/usr/share/{lower_name}/files/{lower_name}.desktop"',
            )
            .replace(
                f'install -Dm 644 $HBB/res/rustdesk-link.desktop -t "${{pkgdir}}/usr/share/{lower_name}/files"',
                f'install -Dm 644 $HBB/res/rustdesk-link.desktop "${{pkgdir}}/usr/share/{lower_name}/files/{lower_name}-link.desktop"',
            )
            .replace("apps/rustdesk.png", f"apps/{lower_name}.png")
            .replace("apps/rustdesk.svg", f"apps/{lower_name}.svg")
        )
        write_text(pkgbuild, updated)
        print(f"[rrremote] Updated res/PKGBUILD for {lower_name}.")

    pacman_install = root / "res" / "pacman_install"
    if pacman_install.exists():
        new_pacman = f"""post_install() {{
\tsystemctl stop rustdesk 2>/dev/null || true
\tsystemctl disable rustdesk 2>/dev/null || true
\trm -f /etc/systemd/system/rustdesk.service /usr/share/applications/rustdesk.desktop /usr/share/applications/rustdesk-link.desktop 2>/dev/null || true
\tcp /usr/share/{lower_name}/files/{lower_name}.service /etc/systemd/system/{lower_name}.service
\tcp /usr/share/{lower_name}/files/{lower_name}.desktop /usr/share/applications/
\tcp /usr/share/{lower_name}/files/{lower_name}-link.desktop /usr/share/applications/
\tsystemctl daemon-reload
\tsystemctl enable {lower_name}
\tsystemctl start {lower_name}
\tupdate-desktop-database
}}

pre_upgrade() {{
\tsystemctl stop {lower_name} || true
\tsystemctl stop rustdesk || true
}}

post_upgrade() {{
\tpost_install
}}

pre_remove() {{
\tsystemctl stop {lower_name} || true
\tsystemctl disable {lower_name} || true
\trm -f /etc/systemd/system/{lower_name}.service || true
}}

post_remove() {{
\trm -f /usr/share/applications/{lower_name}.desktop || true
\trm -f /usr/share/applications/{lower_name}-link.desktop || true
\tupdate-desktop-database
}}
"""
        write_text(pacman_install, new_pacman)
        print(f"[rrremote] Updated res/pacman_install for {lower_name}.")

    for deb_script in ("res/DEBIAN/postinst", "res/DEBIAN/prerm", "res/DEBIAN/postrm"):
        sp = root / deb_script
        if sp.exists():
            txt = read_text(sp)
            updated = txt.replace("rustdesk", lower_name)
            write_text(sp, updated)
            print(f"[rrremote] Updated {deb_script} for {lower_name}.")

    for spec_rel in ("res/rpm-flutter.spec", "res/rpm-flutter-suse.spec"):
        sp = root / spec_rel
        if sp.exists():
            txt = read_text(sp)
            updated = (
                txt.replace("Name:       rustdesk", f"Name:       {lower_name}")
                .replace("URL:        https://rustdesk.com", "URL:        https://github.com/melotusme/RRRemote")
                .replace("Vendor:     rustdesk <info@rustdesk.com>", f"Vendor:     {display_name}")
                .replace("/usr/share/rustdesk", f"/usr/share/{lower_name}")
                .replace("/usr/bin/rustdesk", f"/usr/bin/{lower_name}")
                .replace("/usr/lib/rustdesk", f"/usr/lib/{lower_name}")
                .replace("/usr/local/rustdesk", f"/usr/local/{lower_name}")
                .replace(
                    f'install -Dm 644 $HBB/res/rustdesk.service -t "%{{buildroot}}/usr/share/{lower_name}/files"',
                    f'install -Dm 644 $HBB/res/rustdesk.service "%{{buildroot}}/usr/share/{lower_name}/files/{lower_name}.service"',
                )
                .replace(
                    f'install -Dm 644 $HBB/res/rustdesk.desktop -t "%{{buildroot}}/usr/share/{lower_name}/files"',
                    f'install -Dm 644 $HBB/res/rustdesk.desktop "%{{buildroot}}/usr/share/{lower_name}/files/{lower_name}.desktop"',
                )
                .replace(
                    f'install -Dm 644 $HBB/res/rustdesk-link.desktop -t "%{{buildroot}}/usr/share/{lower_name}/files"',
                    f'install -Dm 644 $HBB/res/rustdesk-link.desktop "%{{buildroot}}/usr/share/{lower_name}/files/{lower_name}-link.desktop"',
                )
                .replace("apps/rustdesk.png", f"apps/{lower_name}.png")
                .replace("apps/rustdesk.svg", f"apps/{lower_name}.svg")
                .replace("files/rustdesk.service", f"files/{lower_name}.service")
                .replace("files/rustdesk.desktop", f"files/{lower_name}.desktop")
                .replace("files/rustdesk-link.desktop", f"files/{lower_name}-link.desktop")
                .replace("/etc/systemd/system/rustdesk.service", f"/etc/systemd/system/{lower_name}.service")
                .replace("/usr/share/applications/rustdesk.desktop", f"/usr/share/applications/{lower_name}.desktop")
                .replace("/usr/share/applications/rustdesk-link.desktop", f"/usr/share/applications/{lower_name}-link.desktop")
                .replace(f"/usr/share/{lower_name}/rustdesk", f"/usr/share/{lower_name}/{lower_name}")
                .replace("systemctl stop rustdesk", f"systemctl stop {lower_name}")
                .replace("systemctl enable rustdesk", f"systemctl enable {lower_name}")
                .replace("systemctl start rustdesk", f"systemctl start {lower_name}")
                .replace("systemctl disable rustdesk", f"systemctl disable {lower_name}")
            )
            write_text(sp, updated)
            print(f"[rrremote] Updated {spec_rel} for {lower_name}.")

    build_py = root / "build.py"
    if build_py.exists():
        txt = read_text(build_py)
        updated = (
            txt.replace(
                "Release/RustDesk.app/Contents/MacOS/",
                f"Release/{display_name}.app/Contents/MacOS/",
            )
            .replace("Package: rustdesk", f"Package: {lower_name}")
            .replace("Maintainer: rustdesk <info@rustdesk.com>", f"Maintainer: {display_name}")
            .replace("Homepage: https://rustdesk.com", "Homepage: https://github.com/melotusme/RRRemote")
            .replace("tmpdeb/usr/share/rustdesk/rustdesk", f"tmpdeb/usr/share/{lower_name}/{lower_name}")
            .replace("tmpdeb/usr/share/rustdesk", f"tmpdeb/usr/share/{lower_name}")
            .replace("tmpdeb/usr/bin/rustdesk", f"tmpdeb/usr/bin/{lower_name}")
            .replace(
                f"cp ../res/rustdesk.service tmpdeb/usr/share/{lower_name}/files/systemd/",
                f"cp ../res/rustdesk.service tmpdeb/usr/share/{lower_name}/files/systemd/{lower_name}.service",
            )
            .replace("apps/rustdesk.png", f"apps/{lower_name}.png")
            .replace("apps/rustdesk.svg", f"apps/{lower_name}.svg")
            .replace("applications/rustdesk.desktop", f"applications/{lower_name}.desktop")
            .replace("applications/rustdesk-link.desktop", f"applications/{lower_name}-link.desktop")
            .replace("dpkg-deb -b tmpdeb rustdesk.deb;", f"dpkg-deb -b tmpdeb {lower_name}.deb;")
            .replace("os.rename('rustdesk.deb', '../rustdesk-%s.deb' % version)", f"os.rename('{lower_name}.deb', '../{lower_name}-%s.deb' % version)")
        )
        if updated != txt:
            write_text(build_py, updated)
            print(f"[rrremote] Updated build.py macOS & Linux packaging paths for {display_name}/{lower_name}.")

    # 6. Android label & modern Gradle mavenCentral() repository
    android_manifest = root / "flutter" / "android" / "app" / "src" / "main" / "AndroidManifest.xml"
    if android_manifest.exists():
        txt = read_text(android_manifest)
        updated = txt.replace('android:label="RustDesk"', f'android:label="{display_name}"').replace(
            'android:label="RustDesk Input"', f'android:label="{display_name} Input"'
        )
        if updated != txt:
            write_text(android_manifest, updated)
            print(f"[rrremote] Updated AndroidManifest.xml labels to {display_name}.")

    android_gradle = root / "flutter" / "android" / "build.gradle"
    if android_gradle.exists():
        txt = read_text(android_gradle)
        if "mavenCentral()" not in txt and "jcenter()" in txt:
            updated = txt.replace("        jcenter()", "        mavenCentral()\n        jcenter()", 1)
            write_text(android_gradle, updated)
            print("[rrremote] Added mavenCentral() to flutter/android/build.gradle.")

    # 7. iOS display & bundle name
    ios_plist = root / "flutter" / "ios" / "Runner" / "Info.plist"
    if ios_plist.exists():
        txt = read_text(ios_plist)
        updated = (
            txt.replace(
                "<key>CFBundleDisplayName</key>\n\t<string>RustDesk</string>",
                f"<key>CFBundleDisplayName</key>\n\t<string>{display_name}</string>",
            )
            .replace(
                "<key>CFBundleName</key>\n\t<string>RustDesk</string>",
                f"<key>CFBundleName</key>\n\t<string>{display_name}</string>",
            )
            .replace(
                "<string>rustdesk</string>",
                f"<string>{lower_name}</string>",
            )
        )
        if updated != txt:
            write_text(ios_plist, updated)
            print(f"[rrremote] Updated iOS Info.plist display name to {display_name}.")


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    display_name = os.environ.get("APP_DISPLAY_NAME", "RRRemote").strip()
    update_repo = os.environ.get("UPDATE_REPO", "melotusme/RRRemote").strip()
    build_tag = os.environ.get("RR_BUILD_TAG", "v1.5.3-rr5").strip()
    rendezvous = os.environ.get("RR_RENDEZVOUS_SERVER", "").strip()
    pub_key = os.environ.get("RR_PUB_KEY", "").strip()
    api_server = os.environ.get("RR_API_SERVER", "").strip()

    print(f"[rrremote] Applying customizations to {root}")
    print(f"[rrremote] Display name: {display_name}, Update repo: {update_repo}, Build tag: {build_tag}")
    print(
        "[rrremote] Build-time server preset:",
        "enabled" if (rendezvous or pub_key or api_server) else "disabled (configure in-app)",
    )

    patch_hbb_common_config(root, display_name, rendezvous, pub_key, api_server)
    patch_update_checker(root, update_repo, build_tag)
    patch_updater_artifact_resolver(root, update_repo)
    patch_default_api_server_fallback(root, api_server)
    patch_display_branding(root, display_name)
    apply_brand_icons(root)

    ui_script = Path(__file__).resolve().parent / "apply_ui_polish.py"
    if ui_script.exists():
        env = os.environ.copy()
        env["UPDATE_REPO"] = update_repo
        subprocess.run([sys.executable, str(ui_script), str(root)], check=True, env=env)

    print("[rrremote] All customizations applied successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
