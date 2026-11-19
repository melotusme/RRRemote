# iOS Screen Sharing (View-Only Host) Roadmap — Phase 2

## Background
- **Controller (iOS -> Windows/macOS/Linux/Android)**: Fully supported out-of-the-box by the RRRemote iOS client built from the RustDesk Flutter core.
- **View-Only Host (Any device -> viewing iOS screen)**: iOS sandboxing does not allow background headless screen capture or third-party touch injection. Apple provides **ReplayKit `RPBroadcastUploadExtension`** for user-initiated system-wide screen broadcasting.

## Planned Architecture (Phase 2)
1. **iOS App Extension (`RRRemoteBroadcastExtension`)**:
   - Subclasses `RPBroadcastSampleHandler` (`SampleHandler.swift`).
   - Captures system-wide `RPSampleBufferType.video` (and optional app/mic audio) within Apple's 50 MB extension memory limit.
   - Streams frames over an **App Group Unix Domain Socket** to the main RRRemote Flutter app process (standard `flutter-webrtc` / `livekit` pattern).
2. **Transport & Signaling (Reusing the Same Self-Hosted Server)**:
   - Deploy a lightweight open-source WebRTC relay/SFU (e.g., `MediaMTX` or `LiveKit`) alongside `hbbs`/`hbbr`/`rustdesk-api` on the same VPS, or P2P WebRTC using `coturn` + signaling endpoint.
   - Reuses the same self-hosted server settings configured in RRRemote.
3. **Cross-Platform Viewer**:
   - Any desktop (Windows/macOS/Linux/Omarchy) or Android client opens the "View iOS Screen" tab (or built-in Web viewer) to watch the iOS screen in real time with low latency.

## Milestones
- [x] Phase 1: Self-hosted `hbbs` + `hbbr` + `rustdesk-api`, GitHub Actions CI for Windows/macOS/Linux(Omarchy)/Android/iOS, auto-update, desktop-to-desktop remote control.
- [ ] Phase 2: Add ReplayKit `BroadcastUploadExtension` + WebRTC view-only stream receiver into RRRemote.
