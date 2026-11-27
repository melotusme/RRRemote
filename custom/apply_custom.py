#!/usr/bin/env python3
"""
Apply RRRemote customizations to a checked-out upstream RustDesk source tree:
1. Disable account/login subsystem cleanly (`is_disable_account() -> true`) so no
   unwanted login/password screens appear (keeps Recent / Favorites / LAN Discovery).
2. Configure single-user personal defaults in `hbb_common::config` (all session/host
   permissions enabled out-of-the-box, adaptive view style, quality monitor, direct
   LAN port 21118, and macOS software codec default to avoid VideoToolbox black screens).
3. Enforce RFC 2544 TUN fake-IP (octets 198, 18/19) non-persistence, startup config
   sanitization, and physical LAN interface fallback for NAT test & intranet listen.
4. Harden macOS video encoding so any frame-1 hardware encoder error immediately
   switches to software VP9/AV1 instead of stalling behind `refresh_allowed == false`.
5. Replace upstream RustDesk icons, strings & metadata across all platforms with
   the original RRRemote brand suite in `branding/`.
6. Zero-rate-limit built-in updater via GitHub `/releases/latest` redirect +
   `-rrN` revision comparison + SHA256-verified `rrremote-update.json` manifest
   (including `get_update_download_file_from_url`, Windows MSI/EXE & macOS root DMG).
7. Optional build-time server defaults via environment variables (never in git).
8. Industrial-grade UI & UX polish via `apply_ui_polish.py`.
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


def patch_hbb_common_config(
    root: Path,
    display_name: str,
    update_repo: str,
    rendezvous: str,
    pub_key: str,
    api_server: str,
) -> None:
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

    # 2. Point documentation helper links to the RRRemote repository instead of rustdesk.com
    repo_url = f"https://github.com/{update_repo}"
    for old_doc, new_doc in (
        (
            'pub const LINK_DOCS_HOME: &str = "https://rustdesk.com/docs/en/";',
            f'pub const LINK_DOCS_HOME: &str = "{repo_url}";',
        ),
        (
            'pub const LINK_DOCS_X11_REQUIRED: &str = "https://rustdesk.com/docs/en/manual/linux/#x11-required";',
            f'pub const LINK_DOCS_X11_REQUIRED: &str = "{repo_url}";',
        ),
    ):
        if old_doc in content:
            content = content.replace(old_doc, new_doc, 1)
            changed = True

    # 3. Single-user personal defaults in DEFAULT_SETTINGS / DEFAULT_DISPLAY_SETTINGS / DEFAULT_LOCAL_SETTINGS:
    #    Enable all host & session permissions out-of-the-box, adaptive view style, quality monitor,
    #    direct LAN access (port 21118), auto-update, and macOS software codec default ("enable-hwcodec" = "N").
    old_defaults_block = (
        "    pub static ref DEFAULT_SETTINGS: RwLock<HashMap<String, String>> = Default::default();\n"
        "    pub static ref OVERWRITE_SETTINGS: RwLock<HashMap<String, String>> = Default::default();\n"
        "    pub static ref DEFAULT_DISPLAY_SETTINGS: RwLock<HashMap<String, String>> = Default::default();\n"
        "    pub static ref OVERWRITE_DISPLAY_SETTINGS: RwLock<HashMap<String, String>> = Default::default();\n"
        "    pub static ref DEFAULT_LOCAL_SETTINGS: RwLock<HashMap<String, String>> = Default::default();"
    )
    new_defaults_block = """    pub static ref DEFAULT_SETTINGS: RwLock<HashMap<String, String>> = RwLock::new({
        #[allow(unused_mut)]
        let mut m = HashMap::from([
            ("access-mode".to_owned(), "full".to_owned()),
            ("enable-keyboard".to_owned(), "Y".to_owned()),
            ("enable-clipboard".to_owned(), "Y".to_owned()),
            ("enable-file-transfer".to_owned(), "Y".to_owned()),
            ("enable-audio".to_owned(), "Y".to_owned()),
            ("enable-tunnel".to_owned(), "Y".to_owned()),
            ("enable-terminal".to_owned(), "Y".to_owned()),
            ("enable-camera".to_owned(), "Y".to_owned()),
            ("enable-remote-restart".to_owned(), "Y".to_owned()),
            ("enable-record-session".to_owned(), "Y".to_owned()),
            ("enable-remote-printer".to_owned(), "Y".to_owned()),
            ("enable-block-input".to_owned(), "Y".to_owned()),
            ("enable-privacy-mode".to_owned(), "Y".to_owned()),
            ("enable-lan-discovery".to_owned(), "Y".to_owned()),
            ("enable-abr".to_owned(), "Y".to_owned()),
            ("allow-remote-config-modification".to_owned(), "Y".to_owned()),
            ("allow-auto-update".to_owned(), "Y".to_owned()),
            ("direct-server".to_owned(), "Y".to_owned()),
            ("approve-mode".to_owned(), "password".to_owned()),
            ("verification-method".to_owned(), "use-both-passwords".to_owned()),
        ]);
        #[cfg(target_os = "macos")]
        m.insert("enable-hwcodec".to_owned(), "N".to_owned());
        m
    });
    pub static ref OVERWRITE_SETTINGS: RwLock<HashMap<String, String>> = Default::default();
    pub static ref DEFAULT_DISPLAY_SETTINGS: RwLock<HashMap<String, String>> = RwLock::new(HashMap::from([
        ("view_style".to_owned(), "adaptive".to_owned()),
        ("show_quality_monitor".to_owned(), "Y".to_owned()),
        ("enable-file-copy-paste".to_owned(), "Y".to_owned()),
        ("show_remote_cursor".to_owned(), "Y".to_owned()),
        ("sync-init-clipboard".to_owned(), "Y".to_owned()),
    ]));
    pub static ref OVERWRITE_DISPLAY_SETTINGS: RwLock<HashMap<String, String>> = Default::default();
    pub static ref DEFAULT_LOCAL_SETTINGS: RwLock<HashMap<String, String>> = RwLock::new(HashMap::from([
        ("allow-remote-cm-modification".to_owned(), "Y".to_owned()),
        ("enable-check-update".to_owned(), "Y".to_owned()),
        ("allow-sync-clipboard-between-sessions".to_owned(), "Y".to_owned()),
    ]));"""
    if '"show_quality_monitor".to_owned()' in content and '"allow-remote-cm-modification".to_owned()' in content:
        print("[rrremote] Personal permission & display defaults already configured in hbb_common::config.")
    elif old_defaults_block in content:
        content = content.replace(old_defaults_block, new_defaults_block, 1)
        changed = True
        print("[rrremote] Configured full personal permission & display defaults in hbb_common::config.")
    else:
        raise RuntimeError("Failed to locate DEFAULT_SETTINGS block in libs/hbb_common/src/config.rs")

    # 3b. Default desktop UserDefaultConfig view_style to "adaptive" (matching mobile)
    old_view_style = (
        '            #[cfg(not(any(target_os = "android", target_os = "ios")))]\n'
        '            keys::OPTION_VIEW_STYLE => self.get_string(key, "original", vec!["adaptive"]),'
    )
    new_view_style = (
        '            #[cfg(not(any(target_os = "android", target_os = "ios")))]\n'
        '            keys::OPTION_VIEW_STYLE => self.get_string(key, "adaptive", vec!["original"]),'
    )
    if new_view_style in content and old_view_style not in content:
        print("[rrremote] Desktop OPTION_VIEW_STYLE already defaults to adaptive.")
    elif old_view_style in content:
        content = content.replace(old_view_style, new_view_style, 1)
        changed = True
        print("[rrremote] Defaulted desktop OPTION_VIEW_STYLE to adaptive.")
    else:
        raise RuntimeError("Failed to locate desktop OPTION_VIEW_STYLE in libs/hbb_common/src/config.rs")

    # 3c. Ensure option2bool treats empty/unset enable-hwcodec on macOS as disabled (false)
    old_opt2bool = (
        "pub fn option2bool(option: &str, value: &str) -> bool {\n"
        '    if option.starts_with("enable-") {'
    )
    new_opt2bool = (
        "pub fn option2bool(option: &str, value: &str) -> bool {\n"
        '    #[cfg(target_os = "macos")]\n'
        '    if option == "enable-hwcodec" {\n'
        '        return value == "Y";\n'
        "    }\n"
        '    if option.starts_with("enable-") {'
    )
    if 'if option == "enable-hwcodec"' in content:
        print("[rrremote] macOS option2bool enable-hwcodec guard already present.")
    elif old_opt2bool in content:
        content = content.replace(old_opt2bool, new_opt2bool, 1)
        changed = True
        print("[rrremote] Defaulted macOS option2bool(enable-hwcodec) to false unless explicitly 'Y'.")
    else:
        raise RuntimeError("Failed to locate option2bool in libs/hbb_common/src/config.rs")

    # 4. RFC 2544 TUN fake-IP (octets 198, 18/19) non-persistence & self-healing on Config2 load/save
    tun_helpers = """#[inline]
pub fn is_tun_fake_ip(ip: &std::net::IpAddr) -> bool {
    if let std::net::IpAddr::V4(v4) = ip {
        let oct = v4.octets();
        oct[0] == 198 && (oct[1] == 18 || oct[1] == 19)
    } else {
        false
    }
}

#[inline]
pub fn is_tun_fake_ip_str(s: &str) -> bool {
    s.trim()
        .parse::<std::net::IpAddr>()
        .map(|ip| is_tun_fake_ip(&ip))
        .unwrap_or(false)
}

impl Config2 {"""
    if "pub fn is_tun_fake_ip(" not in content:
        if "impl Config2 {" not in content:
            raise RuntimeError("Failed to locate `impl Config2 {` in libs/hbb_common/src/config.rs")
        content = content.replace("impl Config2 {", tun_helpers, 1)
        changed = True
        print("[rrremote] Added RFC 2544 TUN fake-IP helpers in hbb_common::config.")

    old_c2_load = (
        "        let (unlock_pin, _, store2) =\n"
        "            decrypt_str_or_original(&config.unlock_pin, PASSWORD_ENC_VERSION);\n"
        "        config.unlock_pin = unlock_pin;\n"
        "        store |= store2;\n"
        "        if store {"
    )
    new_c2_load = (
        "        let (unlock_pin, _, store2) =\n"
        "            decrypt_str_or_original(&config.unlock_pin, PASSWORD_ENC_VERSION);\n"
        "        config.unlock_pin = unlock_pin;\n"
        "        store |= store2;\n"
        "        if config\n"
        "            .options\n"
        '            .get("local-ip-addr")\n'
        "            .is_some_and(|v| is_tun_fake_ip_str(v))\n"
        "        {\n"
        '            config.options.remove("local-ip-addr");\n'
        "            store = true;\n"
        "        }\n"
        "        if store {"
    )
    if 'config.options.remove("local-ip-addr");' in content:
        print("[rrremote] Config2::load TUN fake-IP sanitizer already applied.")
    elif old_c2_load in content:
        content = content.replace(old_c2_load, new_c2_load, 1)
        changed = True
        print("[rrremote] Added startup TUN fake-IP sanitizer in Config2::load.")
    else:
        raise RuntimeError("Failed to locate Config2::load unlock_pin block in libs/hbb_common/src/config.rs")

    old_purify = (
        "    fn purify_options(v: &mut HashMap<String, String>) {\n"
        "        v.retain(|k, v| is_option_can_save(&OVERWRITE_SETTINGS, k, &DEFAULT_SETTINGS, v));\n"
        "    }"
    )
    new_purify = (
        "    fn purify_options(v: &mut HashMap<String, String>) {\n"
        "        v.retain(|k, v| {\n"
        '            !(k == "local-ip-addr" && is_tun_fake_ip_str(v))\n'
        "                && is_option_can_save(&OVERWRITE_SETTINGS, k, &DEFAULT_SETTINGS, v)\n"
        "        });\n"
        "    }"
    )
    if '!(k == "local-ip-addr" && is_tun_fake_ip_str(v))' in content:
        print("[rrremote] Config::purify_options TUN fake-IP guard already applied.")
    elif old_purify in content:
        content = content.replace(old_purify, new_purify, 1)
        changed = True
        print("[rrremote] Guarded Config::purify_options against persisting TUN fake-IPs.")
    else:
        raise RuntimeError("Failed to locate Config::purify_options in libs/hbb_common/src/config.rs")

    old_set_opt = (
        "    pub fn set_option(k: String, v: String) {\n"
        "        if !is_option_can_save(&OVERWRITE_SETTINGS, &k, &DEFAULT_SETTINGS, &v) {"
    )
    new_set_opt = (
        "    pub fn set_option(k: String, v: String) {\n"
        '        if (k == "local-ip-addr" && is_tun_fake_ip_str(&v))\n'
        "            || !is_option_can_save(&OVERWRITE_SETTINGS, &k, &DEFAULT_SETTINGS, &v)\n"
        "        {"
    )
    if '(k == "local-ip-addr" && is_tun_fake_ip_str(&v))' in content:
        print("[rrremote] Config::set_option TUN fake-IP guard already applied.")
    elif old_set_opt in content:
        content = content.replace(old_set_opt, new_set_opt, 1)
        changed = True
        print("[rrremote] Guarded Config::set_option against persisting TUN fake-IPs.")
    else:
        raise RuntimeError("Failed to locate Config::set_option in libs/hbb_common/src/config.rs")

    # 5. Optional build-time server defaults via environment variables
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

    baked_key_const = f"pub const RRREMOTE_HAS_BAKED_KEY: bool = {'true' if pub_key else 'false'};"
    if "pub const RRREMOTE_HAS_BAKED_KEY:" in content:
        new_content, count = re.subn(
            r"pub const RRREMOTE_HAS_BAKED_KEY:\s*bool\s*=\s*(?:true|false);",
            baked_key_const,
            content,
            count=1,
        )
        if new_content != content:
            content = new_content
            changed = True
    else:
        new_content, count = re.subn(
            r'(pub const RS_PUB_KEY:\s*&str\s*=\s*"[^"]*";)',
            rf"\1\n{baked_key_const}",
            content,
            count=1,
        )
        if count != 1:
            raise RuntimeError("Failed to insert RRREMOTE_HAS_BAKED_KEY in libs/hbb_common/src/config.rs")
        content = new_content
        changed = True
        print(f"[rrremote] Recorded RRREMOTE_HAS_BAKED_KEY = {'true' if pub_key else 'false'}.")

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


def patch_macos_video_reliability(root: Path) -> None:
    """Eliminate macOS VideoToolbox RAM encode black screens via software default + frame-1 fallback."""
    # 1. Default enable_hwcodec_option() on macOS to disabled unless explicitly set to "Y"
    codec_rs = root / "libs" / "scrap" / "src" / "common" / "codec.rs"
    if not codec_rs.exists():
        raise FileNotFoundError(f"Expected {codec_rs}")
    codec_txt = read_text(codec_rs)
    old_hw_opt = """#[cfg(any(feature = "hwcodec", feature = "mediacodec"))]
pub fn enable_hwcodec_option() -> bool {
    use base::config::keys::OPTION_ENABLE_HWCODEC;

    if !cfg!(target_os = "ios") {
        return option2bool(
            OPTION_ENABLE_HWCODEC,
            &Config::get_option(OPTION_ENABLE_HWCODEC),
        );
    }
    false
}"""
    new_hw_opt = """#[cfg(any(feature = "hwcodec", feature = "mediacodec"))]
pub fn enable_hwcodec_option() -> bool {
    use base::config::keys::OPTION_ENABLE_HWCODEC;

    #[cfg(target_os = "macos")]
    {
        return Config::get_option(OPTION_ENABLE_HWCODEC) == "Y";
    }
    #[cfg(not(target_os = "macos"))]
    if !cfg!(target_os = "ios") {
        return option2bool(
            OPTION_ENABLE_HWCODEC,
            &Config::get_option(OPTION_ENABLE_HWCODEC),
        );
    }
    #[cfg(not(target_os = "macos"))]
    false
}"""
    if "return Config::get_option(OPTION_ENABLE_HWCODEC) == \"Y\";" in codec_txt:
        print("[rrremote] macOS enable_hwcodec_option default already patched in libs/scrap/src/common/codec.rs.")
    elif old_hw_opt in codec_txt:
        codec_txt = codec_txt.replace(old_hw_opt, new_hw_opt, 1)
        write_text(codec_rs, codec_txt)
        print("[rrremote] Patched libs/scrap/src/common/codec.rs so macOS defaults to software VP9/AV1.")
    else:
        raise RuntimeError("Failed to locate enable_hwcodec_option in libs/scrap/src/common/codec.rs")

    # 2. Ensure HwCodecConfig::clear initializes in-memory CONFIG before clearing ram_encode
    #    so HwCodecConfig::get() never re-reads broken VideoToolbox encoders from _hwcodec cache.
    hwcodec_rs = root / "libs" / "scrap" / "src" / "common" / "hwcodec.rs"
    if not hwcodec_rs.exists():
        raise FileNotFoundError(f"Expected {hwcodec_rs}")
    hw_txt = read_text(hwcodec_rs)
    old_clear = (
        "            let mut c = CONFIG.lock().unwrap();\n"
        "            if let Some(c) = c.as_mut() {"
    )
    new_clear = (
        "            let _ = Self::get();\n"
        "            let mut guard = CONFIG.lock().unwrap();\n"
        "            let c = guard.get_or_insert_with(HwCodecConfig::default);\n"
        "            {"
    )
    if "guard.get_or_insert_with(HwCodecConfig::default)" in hw_txt:
        print("[rrremote] HwCodecConfig::clear cache guard already patched in libs/scrap/src/common/hwcodec.rs.")
    elif old_clear in hw_txt:
        hw_txt = hw_txt.replace(old_clear, new_clear, 1)
        write_text(hwcodec_rs, hw_txt)
        print("[rrremote] Hardened HwCodecConfig::clear in libs/scrap/src/common/hwcodec.rs.")
    else:
        raise RuntimeError("Failed to locate HwCodecConfig::clear in libs/scrap/src/common/hwcodec.rs")

    # 3. In src/server/video_service.rs, VideoToolbox has latency_free() == false (repeat == true)
    #    while refresh_allowed(false, false, false) == false on macOS, deadlocking static screen
    #    updates when frame 1 fails with `RAM encode failed: -1`. Immediately disable & switch
    #    hardware encoder on frame-1 error on macOS so VP9/AV1 renders immediately.
    vs_rs = root / "src" / "server" / "video_service.rs"
    if not vs_rs.exists():
        raise FileNotFoundError(f"Expected {vs_rs}")
    vs_txt = read_text(vs_rs)
    old_switch = (
        "            // repeat encoders can reach max_fail_times on the first frame\n"
        "            if (first && !repeat) || *encode_fail_counter >= max_fail_times {"
    )
    new_switch = (
        "            // repeat encoders can reach max_fail_times on the first frame;\n"
        "            // on macOS refresh_allowed blocks static refreshes before warmup, so switch immediately on frame-1 hw failure.\n"
        '            if (first && (!repeat || (cfg!(target_os = "macos") && encoder.is_hardware())))\n'
        "                || *encode_fail_counter >= max_fail_times\n"
        "            {"
    )
    if 'cfg!(target_os = "macos") && encoder.is_hardware()' in vs_txt:
        print("[rrremote] macOS frame-1 hardware encoder fallback already patched in src/server/video_service.rs.")
    elif old_switch in vs_txt:
        vs_txt = vs_txt.replace(old_switch, new_switch, 1)
        write_text(vs_rs, vs_txt)
        print("[rrremote] Added immediate frame-1 VideoToolbox -> VP9/AV1 fallback in src/server/video_service.rs.")
    else:
        raise RuntimeError("Failed to locate handle_one_frame switch condition in src/server/video_service.rs")


def patch_macos_input_reliability(root: Path) -> None:
    """Prevent macOS keyboard blackouts on missing Input Monitoring & log silent Accessibility drops."""
    # 1. src/keyboard.rs: guarantee Flutter Input source 2 fallback whenever macOS Input Monitoring
    #    is denied without permanently overwriting LocalConfig (so native rdev recovers once granted).
    kb_rs = root / "src" / "keyboard.rs"
    if not kb_rs.exists():
        raise FileNotFoundError(f"Expected {kb_rs}")
    kb_txt = read_text(kb_rs)
    kb_changed = False

    old_init_src = """        #[cfg(target_os = "macos")]
        if !crate::platform::macos::is_can_input_monitoring(false) {
            log::error!("init_input_source, is_can_input_monitoring() false");
            set_local_option(
                CONFIG_OPTION_INPUT_SOURCE.to_string(),
                CONFIG_INPUT_SOURCE_2.to_string(),
            );
            return;
        }"""
    new_init_src = """        #[cfg(target_os = "macos")]
        if !crate::platform::macos::is_can_input_monitoring(false) {
            log::error!(
                "init_input_source, is_can_input_monitoring() false; falling back to Flutter Input source 2 without overwriting saved config"
            );
            return;
        }"""
    if "falling back to Flutter Input source 2 without overwriting saved config" in kb_txt:
        print("[rrremote] macOS init_input_source non-destructive fallback already patched in src/keyboard.rs.")
    elif old_init_src in kb_txt:
        kb_txt = kb_txt.replace(old_init_src, new_init_src, 1)
        kb_changed = True
        print("[rrremote] Patched src/keyboard.rs::init_input_source() to avoid permanently overwriting input-source on macOS.")
    else:
        raise RuntimeError("Failed to locate macOS init_input_source block in src/keyboard.rs")

    old_get_src = """    #[inline]
    pub fn get_cur_session_input_source() -> String {
        #[cfg(target_os = "linux")]
        if !crate::platform::linux::is_x11() {
            return CONFIG_INPUT_SOURCE_2.to_string();
        }
        let input_source = get_local_option(CONFIG_OPTION_INPUT_SOURCE.to_string());"""
    new_get_src = """    #[inline]
    pub fn get_cur_session_input_source() -> String {
        #[cfg(target_os = "linux")]
        if !crate::platform::linux::is_x11() {
            return CONFIG_INPUT_SOURCE_2.to_string();
        }
        #[cfg(target_os = "macos")]
        if !crate::platform::macos::is_can_input_monitoring(false) {
            return CONFIG_INPUT_SOURCE_2.to_string();
        }
        let input_source = get_local_option(CONFIG_OPTION_INPUT_SOURCE.to_string());"""
    if (
        '#[cfg(target_os = "macos")]\n'
        "        if !crate::platform::macos::is_can_input_monitoring(false) {\n"
        "            return CONFIG_INPUT_SOURCE_2.to_string();\n"
        "        }"
    ) in kb_txt:
        print("[rrremote] macOS get_cur_session_input_source guard already patched in src/keyboard.rs.")
    elif old_get_src in kb_txt:
        kb_txt = kb_txt.replace(old_get_src, new_get_src, 1)
        kb_changed = True
        print("[rrremote] Added macOS Input Monitoring guard in src/keyboard.rs::get_cur_session_input_source().")
    else:
        raise RuntimeError("Failed to locate get_cur_session_input_source() in src/keyboard.rs")

    if kb_changed:
        write_text(kb_rs, kb_txt)

    # 2. src/server/input_service.rs: lazily re-init VIRTUAL_INPUT_STATE on macOS if None, and emit
    #    a throttled warning when remote mouse/keyboard input arrives while Accessibility is denied.
    inp_rs = root / "src" / "server" / "input_service.rs"
    if not inp_rs.exists():
        raise FileNotFoundError(f"Expected {inp_rs}")
    inp_txt = read_text(inp_rs)
    inp_changed = False

    old_mouse_mac = """    #[cfg(target_os = "macos")]
    en.set_ignore_flags(enigo_ignore_flags());"""
    new_mouse_mac = """    #[cfg(target_os = "macos")]
    {
        warn_if_macos_accessibility_denied("mouse");
        en.set_ignore_flags(enigo_ignore_flags());
    }"""
    if 'warn_if_macos_accessibility_denied("mouse");' in inp_txt:
        print("[rrremote] macOS mouse Accessibility warning already patched in src/server/input_service.rs.")
    elif old_mouse_mac in inp_txt:
        inp_txt = inp_txt.replace(old_mouse_mac, new_mouse_mac, 1)
        inp_changed = True
        print("[rrremote] Added throttled macOS Accessibility warning for remote mouse input in src/server/input_service.rs.")
    else:
        raise RuntimeError("Failed to locate macOS handle_mouse_simulation_ anchor in src/server/input_service.rs")

    old_key_mac = """#[inline]
#[cfg(target_os = "macos")]
pub fn handle_key(evt: &KeyEvent) {
    // having GUI, run main GUI thread, otherwise crash
    let evt = evt.clone();
    QUEUE.exec_async(move || handle_key_(&evt));"""
    new_key_mac = """#[inline]
#[cfg(target_os = "macos")]
pub fn handle_key(evt: &KeyEvent) {
    warn_if_macos_accessibility_denied("keyboard");
    // having GUI, run main GUI thread, otherwise crash
    let evt = evt.clone();
    QUEUE.exec_async(move || handle_key_(&evt));"""
    if 'warn_if_macos_accessibility_denied("keyboard");' in inp_txt:
        print("[rrremote] macOS keyboard Accessibility warning already patched in src/server/input_service.rs.")
    elif old_key_mac in inp_txt:
        inp_txt = inp_txt.replace(old_key_mac, new_key_mac, 1)
        inp_changed = True
        print("[rrremote] Added throttled macOS Accessibility warning for remote keyboard input in src/server/input_service.rs.")
    else:
        raise RuntimeError("Failed to locate macOS handle_key() in src/server/input_service.rs")

    old_sim = """#[inline]
#[cfg(target_os = "macos")]
fn simulate_(event_type: &EventType) {
    unsafe {
        let _lock = VIRTUAL_INPUT_MTX.lock();
        if let Some(input) = VIRTUAL_INPUT_STATE.as_ref() {
            let _ = input.simulate(&event_type);
        } else if matches!(event_type, EventType::KeyRelease(_)) {
            hbb_common::throttled_log!(
                VirtualInputState::KEY_UP_ERROR_LOG_INTERVAL,
                error,
                "Failed to inject macOS key-up: virtual input is not initialized"
            );
        }
    }
}"""
    new_sim = """#[inline]
#[cfg(target_os = "macos")]
fn warn_if_macos_accessibility_denied(kind: &str) {
    use std::sync::atomic::AtomicI64;
    static LAST_AX_WARN_MS: AtomicI64 = AtomicI64::new(0);
    if !crate::platform::macos::is_process_trusted(false) {
        let now = get_time();
        let prev = LAST_AX_WARN_MS.load(Ordering::Relaxed);
        if now - prev >= 10_000
            && LAST_AX_WARN_MS
                .compare_exchange(prev, now, Ordering::Relaxed, Ordering::Relaxed)
                .is_ok()
        {
            log::warn!(
                "macOS Accessibility (AXIsProcessTrusted) is NOT granted; remote {} input is silently dropped by WindowServer. Re-add RRRemote in System Settings -> Privacy & Security -> Accessibility.",
                kind
            );
        }
    }
}

#[inline]
#[cfg(target_os = "macos")]
fn simulate_(event_type: &EventType) {
    unsafe {
        let _lock = VIRTUAL_INPUT_MTX.lock();
        if VIRTUAL_INPUT_STATE.is_none() {
            VIRTUAL_INPUT_STATE = VirtualInputState::new();
        }
        if let Some(input) = VIRTUAL_INPUT_STATE.as_ref() {
            let _ = input.simulate(&event_type);
        } else {
            hbb_common::throttled_log!(
                VirtualInputState::KEY_UP_ERROR_LOG_INTERVAL,
                error,
                "Failed to inject macOS key event {:?}: virtual input could not be initialized",
                event_type
            );
        }
    }
}"""
    if "fn warn_if_macos_accessibility_denied(kind: &str)" in inp_txt:
        print("[rrremote] macOS VIRTUAL_INPUT_STATE lazy re-init & Accessibility helper already patched in src/server/input_service.rs.")
    elif old_sim in inp_txt:
        inp_txt = inp_txt.replace(old_sim, new_sim, 1)
        inp_changed = True
        print("[rrremote] Added macOS VIRTUAL_INPUT_STATE lazy re-init & Accessibility diagnostics in src/server/input_service.rs.")
    else:
        raise RuntimeError("Failed to locate macOS simulate_() in src/server/input_service.rs")

    if inp_changed:
        write_text(inp_rs, inp_txt)


def patch_update_checker(root: Path, update_repo: str, build_tag: str) -> None:
    """Redirect built-in update check to GitHub `/releases/latest` with -rrN revision support."""
    if "/" not in update_repo:
        raise ValueError(f"Invalid UPDATE_REPO: {update_repo!r}, expected 'owner/repo'")
    owner, repo = update_repo.split("/", 1)

    common_rs = root / "src" / "common.rs"
    if not common_rs.exists():
        raise FileNotFoundError(f"Expected {common_rs}")

    content = read_text(common_rs)

    # 0. Enable startup check_software_update() even though APP_NAME != "RustDesk" (is_custom_client() == true)
    old_check_sw = (
        "pub fn check_software_update() {\n"
        "    if is_custom_client() {\n"
        "        return;\n"
        "    }\n"
        "    let opt = LocalConfig::get_option(keys::OPTION_ENABLE_CHECK_UPDATE);"
    )
    new_check_sw = (
        "pub fn check_software_update() {\n"
        "    let opt = LocalConfig::get_option(keys::OPTION_ENABLE_CHECK_UPDATE);"
    )
    if old_check_sw in content:
        content = content.replace(old_check_sw, new_check_sw, 1)
        print("[rrremote] Enabled startup check_software_update() for RRRemote custom client.")
    elif new_check_sw in content:
        print("[rrremote] Startup check_software_update() already enabled.")
    else:
        raise RuntimeError("Failed to locate check_software_update() in src/common.rs")

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
    """Resolve & download platform installers from rrremote-update.json on GitHub Releases with SHA256."""
    if "/" not in update_repo:
        raise ValueError(f"Invalid UPDATE_REPO: {update_repo!r}, expected 'owner/repo'")
    owner, repo = update_repo.split("/", 1)

    artifact_rs = root / "src" / "updater" / "artifact.rs"
    if not artifact_rs.exists():
        raise FileNotFoundError(f"Expected {artifact_rs}")

    content = read_text(artifact_rs)
    artifact_changed = False

    if "rrremote-update.json" not in content:
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
        content = content.replace(
            "update_metadata::{UpdateArtifactQuery, UpdateMetadataRequirements, VerifiedUpdateArtifact},",
            "update_metadata::{UpdateArtifactQuery, VerifiedUpdateArtifact},",
            1,
        )
        artifact_changed = True
        print(f"[rrremote] Wired SHA256-verified in-app update manifest resolver for {update_repo}.")
    else:
        print("[rrremote] src/updater/artifact.rs already patched for rrremote-update.json.")

    # Allow downloading verified release assets from melotusme/RRRemote in get_update_download_file_from_url
    old_dl_guard = (
        '    if owner != "rustdesk"\n'
        '        || repo != "rustdesk"'
    )
    new_dl_guard = (
        f'    if !((owner == "{owner}" && repo == "{repo}") || (owner == "rustdesk" && repo == "rustdesk"))'
    )
    if f'owner == "{owner}" && repo == "{repo}"' in content:
        print(f"[rrremote] get_update_download_file_from_url already accepts {owner}/{repo}.")
    elif old_dl_guard in content:
        content = content.replace(old_dl_guard, new_dl_guard, 1)
        artifact_changed = True
        print(f"[rrremote] Allowed {owner}/{repo} asset URLs in get_update_download_file_from_url.")
    else:
        raise RuntimeError("Failed to locate get_update_download_file_from_url guard in src/updater/artifact.rs")

    if artifact_changed:
        write_text(artifact_rs, content)

    # Enable silent macOS root DMG updates and native Windows MSI updates in src/updater.rs & src/flutter_ffi.rs
    updater_rs = root / "src" / "updater.rs"
    if updater_rs.exists():
        utxt = read_text(updater_rs)
        uchanged = False
        old_root_skip = (
            "    if crate::is_custom_client() {\n"
            '        log::info!("[root-update] Custom client detected, skipping stock update.");\n'
            "        return Ok(false);\n"
            "    }\n"
        )
        if old_root_skip in utxt:
            utxt = utxt.replace(old_root_skip, "", 1)
            uchanged = True
            print("[rrremote] Enabled macOS silent root DMG auto-update in src/updater.rs.")
        old_umsi = "let update_msi = crate::platform::is_msi_installed()? && !crate::is_custom_client();"
        new_umsi = "let update_msi = crate::platform::is_msi_installed()?;"
        if old_umsi in utxt:
            utxt = utxt.replace(old_umsi, new_umsi, 1)
            uchanged = True
            print("[rrremote] Enabled native MSI update format resolution in src/updater.rs.")
        if uchanged:
            write_text(updater_rs, utxt)

    ffi_rs = root / "src" / "flutter_ffi.rs"
    if ffi_rs.exists():
        ftxt = read_text(ffi_rs)
        old_fmsi = "let update_msi = crate::platform::windows::is_msi_installed()? && !crate::is_custom_client();"
        new_fmsi = "let update_msi = crate::platform::windows::is_msi_installed()?;"
        if old_fmsi in ftxt:
            ftxt = ftxt.replace(old_fmsi, new_fmsi, 1)
            write_text(ffi_rs, ftxt)
            print("[rrremote] Enabled native MSI update format resolution in src/flutter_ffi.rs.")


def patch_default_api_server_fallback(root: Path, api_server: str) -> None:
    common_rs = root / "src" / "common.rs"
    content = read_text(common_rs)
    if api_server:
        marker = "pub fn get_api_server(api: String, custom: String) -> String {"
        if marker in content and "RRREMOTE_DEFAULT_API_SERVER" not in content:
            idx = content.index(marker)
            snippet = content[idx : idx + 1200]
            if 'return "".to_owned();' in snippet:
                patched_snippet = snippet.replace(
                    'return "".to_owned();',
                    "return hbb_common::config::RRREMOTE_DEFAULT_API_SERVER.to_owned();",
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


def patch_display_branding(root: Path, display_name: str, update_repo: str) -> None:
    if not display_name or display_name == "RustDesk":
        return

    lower_name = display_name.lower()
    repo_url = f"https://github.com/{update_repo}"

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

    # 2b. Replace remaining user-visible RustDesk literals in Rust core modules
    auth_2fa = root / "src" / "auth_2fa.rs"
    if auth_2fa.exists():
        txt = read_text(auth_2fa)
        updated = txt.replace('const ISSUER: &str = "RustDesk";', f'const ISSUER: &str = "{display_name}";')
        if updated != txt:
            write_text(auth_2fa, updated)
            print(f"[rrremote] Updated 2FA TOTP issuer to {display_name} in src/auth_2fa.rs.")

    wayland_rs = root / "src" / "server" / "wayland.rs"
    if wayland_rs.exists():
        txt = read_text(wayland_rs)
        updated = (
            txt.replace("RustDesk cannot reach", f"{display_name} cannot reach")
            .replace("that RustDesk can use it", f"that {display_name} can use it")
            .replace("RustDesk could not", f"{display_name} could not")
        )
        if updated != txt:
            write_text(wayland_rs, updated)
            print(f"[rrremote] Updated user-visible Wayland error messages to {display_name}.")

    uinput_rs = root / "src" / "server" / "uinput.rs"
    if uinput_rs.exists():
        txt = read_text(uinput_rs)
        updated = txt.replace("RustDesk UInput", f"{display_name} UInput")
        if updated != txt:
            write_text(uinput_rs, updated)
            print(f"[rrremote] Updated Linux UInput virtual device names to {display_name}.")

    client_rs = root / "src" / "client.rs"
    if client_rs.exists():
        txt = read_text(client_rs)
        updated = txt.replace(
            'pub const SCRAP_X11_REF_URL: &str = "https://rustdesk.com/docs/en/manual/linux/#x11-required";',
            f'pub const SCRAP_X11_REF_URL: &str = "{repo_url}";',
        )
        if updated != txt:
            write_text(client_rs, updated)
            print(f"[rrremote] Updated SCRAP_X11_REF_URL in src/client.rs to {repo_url}.")

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
            .replace("Copyright © 2026 Purslane Tech Pte. Ltd.", f"Copyright © 2026 {display_name}.")
        )
        if updated != txt:
            write_text(win_rc, updated)
            print(f"[rrremote] Updated Windows Runner.rc product metadata to {display_name}.")

    # 4. macOS app bundle name (RRRemote.app), Bundle ID, DisplayName, TCC usage descriptions, Menu Bar & URL scheme
    mac_bundle_id = f"com.carriez.{lower_name}"
    mac_xcconfig = root / "flutter" / "macos" / "Runner" / "Configs" / "AppInfo.xcconfig"
    if mac_xcconfig.exists():
        txt = read_text(mac_xcconfig)
        updated = txt.replace("PRODUCT_NAME = RustDesk", f"PRODUCT_NAME = {display_name}")
        updated = updated.replace(
            "PRODUCT_BUNDLE_IDENTIFIER = com.carriez.flutterHbb",
            f"PRODUCT_BUNDLE_IDENTIFIER = {mac_bundle_id}",
        )
        updated = updated.replace(
            "PRODUCT_COPYRIGHT = Copyright © 2026 Purslane Tech Pte. Ltd. All rights reserved.",
            f"PRODUCT_COPYRIGHT = Copyright © 2026 {display_name}. All rights reserved.",
        )
        if updated != txt:
            write_text(mac_xcconfig, updated)
            print(f"[rrremote] Updated macOS AppInfo.xcconfig PRODUCT_NAME & PRODUCT_BUNDLE_IDENTIFIER ({mac_bundle_id}).")

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
            "<string>com.carriez.rustdesk</string>",
            f"<string>{mac_bundle_id}</string>",
        )
        updated = updated.replace(
            "<string>rustdesk</string>",
            f"<string>{lower_name}</string>",
        )
        usage_insert = ""
        if "<key>NSLocalNetworkUsageDescription</key>" not in updated:
            usage_insert += (
                "\t<key>NSLocalNetworkUsageDescription</key>\n"
                f"\t<string>{display_name} uses local network access for LAN device discovery and direct low-latency connections.</string>\n"
            )
        if "<key>NSCameraUsageDescription</key>" not in updated:
            usage_insert += (
                "\t<key>NSCameraUsageDescription</key>\n"
                f"\t<string>{display_name} uses camera access when remote camera viewing is enabled.</string>\n"
            )
        if usage_insert:
            if "\t<key>NSPrincipalClass</key>" not in updated:
                raise RuntimeError("Failed to locate NSPrincipalClass in flutter/macos/Runner/Info.plist")
            updated = updated.replace(
                "\t<key>NSPrincipalClass</key>",
                f"{usage_insert}\t<key>NSPrincipalClass</key>",
                1,
            )
        if updated != txt:
            write_text(mac_plist, updated)
            print(f"[rrremote] Updated macOS Info.plist display name, URL scheme, bundle ID ({mac_bundle_id}) & TCC usage descriptions.")

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
        updated = (
            txt.replace("/* RustDesk.app */", f"/* {display_name}.app */")
            .replace("path = RustDesk.app;", f"path = {display_name}.app;")
            .replace(
                "PRODUCT_BUNDLE_IDENTIFIER = com.carriez.rustdesk;",
                f"PRODUCT_BUNDLE_IDENTIFIER = {mac_bundle_id};",
            )
        )
        if updated != txt:
            write_text(mac_pbxproj, updated)
            print(f"[rrremote] Updated macOS project.pbxproj product reference & bundle ID ({mac_bundle_id}).")

    # 4b. Fix macOS menu bar tray icon: use embedded transparent template res/mac-tray-dark-x2.png
    #     instead of opaque flutter_assets/assets/icon.png (which turns into a solid square blob under template rendering).
    tray_rs = root / "src" / "tray.rs"
    if tray_rs.exists():
        ttxt = read_text(tray_rs)
        old_tray_img = """    let (icon_rgba, icon_width, icon_height) = {
        let image = load_icon_from_asset()
            .unwrap_or(image::load_from_memory(icon).context("Failed to open icon path")?)
            .into_rgba8();"""
        new_tray_img = """    let (icon_rgba, icon_width, icon_height) = {
        #[cfg(target_os = "macos")]
        let image = image::load_from_memory(icon)
            .context("Failed to open icon path")?
            .into_rgba8();
        #[cfg(not(target_os = "macos"))]
        let image = load_icon_from_asset()
            .unwrap_or(image::load_from_memory(icon).context("Failed to open icon path")?)
            .into_rgba8();"""
        tchanged = False
        if new_tray_img in ttxt:
            print("[rrremote] macOS tray template icon patch already applied in src/tray.rs.")
        elif old_tray_img in ttxt:
            ttxt = ttxt.replace(old_tray_img, new_tray_img, 1)
            tchanged = True
            print("[rrremote] Patched src/tray.rs to use transparent template icon on macOS.")
        else:
            raise RuntimeError("Failed to locate tray icon loader in src/tray.rs")

        old_load_fn = "fn load_icon_from_asset() -> Option<image::DynamicImage> {"
        new_load_fn = '#[cfg(not(target_os = "macos"))]\nfn load_icon_from_asset() -> Option<image::DynamicImage> {'
        if new_load_fn not in ttxt and old_load_fn in ttxt:
            ttxt = ttxt.replace(old_load_fn, new_load_fn, 1)
            tchanged = True
        if tchanged:
            write_text(tray_rs, ttxt)

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
                .replace("URL:        https://rustdesk.com", f"URL:        {repo_url}")
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
            .replace(
                'create-dmg --volname \\"RustDesk Installer\\" --window-pos 200 120 --window-size 800 400 --icon-size 100 --app-drop-link 600 185 --icon RustDesk.app 200 190 --hide-extension RustDesk.app rustdesk.dmg ./build/macos/Build/Products/Release/RustDesk.app',
                f'create-dmg --volname \\"{display_name} Installer\\" --window-pos 200 120 --window-size 800 400 --icon-size 100 --app-drop-link 600 185 --icon {display_name}.app 200 190 --hide-extension {display_name}.app {lower_name}.dmg ./build/macos/Build/Products/Release/{display_name}.app',
            )
            .replace(
                'os.rename("rustdesk.dmg", f"../rustdesk-{version}.dmg")',
                f'os.rename("{lower_name}.dmg", f"../{lower_name}-{{version}}.dmg")',
            )
            .replace("Package: rustdesk", f"Package: {lower_name}")
            .replace("Maintainer: rustdesk <info@rustdesk.com>", f"Maintainer: {display_name}")
            .replace("Homepage: https://rustdesk.com", f"Homepage: {repo_url}")
            .replace(
                "cp ../res/rustdesk.service tmpdeb/usr/share/rustdesk/files/systemd/",
                f"cp ../res/rustdesk.service tmpdeb/usr/share/{lower_name}/files/systemd/{lower_name}.service",
            )
            .replace("tmpdeb/usr/share/rustdesk/rustdesk", f"tmpdeb/usr/share/{lower_name}/{lower_name}")
            .replace("tmpdeb/usr/share/rustdesk", f"tmpdeb/usr/share/{lower_name}")
            .replace("tmpdeb/usr/bin/rustdesk", f"tmpdeb/usr/bin/{lower_name}")
            .replace("apps/rustdesk.png", f"apps/{lower_name}.png")
            .replace("apps/rustdesk.svg", f"apps/{lower_name}.svg")
            .replace("applications/rustdesk.desktop", f"applications/{lower_name}.desktop")
            .replace("applications/rustdesk-link.desktop", f"applications/{lower_name}-link.desktop")
            .replace("dpkg-deb -b tmpdeb rustdesk.deb;", f"dpkg-deb -b tmpdeb {lower_name}.deb;")
            .replace(
                "os.rename('rustdesk.deb', '../rustdesk-%s.deb' % version)",
                f"os.rename('{lower_name}.deb', '../{lower_name}-%s.deb' % version)",
            )
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


def patch_personal_ergonomics(root: Path) -> None:
    """Apply personal-use zero-password auto-approve (key-gated) and full TUN fake-IP LAN immunity."""
    # 1. Personal zero-password auto-approve on private key-authenticated self-hosted servers:
    #    When the host has a custom server Ed25519 `key` configured (so only devices with the
    #    owner's private key can reach it via hbbs/hbbr) and approve-mode is not explicitly
    #    set to "click", immediately authorize incoming sessions without prompting for a password.
    conn_rs = root / "src" / "server" / "connection.rs"
    if not conn_rs.exists():
        raise FileNotFoundError(f"Expected {conn_rs}")
    txt = read_text(conn_rs)
    old_auth = """            if (password::approve_mode() == ApproveMode::Click && !allow_logon_screen_password)
                || password::approve_mode() == ApproveMode::Both && !password::has_valid_password()"""
    new_auth = """            if (!Config::get_option("key").is_empty() || hbb_common::config::RRREMOTE_HAS_BAKED_KEY)
                && Config::get_option("approve-mode") != "click"
            {
                if !self.send_logon_response_and_keep_alive().await {
                    return false;
                }
                self.try_start_cm(lr.my_id.clone(), lr.my_name.clone(), self.authorized);
            } else if (password::approve_mode() == ApproveMode::Click && !allow_logon_screen_password)
                || password::approve_mode() == ApproveMode::Both && !password::has_valid_password()"""
    if new_auth in txt:
        print("[rrremote] Personal key-gated auto-approve already patched in src/server/connection.rs.")
    elif old_auth in txt:
        txt = txt.replace(old_auth, new_auth, 1)
        write_text(conn_rs, txt)
        print("[rrremote] Enabled key-gated zero-password auto-approve in src/server/connection.rs.")
    else:
        raise RuntimeError("Failed to locate login approve block in src/server/connection.rs")

    # 2. Physical non-TUN LAN IPv4 resolver + test_nat_type_() local-ip-addr guard in src/common.rs:
    #    When Clash Verge / Shadowrocket / sing-box TUN mode routes hbbs over utun, socket.local_addr()
    #    carries an RFC 2544 TUN fake-IP (octets 198, 18/19). Resolve a physical private LAN IPv4 via
    #    default_net::get_interfaces() instead of polluting local-ip-addr.
    common_rs = root / "src" / "common.rs"
    if not common_rs.exists():
        raise FileNotFoundError(f"Expected {common_rs}")
    ctxt = read_text(common_rs)
    cchanged = False

    lan_helper = """#[cfg(not(target_os = "ios"))]
pub fn is_virtual_or_tun_interface(interface: &default_net::Interface) -> bool {
    if matches!(
        interface.if_type,
        default_net::interface::InterfaceType::Loopback
            | default_net::interface::InterfaceType::Tunnel
            | default_net::interface::InterfaceType::Ppp
    ) {
        return true;
    }
    #[cfg(unix)]
    {
        // POSIX IFF_UP (0x1), IFF_LOOPBACK (0x8), IFF_POINTOPOINT (0x10)
        if (interface.flags & 0x1) == 0
            || (interface.flags & 0x8) != 0
            || (interface.flags & 0x10) != 0
        {
            return true;
        }
    }
    #[cfg(target_os = "macos")]
    {
        // Darwin IFF_RUNNING (0x40): skip configured-but-inactive interfaces
        if (interface.flags & 0x40) == 0 {
            return true;
        }
    }
    let lname = interface.name.to_ascii_lowercase();
    lname.starts_with("utun")
        || lname.starts_with("tun")
        || lname.starts_with("tap")
        || lname.starts_with("wg")
        || lname.starts_with("tailscale")
        || lname.starts_with("docker")
        || lname.starts_with("veth")
        || lname.starts_with("br-")
        || lname.starts_with("bridge")
        || lname.starts_with("vmenet")
        || lname.starts_with("vmnet")
        || lname.starts_with("vboxnet")
        || lname.starts_with("feth")
        || lname.starts_with("ap1")
        || lname.starts_with("awdl")
        || lname.starts_with("llw")
        || lname.starts_with("anpi")
        || lname.starts_with("gif")
        || lname.starts_with("stf")
        || lname.starts_with("pdp_ip")
        || lname.starts_with("ipsec")
        || lname.starts_with("lo")
}

pub fn resolve_non_tun_lan_ipv4() -> Option<std::net::Ipv4Addr> {
    #[cfg(target_os = "ios")]
    {
        None
    }
    #[cfg(not(target_os = "ios"))]
    {
        let mut fallback: Option<std::net::Ipv4Addr> = None;
        for interface in default_net::get_interfaces() {
            if is_virtual_or_tun_interface(&interface) {
                continue;
            }
            let has_hw_mac = interface
                .mac_addr
                .as_ref()
                .map(|m| {
                    let s = m.address();
                    !s.is_empty() && s.bytes().any(|b| b != b'0' && b != b':' && b != b'-')
                })
                .unwrap_or(false);
            for ipv4 in &interface.ipv4 {
                let addr = ipv4.addr;
                if addr.is_loopback()
                    || addr.is_unspecified()
                    || addr.is_link_local()
                    || hbb_common::config::is_tun_fake_ip(&std::net::IpAddr::V4(addr))
                {
                    continue;
                }
                if addr.is_private() {
                    if has_hw_mac {
                        return Some(addr);
                    }
                    if fallback.is_none() {
                        fallback = Some(addr);
                    }
                }
            }
        }
        fallback
    }
}

#[tokio::main(flavor = "current_thread")]
async fn test_nat_type_() -> ResultType<bool> {"""
    nat_marker = '#[tokio::main(flavor = "current_thread")]\nasync fn test_nat_type_() -> ResultType<bool> {'
    if "pub fn resolve_non_tun_lan_ipv4()" not in ctxt:
        if nat_marker not in ctxt:
            raise RuntimeError("Failed to locate test_nat_type_() in src/common.rs")
        ctxt = ctxt.replace(nat_marker, lan_helper, 1)
        cchanged = True
        print("[rrremote] Added is_virtual_or_tun_interface() & resolve_non_tun_lan_ipv4() in src/common.rs.")

    old_nat_ip = """        if i == 0 {
            // reuse the local addr is required for nat test
            local_addr = Some(socket.local_addr());
            Config::set_option(
                "local-ip-addr".to_owned(),
                socket.local_addr().ip().to_string(),
            );
        }"""
    new_nat_ip = """        if i == 0 {
            // reuse the local addr is required for nat test
            local_addr = Some(socket.local_addr());
            let detected_ip = socket.local_addr().ip();
            if hbb_common::config::is_tun_fake_ip(&detected_ip) {
                if let Some(lan_v4) = resolve_non_tun_lan_ipv4() {
                    Config::set_option("local-ip-addr".to_owned(), lan_v4.to_string());
                } else {
                    Config::set_option("local-ip-addr".to_owned(), String::new());
                }
            } else {
                Config::set_option("local-ip-addr".to_owned(), detected_ip.to_string());
            }
        }"""
    if "if hbb_common::config::is_tun_fake_ip(&detected_ip)" in ctxt:
        print("[rrremote] test_nat_type_() TUN fake-IP guard already patched in src/common.rs.")
    elif old_nat_ip in ctxt:
        ctxt = ctxt.replace(old_nat_ip, new_nat_ip, 1)
        cchanged = True
        print("[rrremote] Protected test_nat_type_() local-ip-addr from RFC 2544 TUN fake-IPs.")
    else:
        raise RuntimeError("Failed to locate test_nat_type_() local-ip-addr block in src/common.rs")

    if cchanged:
        write_text(common_rs, ctxt)

    # 3. TUN fake-IP LAN direct listener fallback in src/rendezvous_mediator.rs (handle_intranet_):
    #    When hbbs is routed via TUN, bind a direct LAN TCP listener on our physical LAN IPv4
    #    so same-LAN devices still connect directly in <5ms instead of timing out on TUN IP.
    med_rs = root / "src" / "rendezvous_mediator.rs"
    if not med_rs.exists():
        raise FileNotFoundError(f"Expected {med_rs}")
    mtxt = read_text(med_rs)
    old_intranet = """        let local_addr = socket.local_addr();
        // we saw invalid local_addr while using proxy, local_addr.ip() == "::1"
        let local_addr: SocketAddr =
            format!("{}:{}", local_addr.ip(), local_addr.port()).parse()?;"""
    new_intranet = """        let local_addr = socket.local_addr();
        if peer_addr.ip().is_loopback() || local_addr.ip().is_loopback() {
            drop(slot);
            bail!(
                "Skip intranet listen on loopback/co-located proxy route (local={}, peer={})",
                local_addr,
                peer_addr
            );
        }
        if hbb_common::config::is_tun_fake_ip(&local_addr.ip()) {
            let Some(lan_v4) = crate::common::resolve_non_tun_lan_ipv4() else {
                bail!("Skip intranet listen on TUN fake-IP {}", local_addr);
            };
            let lan_bind = SocketAddr::new(std::net::IpAddr::V4(lan_v4), 0);
            let listener = hbb_common::tcp::new_listener(lan_bind, false).await?;
            let lan_addr = listener.local_addr()?;
            let mut msg_out = Message::new();
            msg_out.set_local_addr(LocalAddr {
                id: Config::get_id(),
                socket_addr: AddrMangle::encode(peer_addr).into(),
                local_addr: AddrMangle::encode(lan_addr).into(),
                relay_server,
                version: crate::VERSION.to_owned(),
                socket_addr_v6,
                ..Default::default()
            });
            let bytes = msg_out.write_to_bytes()?;
            socket.send_raw(bytes).await?;
            drop(socket);
            if let Ok(Ok((stream, addr))) =
                hbb_common::timeout(3_000, listener.accept()).await
            {
                drop(slot);
                accept_punched_connection(server, stream, addr, meta).await;
            } else {
                drop(slot);
            }
            return Ok(());
        }
        // we saw invalid local_addr while using proxy, local_addr.ip() == "::1"
        let local_addr: SocketAddr =
            format!("{}:{}", local_addr.ip(), local_addr.port()).parse()?;"""
    if "crate::common::resolve_non_tun_lan_ipv4()" in mtxt:
        print("[rrremote] TUN fake-IP LAN listener fallback already patched in src/rendezvous_mediator.rs.")
    elif old_intranet in mtxt:
        mtxt = mtxt.replace(old_intranet, new_intranet, 1)
        write_text(med_rs, mtxt)
        print("[rrremote] Added TUN fake-IP physical LAN listener fallback in src/rendezvous_mediator.rs.")
    else:
        raise RuntimeError("Failed to locate handle_intranet_ local_addr in src/rendezvous_mediator.rs")

    # 4. Controller outbound TCP source-IP guard in src/client.rs:
    #    When the controller's hbbs socket used a TUN fake-IP, do not bind outbound LAN/TCP dials
    #    to the TUN fake-IP (let the OS route via the physical LAN NIC).
    client_rs = root / "src" / "client.rs"
    if not client_rs.exists():
        raise FileNotFoundError(f"Expected {client_rs}")
    cltxt = read_text(client_rs)
    old_dial = (
        "        if allow_tcp_punch {\n"
        "            let fut = connect_tcp_local(peer, Some(local_addr), connect_timeout);"
    )
    new_dial = (
        "        if allow_tcp_punch {\n"
        "            let bind_local = if hbb_common::config::is_tun_fake_ip(&local_addr.ip()) {\n"
        "                None\n"
        "            } else {\n"
        "                Some(local_addr)\n"
        "            };\n"
        "            let fut = connect_tcp_local(peer, bind_local, connect_timeout);"
    )
    if "let bind_local = if hbb_common::config::is_tun_fake_ip(&local_addr.ip())" in cltxt:
        print("[rrremote] Controller outbound TUN source-IP guard already patched in src/client.rs.")
    elif old_dial in cltxt:
        cltxt = cltxt.replace(old_dial, new_dial, 1)
        write_text(client_rs, cltxt)
        print("[rrremote] Guarded controller outbound TCP dial against binding TUN fake-IP in src/client.rs.")
    else:
        raise RuntimeError("Failed to locate allow_tcp_punch connect_tcp_local in src/client.rs")

    # 5. Wire virtual/TUN interface & RFC 2544 fake-IP filtering into src/lan.rs so LAN Discovery
    #    and Wake-on-LAN broadcast cleanly over physical NICs (e.g. en0) instead of failing with
    #    AddrNotAvailable on macOS utun / bridge / VM interfaces.
    lan_rs = root / "src" / "lan.rs"
    if not lan_rs.exists():
        raise FileNotFoundError(f"Expected {lan_rs}")
    ltxt = read_text(lan_rs)
    lchanged = False

    old_lan_bcast = """    #[cfg(not(any(target_os = "ios")))]
    for interface in default_net::get_interfaces() {
        for ipv4 in &interface.ipv4 {
            ipv4s.push(ipv4.addr.clone());
        }
    }"""
    new_lan_bcast = """    #[cfg(not(any(target_os = "ios")))]
    for interface in default_net::get_interfaces() {
        if crate::common::is_virtual_or_tun_interface(&interface) {
            continue;
        }
        for ipv4 in &interface.ipv4 {
            let addr = ipv4.addr;
            if addr.is_loopback()
                || addr.is_unspecified()
                || addr.is_link_local()
                || hbb_common::config::is_tun_fake_ip(&std::net::IpAddr::V4(addr))
            {
                continue;
            }
            ipv4s.push(addr);
        }
    }"""
    if "crate::common::is_virtual_or_tun_interface(&interface)" in ltxt:
        print("[rrremote] LAN discovery virtual/TUN interface filter already patched in src/lan.rs.")
    elif old_lan_bcast in ltxt:
        ltxt = ltxt.replace(old_lan_bcast, new_lan_bcast, 1)
        lchanged = True
        print("[rrremote] Filtered virtual/TUN interfaces & fake-IPs in src/lan.rs::create_broadcast_sockets().")
    else:
        raise RuntimeError("Failed to locate create_broadcast_sockets loop in src/lan.rs")

    old_lan_peer_ip = """    match socket.local_addr() {
        Ok(addr) => return Some(addr.ip()),
        Err(_) => return None,
    };"""
    new_lan_peer_ip = """    match socket.local_addr() {
        Ok(addr) => {
            let ip = addr.ip();
            if hbb_common::config::is_tun_fake_ip(&ip) {
                return crate::common::resolve_non_tun_lan_ipv4().map(IpAddr::V4);
            }
            return Some(ip);
        }
        Err(_) => return None,
    };"""
    if "crate::common::resolve_non_tun_lan_ipv4().map(IpAddr::V4)" in ltxt:
        print("[rrremote] LAN get_ipaddr_by_peer TUN fake-IP fallback already patched in src/lan.rs.")
    elif old_lan_peer_ip in ltxt:
        ltxt = ltxt.replace(old_lan_peer_ip, new_lan_peer_ip, 1)
        lchanged = True
        print("[rrremote] Added TUN fake-IP fallback in src/lan.rs::get_ipaddr_by_peer().")
    else:
        raise RuntimeError("Failed to locate get_ipaddr_by_peer local_addr in src/lan.rs")

    old_wol_loop = """                    for interface in &interfaces {
                        for ipv4 in &interface.ipv4 {"""
    new_wol_loop = """                    for interface in &interfaces {
                        #[cfg(not(target_os = "ios"))]
                        if crate::common::is_virtual_or_tun_interface(interface) {
                            continue;
                        }
                        for ipv4 in &interface.ipv4 {
                            if hbb_common::config::is_tun_fake_ip(&IpAddr::V4(ipv4.addr)) {
                                continue;
                            }"""
    if "if crate::common::is_virtual_or_tun_interface(interface)" in ltxt:
        print("[rrremote] LAN send_wol virtual/TUN filter already patched in src/lan.rs.")
    elif old_wol_loop in ltxt:
        ltxt = ltxt.replace(old_wol_loop, new_wol_loop, 1)
        lchanged = True
        print("[rrremote] Filtered virtual/TUN interfaces in src/lan.rs::send_wol().")

    if lchanged:
        write_text(lan_rs, ltxt)


RR_MACOS_PERMISSION_SWIFT = r'''
// MARK: - RRRemote Snug-Style Floating Permission Helper & Stale-TCC Self-Healing

enum RrPermissionPane: String, CaseIterable {
    case screen = "screen"
    case accessibility = "accessibility"
    case input = "input"

    var tccService: String {
        switch self {
        case .screen:
            return "ScreenCapture"
        case .accessibility:
            return "Accessibility"
        case .input:
            return "ListenEvent"
        }
    }

    var settingsURL: URL {
        switch self {
        case .screen:
            return URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture")!
        case .accessibility:
            return URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility")!
        case .input:
            return URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_ListenEvent")!
        }
    }

    func settingsTitle(isZh: Bool) -> String {
        let isTahoeOrLater = ProcessInfo.processInfo.operatingSystemVersion.majorVersion >= 26
        switch self {
        case .screen:
            return isZh ? "录屏与系统录音" : "Screen & System Audio Recording"
        case .accessibility:
            if isTahoeOrLater {
                return isZh ? "设备控制和数据访问" : "Device Control & Data Access"
            }
            return isZh ? "辅助功能" : "Accessibility"
        case .input:
            return isZh ? "输入监控" : "Input Monitoring"
        }
    }

    func stepLabel(index: Int, isZh: Bool, granted: Bool) -> String {
        let isTahoeOrLater = ProcessInfo.processInfo.operatingSystemVersion.majorVersion >= 26
        let badge = granted ? "✓" : "\(index)"
        switch self {
        case .screen:
            return isZh ? "\(badge) 屏幕录制" : "\(badge) Screen"
        case .accessibility:
            if isTahoeOrLater {
                return isZh ? "\(badge) 设备控制" : "\(badge) Device Control"
            }
            return isZh ? "\(badge) 辅助功能" : "\(badge) Accessibility"
        case .input:
            return isZh ? "\(badge) 输入监控" : "\(badge) Input"
        }
    }
}

final class RrNonActivatingButton: NSButton {
    override func acceptsFirstMouse(for event: NSEvent?) -> Bool {
        return true
    }
}

final class RrAppPasteboardWriter: NSObject, NSPasteboardWriting {
    private let appURL: URL

    init(url: URL) {
        self.appURL = url.standardizedFileURL
        super.init()
    }

    func writableTypes(for pasteboard: NSPasteboard) -> [NSPasteboard.PasteboardType] {
        return [
            .fileURL,
            .URL,
            NSPasteboard.PasteboardType("NSFilenamesPboardType"),
            NSPasteboard.PasteboardType("com.apple.pasteboard.promised-file-url"),
            .string
        ]
    }

    func pasteboardPropertyList(forType type: NSPasteboard.PasteboardType) -> Any? {
        switch type {
        case .fileURL, .URL, NSPasteboard.PasteboardType("com.apple.pasteboard.promised-file-url"):
            return appURL.absoluteString
        case NSPasteboard.PasteboardType("NSFilenamesPboardType"):
            return [appURL.path]
        case .string:
            return appURL.path
        default:
            return nil
        }
    }
}

final class RrAppDragSourceView: NSView, NSDraggingSource {
    private var appURL: URL
    private let iconView = NSImageView()
    private let nameLabel = NSTextField(labelWithString: "RRRemote.app")
    private let subLabel = NSTextField(labelWithString: "")
    private let hintBadge = NSTextField(labelWithString: "")
    private let hintContainer = NSView()
    private var mouseDownPoint: NSPoint?
    private var isDraggingNow = false

    var onDragStateChange: ((Bool) -> Void)?

    init(appURL: URL, isZh: Bool) {
        self.appURL = appURL
        super.init(frame: .zero)
        wantsLayer = true
        layer?.cornerRadius = 12
        layer?.masksToBounds = true
        layer?.backgroundColor = NSColor.white.withAlphaComponent(0.09).cgColor
        layer?.borderWidth = 1
        layer?.borderColor = NSColor.white.withAlphaComponent(0.20).cgColor

        iconView.translatesAutoresizingMaskIntoConstraints = false
        iconView.imageScaling = .scaleProportionallyUpOrDown
        addSubview(iconView)

        nameLabel.font = NSFont.systemFont(ofSize: 14, weight: .semibold)
        nameLabel.textColor = NSColor.white
        nameLabel.lineBreakMode = .byTruncatingTail

        subLabel.font = NSFont.systemFont(ofSize: 11, weight: .regular)
        subLabel.textColor = NSColor.white.withAlphaComponent(0.68)
        subLabel.lineBreakMode = .byTruncatingMiddle

        let textStack = NSStackView(views: [nameLabel, subLabel])
        textStack.orientation = .vertical
        textStack.alignment = .leading
        textStack.spacing = 2
        textStack.translatesAutoresizingMaskIntoConstraints = false
        addSubview(textStack)

        hintContainer.wantsLayer = true
        hintContainer.layer?.cornerRadius = 8
        hintContainer.layer?.backgroundColor = NSColor.systemBlue.withAlphaComponent(0.32).cgColor
        hintContainer.layer?.borderWidth = 1
        hintContainer.layer?.borderColor = NSColor.systemBlue.withAlphaComponent(0.55).cgColor
        hintContainer.translatesAutoresizingMaskIntoConstraints = false
        addSubview(hintContainer)

        hintBadge.font = NSFont.systemFont(ofSize: 12, weight: .medium)
        hintBadge.textColor = NSColor.white
        hintBadge.translatesAutoresizingMaskIntoConstraints = false
        hintContainer.addSubview(hintBadge)

        NSLayoutConstraint.activate([
            iconView.leadingAnchor.constraint(equalTo: leadingAnchor, constant: 10),
            iconView.centerYAnchor.constraint(equalTo: centerYAnchor),
            iconView.widthAnchor.constraint(equalToConstant: 40),
            iconView.heightAnchor.constraint(equalToConstant: 40),

            textStack.leadingAnchor.constraint(equalTo: iconView.trailingAnchor, constant: 10),
            textStack.centerYAnchor.constraint(equalTo: centerYAnchor),
            textStack.trailingAnchor.constraint(lessThanOrEqualTo: hintContainer.leadingAnchor, constant: -8),

            hintContainer.trailingAnchor.constraint(equalTo: trailingAnchor, constant: -10),
            hintContainer.centerYAnchor.constraint(equalTo: centerYAnchor),

            hintBadge.leadingAnchor.constraint(equalTo: hintContainer.leadingAnchor, constant: 10),
            hintBadge.trailingAnchor.constraint(equalTo: hintContainer.trailingAnchor, constant: -10),
            hintBadge.topAnchor.constraint(equalTo: hintContainer.topAnchor, constant: 5),
            hintBadge.bottomAnchor.constraint(equalTo: hintContainer.bottomAnchor, constant: -5)
        ])

        refresh(appURL: appURL, isZh: isZh)
    }

    required init?(coder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }

    func refresh(appURL: URL, isZh: Bool) {
        self.appURL = appURL
        let icon = NSWorkspace.shared.icon(forFile: appURL.path)
        icon.size = NSSize(width: 40, height: 40)
        iconView.image = icon
        let bundleName = appURL.lastPathComponent.isEmpty ? "RRRemote.app" : appURL.lastPathComponent
        nameLabel.stringValue = bundleName
        subLabel.stringValue = isZh
            ? "按住此卡片直接拖入上方系统设置列表"
            : "Hold & drag this card into the System Settings list above"
        hintBadge.stringValue = isZh ? "🤚 拖到上方列表" : "🤚 Drag to list"
    }

    override func acceptsFirstMouse(for event: NSEvent?) -> Bool {
        return true
    }

    override var mouseDownCanMoveWindow: Bool {
        return false
    }

    override func hitTest(_ point: NSPoint) -> NSView? {
        return bounds.contains(point) ? self : nil
    }

    override func mouseDown(with event: NSEvent) {
        mouseDownPoint = convert(event.locationInWindow, from: nil)
        isDraggingNow = false
        layer?.backgroundColor = NSColor.white.withAlphaComponent(0.15).cgColor
    }

    override func mouseDragged(with event: NSEvent) {
        guard !isDraggingNow, let start = mouseDownPoint else { return }
        let current = convert(event.locationInWindow, from: nil)
        let distance = hypot(current.x - start.x, current.y - start.y)
        guard distance > 3 else { return }

        isDraggingNow = true
        let writer = RrAppPasteboardWriter(url: appURL)
        let draggingItem = NSDraggingItem(pasteboardWriter: writer)
        let dragIcon = NSWorkspace.shared.icon(forFile: appURL.path)
        dragIcon.size = NSSize(width: 52, height: 52)
        let dragFrame = NSRect(x: current.x - 26, y: current.y - 26, width: 52, height: 52)
        draggingItem.setDraggingFrame(dragFrame, contents: dragIcon)

        let session = beginDraggingSession(with: [draggingItem], event: event, source: self)
        session.animatesToStartingPositionsOnCancelOrFail = true
        session.draggingFormation = .none
    }

    override func mouseUp(with event: NSEvent) {
        mouseDownPoint = nil
        isDraggingNow = false
        layer?.backgroundColor = NSColor.white.withAlphaComponent(0.09).cgColor
    }

    func draggingSession(_ session: NSDraggingSession, sourceOperationMaskFor context: NSDraggingContext) -> NSDragOperation {
        return .copy
    }

    func ignoreModifierKeys(for session: NSDraggingSession) -> Bool {
        return true
    }

    func draggingSession(_ session: NSDraggingSession, willBeginAt screenPoint: NSPoint) {
        onDragStateChange?(true)
    }

    func draggingSession(_ session: NSDraggingSession, endedAt screenPoint: NSPoint, operation: NSDragOperation) {
        onDragStateChange?(false)
        mouseDownPoint = nil
        isDraggingNow = false
        layer?.backgroundColor = NSColor.white.withAlphaComponent(0.09).cgColor
    }
}

final class RrFloatingDropPanel: NSPanel {
    private weak var guideController: RrPermissionGuideController?
    private let effectView = NSVisualEffectView()
    private let titleLabel = NSTextField(wrappingLabelWithString: "")
    private let resetButton = RrNonActivatingButton(title: "", target: nil, action: nil)
    private let finderButton = RrNonActivatingButton(title: "Finder", target: nil, action: nil)
    private let closeButton = RrNonActivatingButton(title: "✕", target: nil, action: nil)
    private var stepButtons: [RrPermissionPane: RrNonActivatingButton] = [:]
    private let dragCardView: RrAppDragSourceView
    private let restartButton = RrNonActivatingButton(title: "", target: nil, action: nil)

    private let baseHeight: CGFloat = 166
    private let expandedRestartHeight: CGFloat = 208
    private var currentPanelWidth: CGFloat = 480

    init(controller: RrPermissionGuideController, appURL: URL, isZh: Bool) {
        self.guideController = controller
        self.dragCardView = RrAppDragSourceView(appURL: appURL, isZh: isZh)
        super.init(
            contentRect: NSRect(x: 0, y: 0, width: 480, height: 166),
            styleMask: [.borderless, .nonactivatingPanel],
            backing: .buffered,
            defer: false
        )

        level = .floating
        collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        hidesOnDeactivate = false
        isReleasedWhenClosed = false
        isOpaque = false
        backgroundColor = .clear
        hasShadow = true
        isMovableByWindowBackground = false

        effectView.appearance = NSAppearance(named: .darkAqua)
        effectView.material = .hudWindow
        effectView.blendingMode = .behindWindow
        effectView.state = .active
        effectView.wantsLayer = true
        effectView.layer?.cornerRadius = 16
        effectView.layer?.masksToBounds = true
        effectView.layer?.borderWidth = 1
        effectView.layer?.borderColor = NSColor.white.withAlphaComponent(0.18).cgColor
        contentView = effectView

        setupUI(isZh: isZh)

        dragCardView.onDragStateChange = { [weak self] dragging in
            self?.setDraggingPassthrough(dragging)
            if !dragging {
                self?.guideController?.schedulePostDropPoll()
            }
        }
    }

    override var canBecomeKey: Bool {
        return false
    }

    override var canBecomeMain: Bool {
        return false
    }

    override func sendEvent(_ event: NSEvent) {
        if event.type == .leftMouseDown || event.type == .rightMouseDown {
            guideController?.keepSystemSettingsVisible()
        }
        super.sendEvent(event)
    }

    private func styleHeaderButton(_ btn: RrNonActivatingButton, title: String, bgAlpha: CGFloat = 0.12) {
        btn.isBordered = false
        btn.wantsLayer = true
        btn.layer?.cornerRadius = 6
        btn.layer?.backgroundColor = NSColor.white.withAlphaComponent(bgAlpha).cgColor
        btn.layer?.borderWidth = 1
        btn.layer?.borderColor = NSColor.white.withAlphaComponent(0.16).cgColor
        let attr = NSAttributedString(
            string: title,
            attributes: [
                .font: NSFont.systemFont(ofSize: 11, weight: .medium),
                .foregroundColor: NSColor.white.withAlphaComponent(0.92)
            ]
        )
        btn.attributedTitle = attr
    }

    private func setupUI(isZh: Bool) {
        titleLabel.font = NSFont.systemFont(ofSize: 12, weight: .semibold)
        titleLabel.textColor = NSColor.white
        titleLabel.maximumNumberOfLines = 2
        titleLabel.cell?.truncatesLastVisibleLine = true
        titleLabel.setContentCompressionResistancePriority(.defaultLow, for: .horizontal)

        resetButton.target = self
        resetButton.action = #selector(onTapResetItem)
        finderButton.target = self
        finderButton.action = #selector(onTapFinder)
        closeButton.target = self
        closeButton.action = #selector(onTapClose)

        styleHeaderButton(resetButton, title: isZh ? "↻ 重置此项" : "↻ Reset")
        styleHeaderButton(finderButton, title: "Finder")
        styleHeaderButton(closeButton, title: "✕", bgAlpha: 0.10)

        NSLayoutConstraint.activate([
            resetButton.heightAnchor.constraint(equalToConstant: 24),
            resetButton.widthAnchor.constraint(greaterThanOrEqualToConstant: isZh ? 74 : 64),
            finderButton.heightAnchor.constraint(equalToConstant: 24),
            finderButton.widthAnchor.constraint(greaterThanOrEqualToConstant: 52),
            closeButton.heightAnchor.constraint(equalToConstant: 24),
            closeButton.widthAnchor.constraint(equalToConstant: 26)
        ])

        let actionsStack = NSStackView(views: [resetButton, finderButton, closeButton])
        actionsStack.orientation = .horizontal
        actionsStack.spacing = 5
        actionsStack.alignment = .centerY
        actionsStack.setContentCompressionResistancePriority(.required, for: .horizontal)
        actionsStack.setContentHuggingPriority(.required, for: .horizontal)

        let headerRow = NSStackView(views: [titleLabel, actionsStack])
        headerRow.orientation = .horizontal
        headerRow.alignment = .top
        headerRow.spacing = 8

        var pillViews: [NSView] = []
        for (idx, pane) in RrPermissionPane.allCases.enumerated() {
            let pill = RrNonActivatingButton(title: "", target: self, action: #selector(onTapStepPill(_:)))
            pill.tag = idx
            pill.isBordered = false
            pill.wantsLayer = true
            pill.layer?.cornerRadius = 7
            pill.layer?.borderWidth = 1
            pill.translatesAutoresizingMaskIntoConstraints = false
            pill.heightAnchor.constraint(equalToConstant: 26).isActive = true
            stepButtons[pane] = pill
            pillViews.append(pill)
        }

        let pillsRow = NSStackView(views: pillViews)
        pillsRow.orientation = .horizontal
        pillsRow.distribution = .fillEqually
        pillsRow.spacing = 6

        dragCardView.translatesAutoresizingMaskIntoConstraints = false
        dragCardView.heightAnchor.constraint(equalToConstant: 56).isActive = true

        restartButton.target = self
        restartButton.action = #selector(onTapRestart)
        restartButton.isBordered = false
        restartButton.wantsLayer = true
        restartButton.layer?.cornerRadius = 8
        restartButton.layer?.backgroundColor = NSColor.systemGreen.withAlphaComponent(0.88).cgColor
        restartButton.translatesAutoresizingMaskIntoConstraints = false
        restartButton.heightAnchor.constraint(equalToConstant: 34).isActive = true
        restartButton.isHidden = true

        let mainStack = NSStackView(views: [headerRow, pillsRow, dragCardView, restartButton])
        mainStack.orientation = .vertical
        mainStack.alignment = .width
        mainStack.spacing = 8
        mainStack.translatesAutoresizingMaskIntoConstraints = false
        effectView.addSubview(mainStack)

        NSLayoutConstraint.activate([
            mainStack.leadingAnchor.constraint(equalTo: effectView.leadingAnchor, constant: 12),
            mainStack.trailingAnchor.constraint(equalTo: effectView.trailingAnchor, constant: -12),
            mainStack.topAnchor.constraint(equalTo: effectView.topAnchor, constant: 10),
            mainStack.bottomAnchor.constraint(lessThanOrEqualTo: effectView.bottomAnchor, constant: -10)
        ])
    }

    func updateContent(
        activePane: RrPermissionPane,
        grants: [RrPermissionPane: Bool],
        showRestartCTA: Bool,
        appURL: URL,
        isZh: Bool
    ) {
        let paneTitle = activePane.settingsTitle(isZh: isZh)
        if isZh {
            titleLabel.stringValue = "↑ 将 RRRemote.app 拖到上方列表中以允许「\(paneTitle)」（如已在列表中直接打开开关）"
        } else {
            titleLabel.stringValue = "↑ Drag RRRemote.app into the list above to allow \"\(paneTitle)\" (or toggle ON if listed)"
        }

        styleHeaderButton(resetButton, title: isZh ? "↻ 重置此项" : "↻ Reset")
        dragCardView.refresh(appURL: appURL, isZh: isZh)

        let pStyle = NSMutableParagraphStyle()
        pStyle.alignment = .center

        for (idx, pane) in RrPermissionPane.allCases.enumerated() {
            guard let pill = stepButtons[pane] else { continue }
            let granted = grants[pane] ?? false
            let isCurrent = (pane == activePane)
            let label = pane.stepLabel(index: idx + 1, isZh: isZh, granted: granted)

            let fgColor: NSColor
            if granted {
                pill.layer?.backgroundColor = NSColor.systemGreen.withAlphaComponent(isCurrent ? 0.30 : 0.20).cgColor
                pill.layer?.borderColor = NSColor.systemGreen.withAlphaComponent(0.70).cgColor
                fgColor = NSColor.white
            } else if isCurrent {
                pill.layer?.backgroundColor = NSColor.systemBlue.withAlphaComponent(0.32).cgColor
                pill.layer?.borderColor = NSColor.systemBlue.withAlphaComponent(0.80).cgColor
                fgColor = NSColor.white
            } else {
                pill.layer?.backgroundColor = NSColor.white.withAlphaComponent(0.07).cgColor
                pill.layer?.borderColor = NSColor.white.withAlphaComponent(0.16).cgColor
                fgColor = NSColor.white.withAlphaComponent(0.75)
            }

            pill.attributedTitle = NSAttributedString(
                string: label,
                attributes: [
                    .font: NSFont.systemFont(ofSize: 11.5, weight: isCurrent ? .semibold : .medium),
                    .foregroundColor: fgColor,
                    .paragraphStyle: pStyle
                ]
            )
        }

        let restartChanged = (restartButton.isHidden == showRestartCTA)
        restartButton.isHidden = !showRestartCTA
        let restartText = isZh
            ? "✓ 权限已开启 — 点击立即重启 RRRemote 生效"
            : "✓ Permissions enabled — Click to restart RRRemote now"
        restartButton.attributedTitle = NSAttributedString(
            string: restartText,
            attributes: [
                .font: NSFont.systemFont(ofSize: 12.5, weight: .semibold),
                .foregroundColor: NSColor.white,
                .paragraphStyle: pStyle
            ]
        )

        if restartChanged {
            let desiredHeight = desiredPanelHeight
            var f = frame
            f.origin.y -= (desiredHeight - f.height)
            f.size.height = desiredHeight
            setFrame(f, display: true)
        }
        effectView.layoutSubtreeIfNeeded()
    }

    var desiredPanelHeight: CGFloat {
        return restartButton.isHidden ? baseHeight : expandedRestartHeight
    }

    func setDraggingPassthrough(_ isDragging: Bool) {
        ignoresMouseEvents = isDragging
        alphaValue = isDragging ? 0.72 : 1.0
        if !isDragging {
            orderFrontRegardless()
        }
    }

    func placeWaitingOnMainScreen() {
        let visible = NSScreen.main?.visibleFrame ?? NSRect(x: 100, y: 100, width: 1280, height: 800)
        let width = min(480, max(360, visible.width - 24))
        let height = desiredPanelHeight
        currentPanelWidth = width
        let x = visible.midX - (width * 0.5)
        let y = max(visible.minY + 28, visible.minY + (visible.height * 0.14))
        setFrame(NSRect(x: x, y: y, width: width, height: height), display: true)
        effectView.layoutSubtreeIfNeeded()
        orderFrontRegardless()
    }

    func snap(to settingsFrame: CGRect) {
        let screenVisible = NSScreen.screens
            .first(where: { $0.frame.intersects(settingsFrame) })?
            .visibleFrame
            ?? NSScreen.main?.visibleFrame
            ?? settingsFrame

        let sidebarOffset: CGFloat = 220
        let rawWidth = max(420, settingsFrame.width - sidebarOffset)
        let width = min(rawWidth, max(360, screenVisible.width - 16))
        let height = desiredPanelHeight
        currentPanelWidth = width

        var x = settingsFrame.minX + sidebarOffset
        var y = settingsFrame.minY - height + 8

        let minX = screenVisible.minX + 8
        let maxX = max(minX, screenVisible.maxX - width - 8)
        let minY = screenVisible.minY + 8
        let maxY = max(minY, screenVisible.maxY - height - 8)
        x = min(max(x, minX), maxX)
        y = min(max(y, minY), maxY)

        let target = NSRect(x: x, y: y, width: width, height: height)
        if abs(frame.origin.x - target.origin.x) > 0.5
            || abs(frame.origin.y - target.origin.y) > 0.5
            || abs(frame.width - target.width) > 0.5
            || abs(frame.height - target.height) > 0.5
        {
            setFrame(target, display: true)
            effectView.layoutSubtreeIfNeeded()
        }
        if !ignoresMouseEvents {
            orderFrontRegardless()
        }
    }

    @objc private func onTapStepPill(_ sender: NSButton) {
        let all = RrPermissionPane.allCases
        guard sender.tag >= 0 && sender.tag < all.count else { return }
        guideController?.selectPaneFromPill(all[sender.tag])
    }

    @objc private func onTapResetItem() {
        guideController?.resetCurrentPaneAndReopen()
    }

    @objc private func onTapFinder() {
        guard let url = guideController?.resolvedAppBundleURL() else { return }
        NSWorkspace.shared.activateFileViewerSelecting([url])
    }

    @objc private func onTapClose() {
        guideController?.closeGuidePanel()
    }

    @objc private func onTapRestart() {
        guideController?.relaunchApplication()
    }
}

final class RrPermissionGuideController {
    static let shared = RrPermissionGuideController()

    private let settingsBundleId = "com.apple.systempreferences"
    private var panel: RrFloatingDropPanel?
    private var windowTrackTimer: Timer?
    private var permissionPollTimer: Timer?
    private var activePane: RrPermissionPane = .accessibility
    private var openedPanesInSession = Set<RrPermissionPane>()
    private var lastKnownGrants: [RrPermissionPane: Bool] = [:]
    private var sessionNewlyGrantedScreenOrInput = false
    private var hasSeenSettingsWindow = false
    private var consecutiveWindowMisses = 0
    private var trackingStartedAt: TimeInterval = 0
    private var startupHealTriggered = false
    private let startupLock = NSLock()

    private init() {}

    var isZhLocale: Bool {
        return Locale.preferredLanguages.first?.lowercased().hasPrefix("zh") == true
    }

    var currentBundleId: String {
        if let bid = Bundle.main.bundleIdentifier, !bid.isEmpty {
            return bid
        }
        return "com.carriez.rrremote"
    }

    func resolvedAppBundleURL() -> URL {
        let mainURL = Bundle.main.bundleURL
        let installedURL = URL(fileURLWithPath: "/Applications/RRRemote.app")
        if mainURL.path.hasPrefix("/Volumes/") && FileManager.default.fileExists(atPath: installedURL.path) {
            return installedURL
        }
        if mainURL.pathExtension.lowercased() == "app" {
            return mainURL
        }
        if FileManager.default.fileExists(atPath: installedURL.path) {
            return installedURL
        }
        return mainURL
    }

    func canScreenRecording() -> Bool {
        if #available(macOS 10.15, *) {
            return CGPreflightScreenCaptureAccess()
        }
        return true
    }

    func canAccessibility() -> Bool {
        return AXIsProcessTrusted()
    }

    func canInputMonitoring() -> Bool {
        if #available(macOS 10.15, *) {
            return IOHIDCheckAccess(kIOHIDRequestTypeListenEvent) == kIOHIDAccessTypeGranted
        }
        return true
    }

    func isGranted(_ pane: RrPermissionPane) -> Bool {
        switch pane {
        case .screen:
            return canScreenRecording()
        case .accessibility:
            return canAccessibility()
        case .input:
            return canInputMonitoring()
        }
    }

    func currentGrantsSnapshot() -> [RrPermissionPane: Bool] {
        return [
            .screen: canScreenRecording(),
            .accessibility: canAccessibility(),
            .input: canInputMonitoring()
        ]
    }

    func firstMissingPane() -> RrPermissionPane? {
        for pane in RrPermissionPane.allCases {
            if !isGranted(pane) {
                return pane
            }
        }
        return nil
    }

    func resolvePane(_ raw: String) -> RrPermissionPane {
        switch raw.trimmingCharacters(in: .whitespacesAndNewlines).lowercased() {
        case "screen":
            return .screen
        case "accessibility":
            return .accessibility
        case "input":
            return .input
        default:
            return firstMissingPane() ?? .accessibility
        }
    }

    // MARK: - Startup Stale-TCC csreq Self-Healing

    func healStaleTccOnStartup() {
        startupLock.lock()
        if startupHealTriggered {
            startupLock.unlock()
            return
        }
        startupHealTriggered = true
        startupLock.unlock()

        DispatchQueue.global(qos: .utility).async { [weak self] in
            self?.performStartupTccHeal()
        }
    }

    private func performStartupTccHeal() {
        let fm = FileManager.default
        let supportDir = fm.homeDirectoryForCurrentUser
            .appendingPathComponent("Library/Application Support/RRRemote", isDirectory: true)
        try? fm.createDirectory(at: supportDir, withIntermediateDirectories: true)

        // 1. Clean legacy com.carriez.rustdesk TCC once
        let legacyMarker = supportDir.appendingPathComponent("legacy_rustdesk_tcc_cleaned")
        if !fm.fileExists(atPath: legacyMarker.path) {
            _ = runProcess(executable: "/usr/bin/tccutil", arguments: ["reset", "All", "com.carriez.rustdesk"])
            try? "1\n".write(to: legacyMarker, atomically: true, encoding: .utf8)
        }

        // 2. Compute current bundle signature fingerprint (designated requirement + CDHash)
        let bundlePath = Bundle.main.bundleURL.path
        let currentSig = computeSignatureFingerprint(bundlePath: bundlePath)
        guard !currentSig.isEmpty else { return }

        let sigFile = supportDir.appendingPathComponent("macos_tcc_sig.txt")
        let savedSig = (try? String(contentsOf: sigFile, encoding: .utf8))?
            .trimmingCharacters(in: .whitespacesAndNewlines) ?? ""

        // 3. If signature changed, reset ONLY currently-ungranted TCC services so stale csreq rows
        //    never block System Settings switches while already-valid grants remain untouched.
        if savedSig != currentSig {
            for pane in RrPermissionPane.allCases {
                if !isGranted(pane) {
                    _ = runTccReset(service: pane.tccService)
                }
            }
            try? (currentSig + "\n").write(to: sigFile, atomically: true, encoding: .utf8)
        }
    }

    private func computeSignatureFingerprint(bundlePath: String) -> String {
        let output = runProcess(executable: "/usr/bin/codesign", arguments: ["-dvvv", "-r-", bundlePath]).output
        var matchedLines: [String] = []
        for rawLine in output.components(separatedBy: .newlines) {
            let trimmed = rawLine.trimmingCharacters(in: .whitespacesAndNewlines)
            if trimmed.hasPrefix("designated =>")
                || trimmed.hasPrefix("# designated =>")
                || trimmed.hasPrefix("CDHash=")
            {
                matchedLines.append(trimmed)
            }
        }
        return matchedLines.joined(separator: "\n")
    }

    @discardableResult
    private func runTccReset(service: String) -> Bool {
        let res = runProcess(executable: "/usr/bin/tccutil", arguments: ["reset", service, currentBundleId])
        return res.exitCode == 0
    }

    private func runProcess(executable: String, arguments: [String]) -> (exitCode: Int32, output: String) {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: executable)
        process.arguments = arguments
        let pipe = Pipe()
        process.standardOutput = pipe
        process.standardError = pipe
        process.standardInput = FileHandle.nullDevice
        do {
            try process.run()
            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            process.waitUntilExit()
            let text = String(data: data, encoding: .utf8) ?? ""
            return (process.terminationStatus, text)
        } catch {
            return (-1, "")
        }
    }

    // MARK: - MethodChannel Actions

    func openPermissionGuide(paneRaw: String, resetFirst: Bool) {
        let pane = resolvePane(paneRaw)
        let currentlyGranted = isGranted(pane)

        // Anti-stuck-toggle guard: if explicitly requested OR user re-opened the same still-missing pane
        // in this session (indicating a stale TCC row rejected System Settings toggle), wipe that service's stale csreq first.
        if !currentlyGranted && (resetFirst || openedPanesInSession.contains(pane)) {
            _ = runTccReset(service: pane.tccService)
        }

        if !currentlyGranted {
            openedPanesInSession.insert(pane)
            triggerNativePromptIfNeeded(for: pane)
        }

        activePane = pane
        lastKnownGrants = currentGrantsSnapshot()
        openSystemSettings(for: pane)
        presentOrRefreshPanel()
        startTrackingTimers()
    }

    func selectPaneFromPill(_ pane: RrPermissionPane) {
        activePane = pane
        if !isGranted(pane) {
            if openedPanesInSession.contains(pane) {
                _ = runTccReset(service: pane.tccService)
            }
            openedPanesInSession.insert(pane)
            triggerNativePromptIfNeeded(for: pane)
        }
        openSystemSettings(for: pane)
        refreshPanelUI()
    }

    func resetCurrentPaneAndReopen() {
        let pane = activePane
        if !isGranted(pane) {
            _ = runTccReset(service: pane.tccService)
            triggerNativePromptIfNeeded(for: pane)
        }
        openSystemSettings(for: pane)
        refreshPanelUI()
    }

    func resetMissingPermissions(paneRaw: String) -> Bool {
        let normalized = paneRaw.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        let targets: [RrPermissionPane]
        switch normalized {
        case "screen":
            targets = [.screen]
        case "accessibility":
            targets = [.accessibility]
        case "input":
            targets = [.input]
        default:
            targets = RrPermissionPane.allCases
        }

        for pane in targets {
            if !isGranted(pane) {
                _ = runTccReset(service: pane.tccService)
            }
        }
        DispatchQueue.main.async { [weak self] in
            self?.refreshPanelUI()
        }
        return true
    }

    func relaunchApplication() {
        closeGuidePanel()
        let appPath = resolvedAppBundleURL().path
        let proc = Process()
        proc.executableURL = URL(fileURLWithPath: "/bin/sh")
        proc.arguments = ["-c", "sleep 0.5; open -a \"$1\"", "--", appPath]
        proc.standardInput = FileHandle.nullDevice
        proc.standardOutput = FileHandle.nullDevice
        proc.standardError = FileHandle.nullDevice
        try? proc.run()
        NSApplication.shared.terminate(nil)
    }

    private func triggerNativePromptIfNeeded(for pane: RrPermissionPane) {
        guard !isGranted(pane) else { return }
        switch pane {
        case .screen:
            if #available(macOS 10.15, *) {
                _ = CGRequestScreenCaptureAccess()
            }
        case .accessibility:
            let options = ["AXTrustedCheckOptionPrompt": true] as CFDictionary
            _ = AXIsProcessTrustedWithOptions(options)
        case .input:
            if #available(macOS 10.15, *) {
                _ = IOHIDRequestAccess(kIOHIDRequestTypeListenEvent)
            }
        }
    }

    private func openSystemSettings(for pane: RrPermissionPane) {
        let wasRunning = !NSRunningApplication.runningApplications(withBundleIdentifier: settingsBundleId).isEmpty
        let url = pane.settingsURL
        _ = NSWorkspace.shared.open(url)
        keepSystemSettingsVisible()
        if !wasRunning {
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.4) { [weak self] in
                _ = NSWorkspace.shared.open(url)
                self?.keepSystemSettingsVisible()
            }
        }
    }

    func keepSystemSettingsVisible() {
        NSRunningApplication.runningApplications(withBundleIdentifier: settingsBundleId)
            .first(where: { $0.activationPolicy != .prohibited })?
            .activate(options: [.activateIgnoringOtherApps])
    }

    // MARK: - Floating Panel Lifecycle & 30fps Window Tracking

    private func presentOrRefreshPanel() {
        let isZh = isZhLocale
        let appURL = resolvedAppBundleURL()
        if panel == nil {
            panel = RrFloatingDropPanel(controller: self, appURL: appURL, isZh: isZh)
        }
        refreshPanelUI()
        if let settingsFrame = currentSystemSettingsFrame() {
            hasSeenSettingsWindow = true
            consecutiveWindowMisses = 0
            panel?.snap(to: settingsFrame)
        } else if panel?.isVisible != true {
            panel?.placeWaitingOnMainScreen()
        }
    }

    private func refreshPanelUI() {
        guard let panel = panel else { return }
        let grants = currentGrantsSnapshot()
        let allGranted = RrPermissionPane.allCases.allSatisfy { grants[$0] == true }
        let showRestart = sessionNewlyGrantedScreenOrInput || allGranted
        panel.updateContent(
            activePane: activePane,
            grants: grants,
            showRestartCTA: showRestart,
            appURL: resolvedAppBundleURL(),
            isZh: isZhLocale
        )
    }

    func closeGuidePanel() {
        stopTrackingTimers()
        panel?.orderOut(nil)
        panel?.close()
        panel = nil
    }

    private func startTrackingTimers() {
        stopTrackingTimers()
        hasSeenSettingsWindow = false
        consecutiveWindowMisses = 0
        trackingStartedAt = Date().timeIntervalSinceReferenceDate

        let trackTimer = Timer(timeInterval: 1.0 / 30.0, repeats: true) { [weak self] _ in
            self?.tickWindowTracking()
        }
        trackTimer.tolerance = 0.008
        RunLoop.main.add(trackTimer, forMode: .common)
        windowTrackTimer = trackTimer

        let pollTimer = Timer(timeInterval: 0.5, repeats: true) { [weak self] _ in
            self?.tickPermissionPoll()
        }
        pollTimer.tolerance = 0.1
        RunLoop.main.add(pollTimer, forMode: .common)
        permissionPollTimer = pollTimer
    }

    private func stopTrackingTimers() {
        windowTrackTimer?.invalidate()
        windowTrackTimer = nil
        permissionPollTimer?.invalidate()
        permissionPollTimer = nil
    }

    func schedulePostDropPoll() {
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.25) { [weak self] in
            self?.tickPermissionPoll()
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.85) { [weak self] in
            self?.tickPermissionPoll()
        }
    }

    private func tickWindowTracking() {
        guard let panel = panel else {
            stopTrackingTimers()
            return
        }

        if let settingsFrame = currentSystemSettingsFrame() {
            hasSeenSettingsWindow = true
            consecutiveWindowMisses = 0
            panel.snap(to: settingsFrame)
            return
        }

        let settingsApps = NSRunningApplication.runningApplications(withBundleIdentifier: settingsBundleId)
            .filter { !$0.isTerminated && $0.activationPolicy != .prohibited }
        let elapsed = Date().timeIntervalSinceReferenceDate - trackingStartedAt

        if settingsApps.isEmpty && (hasSeenSettingsWindow || elapsed > 4.0) {
            consecutiveWindowMisses += 1
            if consecutiveWindowMisses >= 12 {
                closeGuidePanel()
            }
        } else if hasSeenSettingsWindow && settingsApps.isEmpty {
            consecutiveWindowMisses += 1
            if consecutiveWindowMisses >= 12 {
                closeGuidePanel()
            }
        }
    }

    private func tickPermissionPoll() {
        guard panel != nil else { return }
        let nowGrants = currentGrantsSnapshot()
        let prevScreen = lastKnownGrants[.screen] ?? false
        let prevInput = lastKnownGrants[.input] ?? false
        let prevActive = lastKnownGrants[activePane] ?? false

        if (!prevScreen && nowGrants[.screen] == true) || (!prevInput && nowGrants[.input] == true) {
            sessionNewlyGrantedScreenOrInput = true
        }

        lastKnownGrants = nowGrants

        if !prevActive && nowGrants[activePane] == true {
            if let nextMissing = firstMissingPane() {
                activePane = nextMissing
                if !openedPanesInSession.contains(nextMissing) {
                    openedPanesInSession.insert(nextMissing)
                    triggerNativePromptIfNeeded(for: nextMissing)
                }
                openSystemSettings(for: nextMissing)
            }
        }

        refreshPanelUI()
    }

    private func currentSystemSettingsFrame() -> CGRect? {
        guard let settingsApp = NSRunningApplication.runningApplications(withBundleIdentifier: settingsBundleId)
            .first(where: { !$0.isTerminated && $0.activationPolicy != .prohibited })
        else {
            return nil
        }

        let targetPID = settingsApp.processIdentifier
        guard let windowList = CGWindowListCopyWindowInfo([.optionOnScreenOnly, .excludeDesktopElements], kCGNullWindowID) as? [[String: Any]] else {
            return nil
        }

        var bestRect: CGRect?
        var bestArea: CGFloat = 0

        for entry in windowList {
            guard let ownerPID = entry[kCGWindowOwnerPID as String] as? pid_t, ownerPID == targetPID else {
                continue
            }
            let layer = (entry[kCGWindowLayer as String] as? Int) ?? 0
            let alpha = (entry[kCGWindowAlpha as String] as? Double) ?? 1.0
            guard layer == 0 && alpha > 0 else { continue }
            guard let boundsDict = entry[kCGWindowBounds as String] as? NSDictionary,
                  let cgRect = CGRect(dictionaryRepresentation: boundsDict)
            else {
                continue
            }
            let appKitRect = convertCGTopLeftToAppKit(cgRect)
            guard appKitRect.width > 320 && appKitRect.height > 240 else { continue }
            let area = appKitRect.width * appKitRect.height
            if area > bestArea {
                bestArea = area
                bestRect = appKitRect
            }
        }

        return bestRect
    }

    private func convertCGTopLeftToAppKit(_ cgRect: CGRect) -> CGRect {
        let screenPairs = NSScreen.screens.compactMap { screen -> (frame: CGRect, cgBounds: CGRect)? in
            guard let num = screen.deviceDescription[NSDeviceDescriptionKey("NSScreenNumber")] as? NSNumber else {
                return nil
            }
            let displayID = CGDirectDisplayID(num.uint32Value)
            return (frame: screen.frame, cgBounds: CGDisplayBounds(displayID))
        }

        let matched = screenPairs
            .filter { $0.cgBounds.intersects(cgRect) }
            .max { lhs, rhs in
                let la = lhs.cgBounds.intersection(cgRect)
                let ra = rhs.cgBounds.intersection(cgRect)
                return (la.width * la.height) < (ra.width * ra.height)
            }
            ?? screenPairs.first

        guard let targetScreen = matched else {
            return cgRect
        }

        let localX = cgRect.minX - targetScreen.cgBounds.minX
        let localY = cgRect.minY - targetScreen.cgBounds.minY
        return CGRect(
            x: targetScreen.frame.minX + localX,
            y: targetScreen.frame.maxY - localY - cgRect.height,
            width: cgRect.width,
            height: cgRect.height
        )
    }
}
'''


def patch_macos_permission_flow(root: Path) -> None:
    """Inject Snug-style floating drag-to-authorize helper & startup stale-TCC csreq self-healing into MainFlutterWindow.swift."""
    swift_file = root / "flutter" / "macos" / "Runner" / "MainFlutterWindow.swift"
    if not swift_file.exists():
        raise FileNotFoundError(f"Expected {swift_file}")

    txt = read_text(swift_file)
    changed = False

    # 1. Pure AppKit + CoreGraphics + ApplicationServices + IOKit.hid imports (10.14+ & 12.3+ compatible)
    old_imports = "import Cocoa\nimport AVFoundation"
    new_imports = "import Cocoa\nimport AVFoundation\nimport ApplicationServices\nimport IOKit.hid"
    if "import ApplicationServices" in txt and "import IOKit.hid" in txt:
        print("[rrremote] macOS permission helper imports already present in MainFlutterWindow.swift.")
    elif old_imports in txt:
        txt = txt.replace(old_imports, new_imports, 1)
        changed = True
    else:
        raise RuntimeError("Failed to locate import header in flutter/macos/Runner/MainFlutterWindow.swift")

    # 2. Startup stale-TCC csreq self-healing hook in awakeFromNib()
    old_awake = "        rustdesk_core_main();\n"
    new_awake = "        rustdesk_core_main();\n        RrPermissionGuideController.shared.healStaleTccOnStartup()\n"
    if "RrPermissionGuideController.shared.healStaleTccOnStartup()" in txt:
        print("[rrremote] Startup stale-TCC self-healing hook already present in MainFlutterWindow.awakeFromNib().")
    elif old_awake in txt:
        txt = txt.replace(old_awake, new_awake, 1)
        changed = True
    else:
        raise RuntimeError("Failed to locate rustdesk_core_main() in MainFlutterWindow.awakeFromNib()")

    # 3. Extend MethodChannel("org.rustdesk.rustdesk/host") with openMacPermissionGuide, resetMacPermission, relaunchApp
    old_default_case = (
        "                default:\n"
        "                    result(FlutterMethodNotImplemented)\n"
        "                }"
    )
    new_method_cases = (
        '                case "openMacPermissionGuide":\n'
        "                    let argMap = call.arguments as? [String: Any]\n"
        '                    let paneRaw = (argMap?["pane"] as? String) ?? (call.arguments as? String) ?? "auto"\n'
        '                    let resetFirst = (argMap?["resetFirst"] as? Bool) ?? false\n'
        "                    DispatchQueue.main.async {\n"
        "                        RrPermissionGuideController.shared.openPermissionGuide(paneRaw: paneRaw, resetFirst: resetFirst)\n"
        "                        result(true)\n"
        "                    }\n\n"
        '                case "resetMacPermission":\n'
        "                    let argMap = call.arguments as? [String: Any]\n"
        '                    let paneRaw = (argMap?["pane"] as? String) ?? (call.arguments as? String) ?? "all_missing"\n'
        "                    DispatchQueue.global(qos: .userInitiated).async {\n"
        "                        let ok = RrPermissionGuideController.shared.resetMissingPermissions(paneRaw: paneRaw)\n"
        "                        DispatchQueue.main.async {\n"
        "                            result(ok)\n"
        "                        }\n"
        "                    }\n\n"
        '                case "relaunchApp":\n'
        "                    DispatchQueue.main.async {\n"
        "                        result(true)\n"
        "                        RrPermissionGuideController.shared.relaunchApplication()\n"
        "                    }\n\n"
        "                default:\n"
        "                    result(FlutterMethodNotImplemented)\n"
        "                }"
    )
    if 'case "openMacPermissionGuide":' in txt:
        print("[rrremote] MethodChannel macOS permission handlers already present in MainFlutterWindow.swift.")
    elif old_default_case in txt:
        txt = txt.replace(old_default_case, new_method_cases, 1)
        changed = True
    else:
        raise RuntimeError("Failed to locate FlutterMethodNotImplemented default case in MainFlutterWindow.swift")

    # 4. Append RrPermissionGuideController, RrFloatingDropPanel, RrAppDragSourceView, RrAppPasteboardWriter
    if "final class RrPermissionGuideController" in txt:
        print("[rrremote] RrPermissionGuideController classes already appended to MainFlutterWindow.swift.")
    else:
        txt = txt.rstrip() + "\n" + RR_MACOS_PERMISSION_SWIFT.lstrip("\n")
        changed = True

    if changed:
        write_text(swift_file, txt)
        print("[rrremote] Patched flutter/macos/Runner/MainFlutterWindow.swift with Snug-style floating drag helper & TCC self-healing.")


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    display_name = os.environ.get("APP_DISPLAY_NAME", "RRRemote").strip()
    update_repo = os.environ.get("UPDATE_REPO", "melotusme/RRRemote").strip()
    build_tag = os.environ.get("RR_BUILD_TAG", "v1.5.3-rr11").strip()
    rendezvous = os.environ.get("RR_RENDEZVOUS_SERVER", "").strip()
    pub_key = os.environ.get("RR_PUB_KEY", "").strip()
    api_server = os.environ.get("RR_API_SERVER", "").strip()

    print(f"[rrremote] Applying customizations to {root}")
    print(f"[rrremote] Display name: {display_name}, Update repo: {update_repo}, Build tag: {build_tag}")
    print(
        "[rrremote] Build-time server preset:",
        "enabled" if (rendezvous or pub_key or api_server) else "disabled (configure in-app)",
    )

    patch_hbb_common_config(root, display_name, update_repo, rendezvous, pub_key, api_server)
    patch_macos_video_reliability(root)
    patch_macos_input_reliability(root)
    patch_macos_permission_flow(root)
    patch_update_checker(root, update_repo, build_tag)
    patch_updater_artifact_resolver(root, update_repo)
    patch_default_api_server_fallback(root, api_server)
    patch_personal_ergonomics(root)
    script_dir = str(Path(__file__).resolve().parent)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    from p2p_lan_direct import patch_lan_direct_fastpath

    patch_lan_direct_fastpath(root)
    patch_display_branding(root, display_name, update_repo)
    apply_brand_icons(root)

    ui_script = Path(__file__).resolve().parent / "apply_ui_polish.py"
    if ui_script.exists() and os.environ.get("RR_SKIP_UI_POLISH", "") != "1":
        env = os.environ.copy()
        env["UPDATE_REPO"] = update_repo
        subprocess.run([sys.executable, str(ui_script), str(root)], check=True, env=env)

    print("[rrremote] All customizations applied successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
