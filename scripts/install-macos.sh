#!/usr/bin/env bash
# Install or auto-update RRRemote on macOS (Apple Silicon & Intel) and configure
# self-hosted rendezvous/relay/API server settings.
#
# Usage:
#   bash scripts/install-macos.sh --server 203.0.113.10 --key "<PUBKEY>" --api-server http://203.0.113.10:21114 --register-auto-update
#   bash scripts/install-macos.sh --sign-identity "RRRemote Local Signing" --install-service

set -euo pipefail

REPO="melotusme/RRRemote"
FALLBACK_REPO=""
SERVER=""
RELAY=""
KEY=""
API_SERVER=""
SIGN_IDENTITY="${RR_SIGN_IDENTITY:-}"
REGISTER_AUTO_UPDATE=0
INSTALL_SERVICE=0
FORCE_INSTALL=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo) REPO="$2"; shift 2 ;;
    --fallback-repo) FALLBACK_REPO="$2"; shift 2 ;;
    --server) SERVER="$2"; shift 2 ;;
    --relay) RELAY="$2"; shift 2 ;;
    --key) KEY="$2"; shift 2 ;;
    --api-server) API_SERVER="$2"; shift 2 ;;
    --sign-identity) SIGN_IDENTITY="$2"; shift 2 ;;
    --register-auto-update) REGISTER_AUTO_UPDATE=1; shift ;;
    --install-service) INSTALL_SERVICE=1; shift ;;
    --force) FORCE_INSTALL=1; shift ;;
    *) echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done

# Detect Apple Silicon reliably even when invoked under Rosetta 2
ARCH="$(uname -m)"
if [[ "${ARCH}" != "arm64" ]] && [[ "$(sysctl -n sysctl.proc_translated 2>/dev/null || echo 0)" == "1" ]]; then
  ARCH="arm64"
fi

if [[ "${ARCH}" == "arm64" ]]; then
  ASSET_REGEX="aarch64.*\.dmg$"
  MANIFEST_ARCH="aarch64"
else
  ASSET_REGEX="x86_64.*\.dmg$"
  MANIFEST_ARCH="x86_64"
fi

STATE_DIR="${HOME}/Library/Application Support/RRRemote"
STABLE_SCRIPT_DIR="${STATE_DIR}/scripts"
VERSION_FILE="${STATE_DIR}/installed_tag.txt"
DESIGNATED_REQ_FILE="${STATE_DIR}/designated_req.txt"
LEGACY_TCC_MARKER="${STATE_DIR}/legacy_rustdesk_tcc_cleaned"
mkdir -p "${STATE_DIR}"

if [[ ! -f "${LEGACY_TCC_MARKER}" ]]; then
  tccutil reset All com.carriez.rustdesk 2>/dev/null || true
  touch "${LEGACY_TCC_MARKER}" 2>/dev/null || true
fi

TMP_DIR=""
MOUNT_POINT=""
cleanup() {
  if [[ -n "${MOUNT_POINT}" ]]; then
    hdiutil detach "${MOUNT_POINT}" -quiet 2>/dev/null || hdiutil detach "${MOUNT_POINT}" -force -quiet 2>/dev/null || true
    MOUNT_POINT=""
  fi
  if [[ -n "${TMP_DIR}" && -d "${TMP_DIR}" ]]; then
    rm -rf "${TMP_DIR}"
    TMP_DIR=""
  fi
}
trap cleanup EXIT

fetch_release_json() {
  local repo="$1"
  local api_json
  api_json="$(curl -fsSL -H "User-Agent: RRRemote-Installer" -H "Accept: application/vnd.github+json" \
    "https://api.github.com/repos/${repo}/releases/latest" 2>/dev/null || true)"
  if [[ -n "${api_json}" ]]; then
    printf '%s' "${api_json}"
    return 0
  fi
  # Zero-rate-limit fallback via GitHub web redirect + expanded_assets
  local loc tag html
  loc="$(curl -fsSI -H "User-Agent: RRRemote-Installer" "https://github.com/${repo}/releases/latest" | awk 'tolower($1)=="location:"{print $2}' | tr -d '\r\n')"
  tag="${loc##*/}"
  [[ -n "${tag}" ]] || return 1
  html="$(curl -fsSL -H "User-Agent: RRRemote-Installer" "https://github.com/${repo}/releases/expanded_assets/${tag}")"
  printf '%s' "${html}" | python3 -c '
import json, re, sys
tag = sys.argv[1]
html = sys.stdin.read()
seen = set()
assets = []
for m in re.finditer(r"href=\"(/[^\"\x27]+/releases/download/[^\"\x27]+)\"", html):
    rel = m.group(1)
    if rel not in seen:
        seen.add(rel)
        assets.append({"name": rel.rsplit("/", 1)[-1], "browser_download_url": "https://github.com" + rel})
print(json.dumps({"tag_name": tag, "assets": assets}))
' "${tag}"
}

detect_local_sign_identity() {
  if [[ -n "${SIGN_IDENTITY}" ]]; then
    printf '%s' "${SIGN_IDENTITY}"
    return 0
  fi
  if security find-identity -v -p codesigning 2>/dev/null | grep -Fq '"RRRemote Local Signing"'; then
    printf '%s' "RRRemote Local Signing"
    return 0
  fi
  printf ''
}

sign_app_inside_out() {
  local app_path="$1"
  local identity="$2"
  local ent_plist="${TMP_DIR}/entitlements.plist"
  local ent_args=()

  # Extract existing bundle entitlements (if any) so re-signing never strips them
  if codesign -d --entitlements :- --xml "${app_path}" > "${ent_plist}" 2>/dev/null && grep -q "<dict>" "${ent_plist}"; then
    ent_args=(--entitlements "${ent_plist}")
  else
    rm -f "${ent_plist}"
  fi

  local sign_opts=(--force --sign "${identity}")
  if [[ "${identity}" != "-" && "${identity}" == *"Developer ID Application"* ]]; then
    sign_opts+=(--options runtime --timestamp)
  fi

  # 1. Sign nested Mach-O binaries and frameworks inside-out (never use deprecated --deep)
  if [[ -d "${app_path}/Contents/Frameworks" ]]; then
    while IFS= read -r -d '' bin; do
      if file -b "${bin}" | grep -q 'Mach-O'; then
        codesign "${sign_opts[@]}" "${bin}"
      fi
    done < <(find "${app_path}/Contents/Frameworks" -type f -print0)

    while IFS= read -r -d '' fw; do
      codesign "${sign_opts[@]}" "${fw}"
    done < <(find "${app_path}/Contents/Frameworks" -depth -type d -name "*.framework" -print0)
  fi

  # 2. Sign embedded service helper binary if present
  if [[ -f "${app_path}/Contents/MacOS/service" ]]; then
    codesign "${sign_opts[@]}" "${app_path}/Contents/MacOS/service"
  fi

  # 3. Sign main app bundle last, preserving entitlements
  if [[ "${#ent_args[@]}" -gt 0 ]]; then
    codesign "${sign_opts[@]}" --generate-entitlement-der "${ent_args[@]}" "${app_path}"
  else
    codesign "${sign_opts[@]}" "${app_path}"
  fi
}

migrate_legacy_preferences() {
  local legacy_pref="${HOME}/Library/Preferences/com.carriez.RustDesk"
  local new_pref="${HOME}/Library/Preferences/com.carriez.RRRemote"
  [[ -d "${legacy_pref}" ]] || return 0

  mkdir -p "${new_pref}/peers"
  local migrated=0

  # Per-file migration so existing RRRemote2.toml never blocks migrating peers/ or ID/favs
  for pair in \
    "RustDesk.toml:RRRemote.toml" \
    "RustDesk_local.toml:RRRemote_local.toml" \
    "RustDesk_default.toml:RRRemote_default.toml" \
    "peers.toml:peers.toml"; do
    local src_name="${pair%%:*}"
    local dst_name="${pair##*:}"
    if [[ -f "${legacy_pref}/${src_name}" && ! -f "${new_pref}/${dst_name}" ]]; then
      cp -p "${legacy_pref}/${src_name}" "${new_pref}/${dst_name}"
      migrated=1
    fi
  done

  # Migrate RustDesk2.toml -> RRRemote2.toml without clobbering an already-configured server
  if [[ -f "${legacy_pref}/RustDesk2.toml" ]]; then
    if [[ ! -f "${new_pref}/RRRemote2.toml" ]]; then
      cp -p "${legacy_pref}/RustDesk2.toml" "${new_pref}/RRRemote2.toml"
      migrated=1
    elif ! grep -q "custom-rendezvous-server" "${new_pref}/RRRemote2.toml" 2>/dev/null \
      && grep -q "custom-rendezvous-server" "${legacy_pref}/RustDesk2.toml" 2>/dev/null; then
      cp -p "${new_pref}/RRRemote2.toml" "${new_pref}/RRRemote2.toml.pre-migrate.bak"
      cp -p "${legacy_pref}/RustDesk2.toml" "${new_pref}/RRRemote2.toml"
      migrated=1
    fi
  fi

  # Migrate individual peer files without overwriting existing ones
  if [[ -d "${legacy_pref}/peers" ]]; then
    local p
    for p in "${legacy_pref}/peers/"*; do
      [[ -f "${p}" ]] || continue
      local base
      base="$(basename "${p}")"
      if [[ ! -f "${new_pref}/peers/${base}" ]]; then
        cp -p "${p}" "${new_pref}/peers/${base}"
        migrated=1
      fi
    done
  fi

  if [[ "${migrated}" == "1" ]]; then
    echo "[rrremote] Migrated legacy preferences/peers into ${new_pref}"
  fi
}

stop_running_app() {
  if pgrep -x RRRemote >/dev/null 2>&1; then
    osascript -e 'tell application "RRRemote" to quit' 2>/dev/null || true
    for _ in 1 2 3 4 5; do
      pgrep -x RRRemote >/dev/null 2>&1 || break
      sleep 0.4
    done
    pkill -x RRRemote 2>/dev/null || true
  fi
  if pgrep -x RustDesk >/dev/null 2>&1; then
    pkill -x RustDesk 2>/dev/null || true
  fi
}

USED_REPO="${REPO}"
RELEASE_JSON="$(fetch_release_json "${REPO}" 2>/dev/null || true)"
if [[ -z "${RELEASE_JSON}" && -n "${FALLBACK_REPO}" ]]; then
  echo "[rrremote] No release in ${REPO} yet, falling back to ${FALLBACK_REPO}..."
  USED_REPO="${FALLBACK_REPO}"
  RELEASE_JSON="$(fetch_release_json "${FALLBACK_REPO}")"
fi

if [[ -z "${RELEASE_JSON}" ]]; then
  echo "ERROR: Could not fetch release metadata from ${REPO}" >&2
  exit 1
fi

PARSED="$(printf '%s' "${RELEASE_JSON}" | python3 -c '
import json, re, sys
pattern = re.compile(sys.argv[1])
data = json.load(sys.stdin)
tag = data.get("tag_name", "")
url = ""
name = ""
manifest_url = ""
for a in data.get("assets", []):
    n = a.get("name", "")
    if n == "rrremote-update.json":
        manifest_url = a.get("browser_download_url", "")
    elif not url and pattern.search(n):
        url = a.get("browser_download_url", "")
        name = n
print(tag)
print(name)
print(url)
print(manifest_url)
' "${ASSET_REGEX}")"

TAG="$(echo "${PARSED}" | sed -n '1p')"
ASSET_NAME="$(echo "${PARSED}" | sed -n '2p')"
ASSET_URL="$(echo "${PARSED}" | sed -n '3p')"
MANIFEST_URL="$(echo "${PARSED}" | sed -n '4p')"

if [[ -z "${ASSET_URL}" ]]; then
  echo "ERROR: No macOS (${ARCH}) DMG asset found in ${USED_REPO}@${TAG}" >&2
  exit 1
fi

DESIRED_TAG="${USED_REPO}@${TAG}"
CURRENT_TAG="$(cat "${VERSION_FILE}" 2>/dev/null || true)"

WAS_RUNNING=0
if pgrep -x RRRemote >/dev/null 2>&1 || pgrep -x RustDesk >/dev/null 2>&1; then
  WAS_RUNNING=1
fi

INSTALLED_APP="/Applications/RRRemote.app"
APP_UPDATED=0

if [[ "${FORCE_INSTALL}" == "1" || "${CURRENT_TAG}" != "${DESIRED_TAG}" || ! -d "${INSTALLED_APP}" ]]; then
  TMP_DIR="$(mktemp -d)"
  DMG_PATH="${TMP_DIR}/${ASSET_NAME}"
  echo "[rrremote] Downloading ${ASSET_NAME} from ${DESIRED_TAG}..."
  curl -fL "${ASSET_URL}" -o "${DMG_PATH}"

  # Verify SHA256 against rrremote-update.json when published in the release
  if [[ -n "${MANIFEST_URL}" ]]; then
    MANIFEST_JSON="$(curl -fsSL -H "User-Agent: RRRemote-Installer" "${MANIFEST_URL}" 2>/dev/null || true)"
    if [[ -n "${MANIFEST_JSON}" ]]; then
      EXPECTED_SHA="$(printf '%s' "${MANIFEST_JSON}" | python3 -c '
import json, sys
arch, fname = sys.argv[1], sys.argv[2]
data = json.load(sys.stdin)
for item in data.get("artifacts", []):
    if item.get("platform") == "macos" and item.get("arch") == arch and item.get("format") == "dmg":
        if not fname or item.get("file_name") == fname:
            print(item.get("sha256", ""))
            break
' "${MANIFEST_ARCH}" "${ASSET_NAME}")"
      if [[ -n "${EXPECTED_SHA}" ]]; then
        ACTUAL_SHA="$(shasum -a 256 "${DMG_PATH}" | awk '{print $1}')"
        if [[ "${ACTUAL_SHA}" != "${EXPECTED_SHA}" ]]; then
          echo "ERROR: SHA256 mismatch for ${ASSET_NAME} (expected ${EXPECTED_SHA}, got ${ACTUAL_SHA})" >&2
          exit 1
        fi
        echo "[rrremote] Verified SHA256 (${ACTUAL_SHA:0:16}...)."
      fi
    fi
  fi

  MOUNT_POINT="$(hdiutil attach -readonly -nobrowse -noautoopen "${DMG_PATH}" | awk '/\/Volumes\//{print substr($0, index($0, "/Volumes/"))}' | head -n 1)"
  if [[ -z "${MOUNT_POINT}" || ! -d "${MOUNT_POINT}" ]]; then
    echo "ERROR: Failed to mount ${DMG_PATH}" >&2
    exit 1
  fi
  APP_SRC="$(find "${MOUNT_POINT}" -maxdepth 2 -name "*.app" | head -n 1)"
  if [[ -z "${APP_SRC}" || ! -d "${APP_SRC}" ]]; then
    echo "ERROR: No .app bundle found inside ${DMG_PATH}" >&2
    exit 1
  fi
  APP_NAME="$(basename "${APP_SRC}")"
  INSTALLED_APP="/Applications/${APP_NAME}"

  echo "[rrremote] Installing ${APP_NAME} to /Applications..."
  stop_running_app

  # Safely unload legacy user-session RustDesk LaunchAgent if present
  if [[ -f "/Library/LaunchAgents/com.carriez.RustDesk_server.plist" ]]; then
    launchctl bootout "gui/$(id -u)" "/Library/LaunchAgents/com.carriez.RustDesk_server.plist" 2>/dev/null || true
  fi
  if [[ -f "/Library/LaunchDaemons/com.carriez.RustDesk_service.plist" ]]; then
    echo "[rrremote] Note: Legacy /Library/LaunchDaemons/com.carriez.RustDesk_service.plist is still present; run 'sudo launchctl bootout system /Library/LaunchDaemons/com.carriez.RustDesk_service.plist && sudo rm -f /Library/LaunchDaemons/com.carriez.RustDesk_service.plist' to clean it up."
  fi

  migrate_legacy_preferences

  if [[ "${APP_NAME}" == "RRRemote.app" && -d "/Applications/RustDesk.app" ]]; then
    rm -rf "/Applications/RustDesk.app"
  fi

  # Capture existing app's designated requirement before replacing so ad-hoc cdhash -> persistent
  # certificate upgrades can clear stale TCC csreq rows once.
  OLD_REQ=""
  if [[ -d "${INSTALLED_APP}" ]]; then
    OLD_REQ="$({ codesign -d -r- "${INSTALLED_APP}" 2>&1 || true; } | sed -n 's/^designated => //p' | head -n 1)"
  fi
  if [[ -z "${OLD_REQ}" && -f "${DESIGNATED_REQ_FILE}" ]]; then
    OLD_REQ="$(cat "${DESIGNATED_REQ_FILE}" 2>/dev/null || true)"
  fi

  rm -rf "${INSTALLED_APP}"
  ditto "${APP_SRC}" "${INSTALLED_APP}"
  xattr -dr com.apple.quarantine "${INSTALLED_APP}" 2>/dev/null || true

  # Preserve valid CI/Developer ID certificate signatures untouched unless --sign-identity was
  # explicitly specified, or if an ad-hoc bundle has Hardened Runtime enabled (SIP dyld failure).
  EFFECTIVE_IDENTITY="$(detect_local_sign_identity)"
  CODESIGN_META="$(codesign -dv "${INSTALLED_APP}" 2>&1 || true)"
  BUNDLE_REQ="$({ codesign -d -r- "${INSTALLED_APP}" 2>&1 || true; } | sed -n 's/^designated => //p' | head -n 1)"
  if [[ -n "${SIGN_IDENTITY}" ]]; then
    echo "[rrremote] Signing ${INSTALLED_APP} inside-out with requested Keychain identity '${SIGN_IDENTITY}'..."
    sign_app_inside_out "${INSTALLED_APP}" "${SIGN_IDENTITY}"
  elif echo "${CODESIGN_META}" | grep -Eq 'flags=.*\(.*adhoc.*runtime'; then
    echo "[rrremote] Ad-hoc Hardened Runtime detected; re-signing inside-out without runtime for SIP dyld compatibility..."
    sign_app_inside_out "${INSTALLED_APP}" "-"
  elif [[ "${BUNDLE_REQ}" == *"certificate leaf"* ]] && codesign --verify --deep --strict "${INSTALLED_APP}" >/dev/null 2>&1; then
    echo "[rrremote] Preserving valid certificate-backed bundle signature on ${INSTALLED_APP}."
  elif [[ -n "${EFFECTIVE_IDENTITY}" ]]; then
    echo "[rrremote] Signing ${INSTALLED_APP} inside-out with Keychain identity '${EFFECTIVE_IDENTITY}'..."
    sign_app_inside_out "${INSTALLED_APP}" "${EFFECTIVE_IDENTITY}"
  elif codesign --verify --deep --strict "${INSTALLED_APP}" >/dev/null 2>&1; then
    echo "[rrremote] Preserving valid bundle signature on ${INSTALLED_APP}."
  else
    echo "[rrremote] Bundle signature invalid/unsealed; re-signing inside-out (ad-hoc, preserving entitlements)..."
    sign_app_inside_out "${INSTALLED_APP}" "-"
    echo "[rrremote] Tip: Create a self-signed Code Signing certificate named 'RRRemote Local Signing' in Keychain Access so macOS TCC permissions survive future updates."
  fi

  codesign --verify --deep --strict "${INSTALLED_APP}" || echo "[rrremote] WARNING: codesign verification reported issues on ${INSTALLED_APP}" >&2

  NEW_REQ="$({ codesign -d -r- "${INSTALLED_APP}" 2>&1 || true; } | sed -n 's/^designated => //p' | head -n 1)"
  if [[ -n "${NEW_REQ}" ]]; then
    printf '%s\n' "${NEW_REQ}" > "${DESIGNATED_REQ_FILE}"
  fi
  if [[ -n "${OLD_REQ}" && "${OLD_REQ}" != "${NEW_REQ}" && "${OLD_REQ}" == *"cdhash"* ]]; then
    echo "[rrremote] Code signing requirement changed from ad-hoc cdhash to persistent signature; resetting stale macOS TCC entries for com.carriez.rrremote..."
    for tcc_svc in Accessibility ScreenCapture ListenEvent; do
      tccutil reset "${tcc_svc}" com.carriez.rrremote 2>/dev/null || true
    done
  fi

  hdiutil detach "${MOUNT_POINT}" -quiet || true
  MOUNT_POINT=""

  echo "${DESIRED_TAG}" > "${VERSION_FILE}"
  APP_UPDATED=1
  echo "[rrremote] Installed ${DESIRED_TAG}."
else
  migrate_legacy_preferences
  if [[ -d "${INSTALLED_APP}" && ! -f "${DESIGNATED_REQ_FILE}" ]]; then
    NEW_REQ="$({ codesign -d -r- "${INSTALLED_APP}" 2>&1 || true; } | sed -n 's/^designated => //p' | head -n 1)"
    if [[ -n "${NEW_REQ}" ]]; then
      printf '%s\n' "${NEW_REQ}" > "${DESIGNATED_REQ_FILE}"
    fi
  fi
  echo "[rrremote] Already up to date (${DESIRED_TAG})."
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -n "${SERVER}" && -n "${KEY}" ]]; then
  # Ensure RRRemote is stopped while updating RRRemote2.toml so in-memory state cannot overwrite it
  stop_running_app
  ARGS=(--server "${SERVER}" --key "${KEY}")
  [[ -n "${RELAY}" ]] && ARGS+=(--relay "${RELAY}")
  [[ -n "${API_SERVER}" ]] && ARGS+=(--api-server "${API_SERVER}")
  python3 "${SCRIPT_DIR}/configure-client.py" "${ARGS[@]}"
fi

if [[ "${INSTALL_SERVICE}" == "1" ]]; then
  SERVICE_BIN="${INSTALLED_APP}/Contents/MacOS/service"
  if [[ -x "${SERVICE_BIN}" ]]; then
    echo "[rrremote] Installing macOS background LaunchDaemon & LaunchAgent (requires sudo)..."
    sudo "${SERVICE_BIN}" --write-plists
    sudo launchctl bootout system/com.carriez.RRRemote_service 2>/dev/null || true
    sudo launchctl bootstrap system /Library/LaunchDaemons/com.carriez.RRRemote_service.plist 2>/dev/null \
      || sudo launchctl load -w /Library/LaunchDaemons/com.carriez.RRRemote_service.plist
    launchctl bootout "gui/$(id -u)" /Library/LaunchAgents/com.carriez.RRRemote_server.plist 2>/dev/null || true
    launchctl bootstrap "gui/$(id -u)" /Library/LaunchAgents/com.carriez.RRRemote_server.plist 2>/dev/null \
      || launchctl load -w /Library/LaunchAgents/com.carriez.RRRemote_server.plist
    if [[ -n "${SERVER}" && -n "${KEY}" ]]; then
      sudo python3 "${SCRIPT_DIR}/configure-client.py" "${ARGS[@]}" --config-path /var/root/Library/Preferences/com.carriez.RRRemote/RRRemote2.toml 2>/dev/null || true
    fi
    echo "[rrremote] Background LaunchDaemon & LaunchAgent installed."
  else
    echo "[rrremote] WARNING: ${SERVICE_BIN} not found; skipping service installation." >&2
  fi
elif [[ ! -f "/Library/LaunchDaemons/com.carriez.RRRemote_service.plist" ]]; then
  echo "[rrremote] Note: Background daemon not installed. Pass --install-service if you want unattended/login-window background service."
fi

# Never leave RRRemote dead if it was running before install/update/config (or after fresh install)
if [[ -d "${INSTALLED_APP}" ]] && [[ "${WAS_RUNNING}" == "1" || "${APP_UPDATED}" == "1" ]]; then
  CONSOLE_USER="$(stat -f '%Su' /dev/console 2>/dev/null || true)"
  if launchctl managername 2>/dev/null | grep -qi "Aqua" || [[ "${CONSOLE_USER}" == "$(id -un)" ]]; then
    open -a "${INSTALLED_APP}" 2>/dev/null || true
    echo "[rrremote] Launched ${INSTALLED_APP}."
  fi
fi

if [[ "${REGISTER_AUTO_UPDATE}" == "1" ]]; then
  mkdir -p "${STABLE_SCRIPT_DIR}"
  cp -f "${SCRIPT_DIR}/install-macos.sh" "${STABLE_SCRIPT_DIR}/install-macos.sh"
  chmod +x "${STABLE_SCRIPT_DIR}/install-macos.sh"
  if [[ -f "${SCRIPT_DIR}/configure-client.py" ]]; then
    cp -f "${SCRIPT_DIR}/configure-client.py" "${STABLE_SCRIPT_DIR}/configure-client.py"
  fi

  PLIST="${HOME}/Library/LaunchAgents/com.rrremote.autoupdate.plist"
  mkdir -p "${HOME}/Library/LaunchAgents"
  SIGN_ARGS_XML=""
  if [[ -n "${SIGN_IDENTITY}" ]]; then
    SIGN_ARGS_XML="    <string>--sign-identity</string>
    <string>${SIGN_IDENTITY}</string>"
  fi

  cat > "${PLIST}" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.rrremote.autoupdate</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
  </dict>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>${STABLE_SCRIPT_DIR}/install-macos.sh</string>
    <string>--repo</string>
    <string>${REPO}</string>
${SIGN_ARGS_XML}
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>4</integer>
    <key>Minute</key>
    <integer>0</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>${STATE_DIR}/autoupdate.log</string>
  <key>StandardErrorPath</key>
  <string>${STATE_DIR}/autoupdate.log</string>
</dict>
</plist>
EOF
  # Remove any blank lines inside <array> if SIGN_ARGS_XML was empty
  python3 -c '
from pathlib import Path
import sys
p = Path(sys.argv[1])
p.write_text("\n".join(line for line in p.read_text(encoding="utf-8").splitlines() if line.strip()) + "\n", encoding="utf-8")
' "${PLIST}"
  launchctl bootout "gui/$(id -u)" "${PLIST}" 2>/dev/null || launchctl unload "${PLIST}" 2>/dev/null || true
  launchctl bootstrap "gui/$(id -u)" "${PLIST}" 2>/dev/null || launchctl load -w "${PLIST}"
  echo "[rrremote] Registered daily auto-update LaunchAgent: ${PLIST}"
fi
