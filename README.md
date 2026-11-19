# RRRemote

Personal, self-hosted, cross-platform remote desktop solution built on top of open-source **RustDesk** (`1.5.3`) + **RustDesk Server (`hbbs`/`hbbr`)** + **lejianwen/rustdesk-api** — focused on high NAT hole-punching efficiency, zero commercial bloat, custom self-hosted servers, and automated GitHub Actions builds & updates.

## Supported Platforms
- **Windows (x64)**: Controller + Unattended Host (with system service & auto-update task)
- **macOS (Apple Silicon & Intel)**: Controller + Host (ScreenCaptureKit on arm64, LaunchAgent auto-update)
- **Linux & Omarchy (Arch + Hyprland / Wayland)**: Controller + Host (`.pkg.tar.zst` / `.deb`, PipeWire + `xdg-desktop-portal-hyprland` restore token + `/dev/uinput`)
- **Android (arm64)**: Controller + Host (`.apk`)
- **iOS (arm64)**: Controller (unsigned `.ipa` for sideloading / Xcode signing); Phase 2 adds ReplayKit + WebRTC view-only screen sharing (see [docs/ios-screen-share-roadmap.md](docs/ios-screen-share-roadmap.md))

## Architecture
```text
+--------------------+         P2P Hole Punching (TCP/UDP)         +--------------------+
|  RRRemote Client   | <=========================================> |  RRRemote Client   |
| (Win/Mac/Linux/    |      Fallback Relay (hbbr, -k _ auth)       | (Win/Mac/Omarchy/  |
|  Android/iOS)      | <------ Self-Hosted VPS (hbbs/hbbr) ------> |  Android)          |
+--------------------+                      ^                      +--------------------+
          |                                 |
          +---- Device List & Sync API -----+  (lejianwen/rustdesk-api, SQLite, register=off)
```

## Privacy First
This repository contains **zero personal IP addresses, server keys, passwords, or machine inventories**.
- Automated CI check ([privacy-guard.yml](.github/workflows/privacy-guard.yml)) runs `scripts/privacy-check.py` on every push/PR to prevent accidental leaks.
- Server defaults are injected **only at build time** via optional GitHub Actions Secrets, and can always be changed inside the client's **Settings -> Network -> ID/Relay Server** UI.

## GitHub Actions CI & Optional Secrets
To pre-configure your self-hosted server inside your custom-built installers, set these repository secrets under **Settings -> Secrets and variables -> Actions**:

| Secret | Description | Example |
| :--- | :--- | :--- |
| `RR_RENDEZVOUS_SERVER` | Your self-hosted `hbbs`/`hbbr` host or IP | `203.0.113.10` or `remote.example.com` |
| `RR_PUB_KEY` | Contents of `/var/lib/rrremote/server/id_ed25519.pub` | *(Ed25519 public key)* |
| `RR_API_SERVER` | Self-hosted `rustdesk-api` URL for device list sync | `http://203.0.113.10:21114` |

Trigger a build via **Actions -> Build and Release RRRemote -> Run workflow** or by pushing a tag (`git tag v1.5.3-rr1 && git push origin v1.5.3-rr1`).

## Self-Hosted Server Setup
On any Debian/Ubuntu x86_64 VPS:
```bash
PUBLIC_HOST=203.0.113.10 bash server/install-systemd.sh
```
Required firewall ports:
- `TCP 21114`: Device list API & Web Admin (`rustdesk-api`)
- `TCP 21115, 21116, 21118` & `UDP 21116`: Rendezvous / NAT hole punching (`hbbs`)
- `TCP 21117, 21119`: Relay fallback (`hbbr`)

## Client Installation & Auto-Update

### Windows
```powershell
.\scripts\install-windows.ps1 `
  -Server "203.0.113.10" `
  -Key "<YOUR_PUB_KEY>" `
  -ApiServer "http://203.0.113.10:21114" `
  -RegisterAutoUpdate
```

### macOS (Apple Silicon & Intel)
```bash
bash scripts/install-macos.sh \
  --server "203.0.113.10" \
  --key "<YOUR_PUB_KEY>" \
  --api-server "http://203.0.113.10:21114" \
  --register-auto-update
```

### Linux / Omarchy (Arch + Hyprland / Wayland)
```bash
bash scripts/install-linux-omarchy.sh \
  --server "203.0.113.10" \
  --key "<YOUR_PUB_KEY>" \
  --api-server "http://203.0.113.10:21114" \
  --register-auto-update
```

### Switch Self-Hosted Server Anytime
Either change it directly in the app under **Settings -> Network**, or run:
```bash
python3 scripts/configure-client.py --server "203.0.113.10" --key "<YOUR_PUB_KEY>" --api-server "http://203.0.113.10:21114"
```
