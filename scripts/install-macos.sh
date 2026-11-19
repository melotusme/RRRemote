#!/usr/bin/env bash
# Install or auto-update RRRemote on macOS (Apple Silicon & Intel) and configure
# self-hosted rendezvous/relay/API server settings.
#
# Usage:
#   bash scripts/install-macos.sh --server 203.0.113.10 --key "<PUBKEY>" --api-server http://203.0.113.10:21114 --register-auto-update

set -euo pipefail

REPO="melotusme/RRRemote"
FALLBACK_REPO=""
SERVER=""
RELAY=""
KEY=""
API_SERVER=""
REGISTER_AUTO_UPDATE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo) REPO="$2"; shift 2 ;;
    --fallback-repo) FALLBACK_REPO="$2"; shift 2 ;;
    --server) SERVER="$2"; shift 2 ;;
    --relay) RELAY="$2"; shift 2 ;;
    --key) KEY="$2"; shift 2 ;;
    --api-server) API_SERVER="$2"; shift 2 ;;
    --register-auto-update) REGISTER_AUTO_UPDATE=1; shift ;;
    *) echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done

ARCH="$(uname -m)"
if [[ "${ARCH}" == "arm64" ]]; then
  ASSET_REGEX="aarch64.*\.dmg$"
else
  ASSET_REGEX="x86_64.*\.dmg$"
fi

STATE_DIR="${HOME}/Library/Application Support/RRRemote"
VERSION_FILE="${STATE_DIR}/installed_tag.txt"
mkdir -p "${STATE_DIR}"

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
for a in data.get("assets", []):
    n = a.get("name", "")
    if pattern.search(n):
        url = a.get("browser_download_url", "")
        name = n
        break
print(tag)
print(name)
print(url)
' "${ASSET_REGEX}")"

TAG="$(echo "${PARSED}" | sed -n '1p')"
ASSET_NAME="$(echo "${PARSED}" | sed -n '2p')"
ASSET_URL="$(echo "${PARSED}" | sed -n '3p')"

if [[ -z "${ASSET_URL}" ]]; then
  echo "ERROR: No macOS (${ARCH}) DMG asset found in ${USED_REPO}@${TAG}" >&2
  exit 1
fi

DESIRED_TAG="${USED_REPO}@${TAG}"
CURRENT_TAG="$(cat "${VERSION_FILE}" 2>/dev/null || true)"

if [[ "${CURRENT_TAG}" != "${DESIRED_TAG}" ]]; then
  TMP_DIR="$(mktemp -d)"
  trap 'rm -rf "${TMP_DIR}"' EXIT
  DMG_PATH="${TMP_DIR}/${ASSET_NAME}"
  echo "[rrremote] Downloading ${ASSET_NAME} from ${DESIRED_TAG}..."
  curl -fL "${ASSET_URL}" -o "${DMG_PATH}"

  MOUNT_POINT="$(hdiutil attach -nobrowse -noautoopen "${DMG_PATH}" | awk '/\/Volumes\//{print substr($0, index($0, "/Volumes/"))}' | head -n 1)"
  APP_SRC="$(find "${MOUNT_POINT}" -maxdepth 2 -name "*.app" | head -n 1)"
  APP_NAME="$(basename "${APP_SRC}")"

  echo "[rrremote] Installing ${APP_NAME} to /Applications..."
  pkill -x RustDesk 2>/dev/null || true
  rm -rf "/Applications/${APP_NAME}"
  cp -R "${APP_SRC}" "/Applications/${APP_NAME}"
  xattr -dr com.apple.quarantine "/Applications/${APP_NAME}" 2>/dev/null || true
  codesign --force --deep --sign - "/Applications/${APP_NAME}" 2>/dev/null || true
  hdiutil detach "${MOUNT_POINT}" -quiet || true

  echo "${DESIRED_TAG}" > "${VERSION_FILE}"
  echo "[rrremote] Installed ${DESIRED_TAG}."
else
  echo "[rrremote] Already up to date (${DESIRED_TAG})."
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -n "${SERVER}" && -n "${KEY}" ]]; then
  ARGS=(--server "${SERVER}" --key "${KEY}")
  [[ -n "${RELAY}" ]] && ARGS+=(--relay "${RELAY}")
  [[ -n "${API_SERVER}" ]] && ARGS+=(--api-server "${API_SERVER}")
  python3 "${SCRIPT_DIR}/configure-client.py" "${ARGS[@]}"
fi

if [[ "${REGISTER_AUTO_UPDATE}" == "1" ]]; then
  PLIST="${HOME}/Library/LaunchAgents/com.rrremote.autoupdate.plist"
  mkdir -p "${HOME}/Library/LaunchAgents"
  cat > "${PLIST}" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.rrremote.autoupdate</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>${SCRIPT_DIR}/install-macos.sh</string>
    <string>--repo</string>
    <string>${REPO}</string>
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
  launchctl unload "${PLIST}" 2>/dev/null || true
  launchctl load "${PLIST}"
  echo "[rrremote] Registered daily auto-update LaunchAgent: ${PLIST}"
fi
