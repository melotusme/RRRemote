#!/usr/bin/env python3
"""
RRRemote P2P / Same-LAN Direct Fast-Path Patches.

Solves same-LAN connections falling back to WAN relay under carrier-grade NAT (CGNAT)
multi-IP pools or symmetric NAT (`nat_type = 2`), where `hbbs` sees different public
IPs for two devices on the same LAN and skips `FetchLocalAddr` (`is_local = false`).

Patches applied idempotently to upstream RustDesk 1.5.3:
1. `src/lan.rs`: Add `pub fn probe_lan_peer_ip(peer_id: &str, timeout_ms: u64) -> Option<IpAddr>`
   which broadcasts (and unicasts to any cached `LanPeers` IPs for `peer_id`) a standard
   `PeerDiscovery("ping")` over physical non-TUN interfaces and returns the source IP only
   upon receiving a live `PeerDiscovery("pong")` with an exact `p.id == peer_id` match.
2. `src/client.rs`: In `Client::_start()`, before contacting `hbbs`, run the live LAN
   probe (<=300ms) for numeric peer IDs when not force-relay/proxy/other_server and
   `enable-lan-discovery` is enabled. On match, attempt direct TCP to the peer's
   `direct-access-port` (default `:21118`) with a tight 1200ms timeout (`stream_type = "LAN"`).
   Any failure or timeout falls back seamlessly to the normal `hbbs` rendezvous/P2P/relay flow.
3. `src/client/io_loop.rs` & `src/port_forward.rs`: Treat `stream_type == "LAN"` like
   `is_direct_ip_access` for the insecure-connection confirmation gate, avoiding a
   spurious confirmation dialog on live-verified same-LAN direct sessions.
"""

from __future__ import annotations

from pathlib import Path


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8", newline="\n")


LAN_PROBE_FN = """
/// Fast, live-verified LAN peer IP lookup by peer ID.
///
/// Broadcasts (and unicasts to any cached `LanPeers` IPs for `peer_id`) a standard
/// `PeerDiscovery("ping")` on physical non-TUN interfaces and returns the source IP as
/// soon as a `PeerDiscovery("pong")` with an exact `p.id == peer_id` match arrives.
///
/// Live verification prevents misconnecting to a recycled DHCP IP on another LAN, and
/// discovers same-LAN peers even when `LanPeers` has never been populated or CGNAT
/// multi-IP prevents `hbbs` from setting `is_local = true`.
pub fn probe_lan_peer_ip(peer_id: &str, timeout_ms: u64) -> Option<IpAddr> {
    let target_id = peer_id.trim();
    if target_id.is_empty() || target_id == Config::get_id().as_str() {
        return None;
    }

    let sockets = create_broadcast_sockets();
    if sockets.is_empty() {
        return None;
    }

    let mut msg_out = Message::new();
    msg_out.set_peer_discovery(PeerDiscovery {
        cmd: "ping".to_owned(),
        id: "".to_owned(),
        ..Default::default()
    });
    let out = match msg_out.write_to_bytes() {
        Ok(b) => b,
        Err(_) => return None,
    };

    let bcast_port = get_broadcast_port();
    let bcast_addr = SocketAddr::from(([255, 255, 255, 255], bcast_port));

    // Collect cached LAN candidate IPs for `target_id` (if any) for unicast fallback on
    // Wi-Fi networks that isolate broadcast traffic.
    let mut cached_ips: Vec<IpAddr> = Vec::new();
    for peer in &config::LanPeers::load().peers {
        if peer.id == target_id {
            for ip_str in peer.ip_mac.keys() {
                if let Ok(ip) = ip_str.trim().parse::<IpAddr>() {
                    if !ip.is_loopback()
                        && !ip.is_unspecified()
                        && !hbb_common::config::is_tun_fake_ip(&ip)
                        && !cached_ips.contains(&ip)
                    {
                        cached_ips.push(ip);
                    }
                }
            }
        }
    }

    for socket in &sockets {
        let _ = socket.set_nonblocking(true);
        let _ = socket.send_to(&out, bcast_addr);
        for ip in &cached_ips {
            let _ = socket.send_to(&out, SocketAddr::new(*ip, bcast_port));
        }
    }

    let deadline = Instant::now() + std::time::Duration::from_millis(timeout_ms.max(50));
    let mut buf = [0u8; 2048];
    while Instant::now() < deadline {
        for socket in &sockets {
            while let Ok((len, addr)) = socket.recv_from(&mut buf) {
                if let Ok(msg_in) = Message::parse_from_bytes(&buf[..len]) {
                    if let Some(rendezvous_message::Union::PeerDiscovery(p)) = msg_in.union {
                        if p.cmd == "pong" && p.id == target_id {
                            let ip = addr.ip();
                            if !ip.is_loopback()
                                && !ip.is_unspecified()
                                && !hbb_common::config::is_tun_fake_ip(&ip)
                            {
                                return Some(ip);
                            }
                        }
                    }
                }
            }
        }
        std::thread::sleep(std::time::Duration::from_millis(5));
    }
    None
}
"""


def _patch_lan_rs(root: Path) -> None:
    lan_rs = root / "src" / "lan.rs"
    if not lan_rs.exists():
        raise FileNotFoundError(f"Expected {lan_rs}")
    txt = _read_text(lan_rs)
    if "pub fn probe_lan_peer_ip(" in txt:
        print("[rrremote] probe_lan_peer_ip() already patched in src/lan.rs.")
        return

    anchor = "pub async fn discover() -> ResultType<()> {"
    if anchor not in txt:
        raise RuntimeError("Failed to locate discover() in src/lan.rs")

    txt = txt.rstrip() + "\n" + LAN_PROBE_FN.lstrip("\n")
    _write_text(lan_rs, txt)
    print("[rrremote] Added live-verified probe_lan_peer_ip() to src/lan.rs.")


def _patch_client_rs(root: Path) -> None:
    client_rs = root / "src" / "client.rs"
    if not client_rs.exists():
        raise FileNotFoundError(f"Expected {client_rs}")
    txt = _read_text(client_rs)
    if "crate::lan::probe_lan_peer_ip(" in txt:
        print("[rrremote] Same-LAN direct fast-path already patched in src/client.rs.")
        return

    old_block = """        let (peer, other_server, key, token) = if let Some((a, b, c)) = other_server.as_ref() {
            (a.as_ref(), b.as_ref(), c.as_ref(), "")
        } else {
            (peer, "", key, token)
        };
        let (rendezvous_server, servers, contained) = if other_server.is_empty() {"""

    new_block = """        let (peer, other_server, key, token) = if let Some((a, b, c)) = other_server.as_ref() {
            (a.as_ref(), b.as_ref(), c.as_ref(), "")
        } else {
            (peer, "", key, token)
        };

        // RRRemote: Same-LAN direct fast-path independent of hbbs public-IP equality.
        // Under carrier-grade NAT (CGNAT) multi-IP pools, same-LAN peers often register
        // different public IPs on hbbs (`is_local = false`) and fall back to WAN relay.
        // Live-verify the peer ID via LAN UDP discovery (<=300ms) and dial its direct
        // port (default :21118) with a tight 1200ms timeout, falling back seamlessly to
        // normal hbbs rendezvous/P2P/relay on any failure.
        if other_server.is_empty()
            && !interface.is_force_relay()
            && !Config::is_proxy()
            && config::option2bool(
                "enable-lan-discovery",
                &Config::get_option("enable-lan-discovery"),
            )
        {
            let peer_for_lan = peer.to_owned();
            if let Ok(Some(lan_ip)) =
                tokio::task::spawn_blocking(move || crate::lan::probe_lan_peer_ip(&peer_for_lan, 300))
                    .await
            {
                let direct_port = Config::get_option("direct-access-port")
                    .parse::<u16>()
                    .ok()
                    .filter(|&p| p > 0)
                    .unwrap_or((RELAY_PORT + 1) as u16);
                let lan_target = SocketAddr::new(lan_ip, direct_port);
                match connect_tcp_local(lan_target, None, 1_200).await {
                    Ok(stream) => {
                        log::info!(
                            "LAN direct fast-path connected to {} ({}) bypassing rendezvous/CGNAT",
                            peer,
                            lan_target
                        );
                        return Ok((
                            (stream, true, None, None, "LAN"),
                            (0, "".to_owned()),
                            false,
                        ));
                    }
                    Err(err) => {
                        log::debug!(
                            "LAN direct fast-path to {} ({}) failed ({}), falling back to rendezvous",
                            peer,
                            lan_target,
                            err
                        );
                    }
                }
            }
        }

        let (rendezvous_server, servers, contained) = if other_server.is_empty() {"""

    if old_block not in txt:
        raise RuntimeError("Failed to locate Client::_start() rendezvous anchor in src/client.rs")

    txt = txt.replace(old_block, new_block, 1)
    _write_text(client_rs, txt)
    print("[rrremote] Added same-LAN direct fast-path in src/client.rs::Client::_start().")


def _patch_insecure_gate(root: Path) -> None:
    io_loop_rs = root / "src" / "client" / "io_loop.rs"
    if not io_loop_rs.exists():
        raise FileNotFoundError(f"Expected {io_loop_rs}")
    iotxt = _read_text(io_loop_rs)
    old_io = """                if !is_secured
                    && !crate::common::is_direct_ip_access(&self.handler.get_id())
                    && !client::confirm_insecure_connection(&self.handler, &mut self.receiver).await"""
    new_io = """                if !is_secured
                    && !crate::common::is_direct_ip_access(&self.handler.get_id())
                    && stream_type != "LAN"
                    && !client::confirm_insecure_connection(&self.handler, &mut self.receiver).await"""
    if '&& stream_type != "LAN"' in iotxt:
        print("[rrremote] LAN fast-path gate already patched in src/client/io_loop.rs.")
    elif old_io in iotxt:
        iotxt = iotxt.replace(old_io, new_io, 1)
        _write_text(io_loop_rs, iotxt)
        print("[rrremote] Allowed live-verified LAN fast-path in src/client/io_loop.rs.")
    else:
        raise RuntimeError("Failed to locate confirm_insecure_connection gate in src/client/io_loop.rs")

    pf_rs = root / "src" / "port_forward.rs"
    if not pf_rs.exists():
        raise FileNotFoundError(f"Expected {pf_rs}")
    pftxt = _read_text(pf_rs)
    old_pf = """    let ((mut stream, direct, pk, kcp, _stream_type), (feedback, rendezvous_server)) =
        Client::start(id, key, token, conn_type, interface.clone()).await?;
    let mut trust = crate::trusted_devices::client::Session::new(
        &interface.get_lch().read().unwrap(), stream.is_secured(), pk.as_deref())?;
    interface.update_direct(Some(direct));
    if !stream.is_secured() && !crate::common::is_direct_ip_access(id) {"""
    new_pf = """    let ((mut stream, direct, pk, kcp, stream_type), (feedback, rendezvous_server)) =
        Client::start(id, key, token, conn_type, interface.clone()).await?;
    let mut trust = crate::trusted_devices::client::Session::new(
        &interface.get_lch().read().unwrap(), stream.is_secured(), pk.as_deref())?;
    interface.update_direct(Some(direct));
    if !stream.is_secured() && !crate::common::is_direct_ip_access(id) && stream_type != "LAN" {"""
    if '&& stream_type != "LAN"' in pftxt:
        print("[rrremote] LAN fast-path gate already patched in src/port_forward.rs.")
    elif old_pf in pftxt:
        count = pftxt.count(old_pf)
        pftxt = pftxt.replace(old_pf, new_pf)
        _write_text(pf_rs, pftxt)
        print(f"[rrremote] Allowed live-verified LAN fast-path in src/port_forward.rs ({count} site(s)).")
    else:
        raise RuntimeError("Failed to locate confirm_insecure_connection gate in src/port_forward.rs")


def patch_lan_direct_fastpath(root: Path) -> None:
    """Apply all same-LAN direct fast-path patches idempotently."""
    _patch_lan_rs(root)
    _patch_client_rs(root)
    _patch_insecure_gate(root)
