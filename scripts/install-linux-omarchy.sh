#!/usr/bin/env bash
# Install or auto-update RRRemote on Linux — with first-class support for
# Omarchy (Arch Linux + Hyprland / Wayland) unattended screen sharing & input.
#
# Usage:
#   bash scripts/install-linux-omarchy.sh --server 203.0.113.10 --key "<PUBKEY>" --api-server http://203.0.113.10:21114 --register-auto-update

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
if [[ "${ARCH}" != "x86_64" ]]; then
  echo "ERROR: Currently x86_64 packages are supported (got ${ARCH})" >&2
  exit 1
fi

if command -v pacman >/dev/null 2>&1; then
  PKG_TYPE="arch"
  ASSET_REGEX="x86_64\.pkg\.tar\.zst$"
elif command -v apt-get >/dev/null 2>&1; then
  PKG_TYPE="deb"
  ASSET_REGEX="x86_64\.deb$"
else
  echo "ERROR: Unsupported Linux package manager (expected pacman or apt-get)" >&2
  exit 1
fi

STATE_DIR="${HOME}/.local/share/rrremote"
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
    if pattern.search(n) and "sciter" not in n and "unattended" not in n:
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
  echo "ERROR: No ${PKG_TYPE} package asset found in ${USED_REPO}@${TAG}" >&2
  exit 1
fi

DESIRED_TAG="${USED_REPO}@${TAG}"
CURRENT_TAG="$(cat "${VERSION_FILE}" 2>/dev/null || true)"

if [[ "${CURRENT_TAG}" != "${DESIRED_TAG}" ]]; then
  TMP_DIR="$(mktemp -d)"
  trap 'rm -rf "${TMP_DIR}"' EXIT
  PKG_PATH="${TMP_DIR}/${ASSET_NAME}"
  echo "[rrremote] Downloading ${ASSET_NAME} from ${DESIRED_TAG}..."
  curl -fL "${ASSET_URL}" -o "${PKG_PATH}"

  if [[ "${PKG_TYPE}" == "arch" ]]; then
    sudo pacman -U --noconfirm "${PKG_PATH}"
  else
    sudo apt-get install -y "${PKG_PATH}"
  fi

  echo "${DESIRED_TAG}" > "${VERSION_FILE}"
  echo "[rrremote] Installed ${DESIRED_TAG}."
else
  echo "[rrremote] Already up to date (${DESIRED_TAG})."
fi

# Omarchy / Hyprland Wayland unattended screen sharing & input setup
if command -v hyprctl >/dev/null 2>&1 || [[ "${XDG_CURRENT_DESKTOP:-}" == *"Hyprland"* ]] || pgrep -x Hyprland >/dev/null 2>&1; then
  echo "[rrremote] Detected Hyprland / Omarchy Wayland environment — applying portal & uinput tuning..."
  XDPH_CONF="${HOME}/.config/hypr/xdph.conf"
  mkdir -p "$(dirname "${XDPH_CONF}")"
  if [[ ! -f "${XDPH_CONF}" ]] || ! grep -q "allow_token_by_default" "${XDPH_CONF}"; then
    cat >> "${XDPH_CONF}" <<'EOF'

screencast {
    allow_token_by_default = true
}
EOF
    echo "[rrremote] Enabled screencast restore token in ${XDPH_CONF}"
  fi

  # Ensure /dev/uinput is loaded and accessible for remote mouse/keyboard injection
  if [[ ! -f /etc/modules-load.d/uinput.conf ]]; then
    echo 'uinput' | sudo tee /etc/modules-load.d/uinput.conf >/dev/null
  fi
  sudo modprobe uinput 2>/dev/null || true
  if [[ ! -f /etc/udev/rules.d/99-rrremote-uinput.rules ]]; then
    echo 'KERNEL=="uinput", MODE="0660", GROUP="input", OPTIONS+="static_node=uinput"' | \
      sudo tee /etc/udev/rules.d/99-rrremote-uinput.rules >/dev/null
    sudo udevadm control --reload-rules && sudo udevadm trigger /dev/uinput 2>/dev/null || true
    sudo usermod -aG input "${USER}" 2>/dev/null || true
  fi
fi

# Enable system service if present
if systemctl list-unit-files | grep -q "^rustdesk\.service"; then
  sudo systemctl enable --now rustdesk.service
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -n "${SERVER}" && -n "${KEY}" ]]; then
  ARGS=(--server "${SERVER}" --key "${KEY}")
  [[ -n "${RELAY}" ]] && ARGS+=(--relay "${RELAY}")
  [[ -n "${API_SERVER}" ]] && ARGS+=(--api-server "${API_SERVER}")
  python3 "${SCRIPT_DIR}/configure-client.py" "${ARGS[@]}"
  sudo python3 "${SCRIPT_DIR}/configure-client.py" "${ARGS[@]}" --config-path /root/.config/rustdesk/RustDesk2.toml 2>/dev/null || true
  sudo systemctl restart rustdesk.service 2>/dev/null || true
fi

if [[ "${REGISTER_AUTO_UPDATE}" == "1" ]]; then
  UNIT_DIR="${HOME}/.config/systemd/user"
  mkdir -p "${UNIT_DIR}"
  cat > "${UNIT_DIR}/rrremote-autoupdate.service" <<EOF
[Unit]
Description=RRRemote Auto-Update Check

[Service]
Type=oneshot
ExecStart=/usr/bin/env bash ${SCRIPT_DIR}/install-linux-omarchy.sh --repo ${REPO}
EOF
  cat > "${UNIT_DIR}/rrremote-autoupdate.timer" <<'EOF'
[Unit]
Description=Daily RRRemote Auto-Update Check

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
EOF
  systemctl --user daemon-reload
  systemctl --user enable --now rrremote-autoupdate.timer
  echo "[rrremote] Enabled user systemd timer: rrremote-autoupdate.timer"
fi
