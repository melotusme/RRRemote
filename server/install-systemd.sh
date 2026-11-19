#!/usr/bin/env bash
# Deploy RRRemote self-hosted rendezvous (hbbs), relay (hbbr), and device-list API
# (lejianwen/rustdesk-api) as lightweight systemd services on Debian/Ubuntu x86_64.
#
# Usage:
#   PUBLIC_HOST=203.0.113.10 bash server/install-systemd.sh
# If PUBLIC_HOST is omitted on GCP, it is auto-detected from GCP metadata.

set -euo pipefail

RUSTDESK_SERVER_VERSION="${RUSTDESK_SERVER_VERSION:-1.1.16}"
RUSTDESK_API_VERSION="${RUSTDESK_API_VERSION:-v2.7}"
PUBLIC_HOST="${PUBLIC_HOST:-}"

if [[ -z "${PUBLIC_HOST}" ]]; then
  PUBLIC_HOST="$(curl -fsSL -H 'Metadata-Flavor: Google' \
    http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip 2>/dev/null || true)"
fi

if [[ -z "${PUBLIC_HOST}" ]]; then
  echo "ERROR: Please set PUBLIC_HOST=<your-server-ip-or-domain>" >&2
  exit 1
fi

echo "[1/5] Preparing directories..."
sudo mkdir -p /opt/rrremote/server /opt/rrremote/api /var/lib/rrremote/server /var/lib/rrremote/api
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

echo "[2/5] Downloading rustdesk-server ${RUSTDESK_SERVER_VERSION}..."
curl -fL "https://github.com/rustdesk/rustdesk-server/releases/download/${RUSTDESK_SERVER_VERSION}/rustdesk-server-linux-amd64.zip" \
  -o "${TMP_DIR}/rustdesk-server.zip"
python3 -c "import zipfile; zipfile.ZipFile('${TMP_DIR}/rustdesk-server.zip').extractall('${TMP_DIR}/rd-srv')"
sudo install -m 0755 "${TMP_DIR}/rd-srv/amd64/hbbs" /opt/rrremote/server/hbbs
sudo install -m 0755 "${TMP_DIR}/rd-srv/amd64/hbbr" /opt/rrremote/server/hbbr

echo "[3/5] Downloading lejianwen/rustdesk-api ${RUSTDESK_API_VERSION}..."
curl -fL "https://github.com/lejianwen/rustdesk-api/releases/download/${RUSTDESK_API_VERSION}/linux-amd64.tar.gz" \
  -o "${TMP_DIR}/rustdesk-api.tar.gz"
mkdir -p "${TMP_DIR}/rd-api"
tar -xzf "${TMP_DIR}/rustdesk-api.tar.gz" -C "${TMP_DIR}/rd-api"
sudo cp -a "${TMP_DIR}/rd-api/"* /opt/rrremote/api/
sudo chmod +x /opt/rrremote/api/release/apimain

echo "[4/5] Configuring systemd services (key enforcement enabled via -k _)..."
sudo tee /etc/systemd/system/rrremote-hbbs.service > /dev/null <<'EOF'
[Unit]
Description=RRRemote ID/Rendezvous Server (hbbs)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/var/lib/rrremote/server
ExecStart=/opt/rrremote/server/hbbs -k _
Restart=always
RestartSec=3
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF

sudo tee /etc/systemd/system/rrremote-hbbr.service > /dev/null <<'EOF'
[Unit]
Description=RRRemote Relay Server (hbbr)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/var/lib/rrremote/server
ExecStart=/opt/rrremote/server/hbbr -k _
Restart=always
RestartSec=3
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF

JWT_SECRET="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
sudo python3 - "${PUBLIC_HOST}" "${JWT_SECRET}" <<'PY'
import re
import sys
from pathlib import Path

pub_host, jwt_secret = sys.argv[1], sys.argv[2]
cfg = Path("/opt/rrremote/api/release/conf/config.yaml")
txt = cfg.read_text(encoding="utf-8")
txt = re.sub(r'title:\s*"[^"]*"', 'title: "RRRemote Admin"', txt, count=1)
txt = re.sub(r'id-server:\s*"[^"]*"', f'id-server: "{pub_host}:21116"', txt, count=1)
txt = re.sub(r'relay-server:\s*"[^"]*"', f'relay-server: "{pub_host}:21117"', txt, count=1)
txt = re.sub(r'api-server:\s*"[^"]*"', f'api-server: "http://{pub_host}:21114"', txt, count=1)
txt = re.sub(r'key-file:\s*"[^"]*"', 'key-file: "/var/lib/rrremote/server/id_ed25519.pub"', txt, count=1)
txt = txt.replace('jwt:\n  key: ""', f'jwt:\n  key: "{jwt_secret}"')
cfg.write_text(txt, encoding="utf-8")
PY

sudo tee /etc/systemd/system/rrremote-api.service > /dev/null <<'EOF'
[Unit]
Description=RRRemote API & Device List Server (rustdesk-api)
After=network-online.target rrremote-hbbs.service
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/rrremote/api/release
ExecStart=/opt/rrremote/api/release/apimain
Restart=always
RestartSec=3
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF

echo "[5/5] Starting services..."
sudo systemctl daemon-reload
sudo systemctl enable --now rrremote-hbbs rrremote-hbbr rrremote-api
sleep 2
sudo systemctl is-active rrremote-hbbs rrremote-hbbr rrremote-api

echo ""
echo "=== Deployment complete ==="
echo "ID Server:    ${PUBLIC_HOST}"
echo "Relay Server: ${PUBLIC_HOST}"
echo "API Server:   http://${PUBLIC_HOST}:21114"
echo "Public Key:   $(sudo cat /var/lib/rrremote/server/id_ed25519.pub)"
echo "Check initial admin password with: sudo journalctl -u rrremote-api -n 30 --no-pager"
