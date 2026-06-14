# Protocol Strategy for Iran and Restricted Networks

## Why WireGuard Often Fails from Iran

WireGuard uses **UDP exclusively** and produces a distinctive Noise Protocol
handshake pattern (148-byte initiation packet). Iranian ISPs run deep packet
inspection (DPI) equipment that can detect and block this pattern in under a
second. Additionally:

- UDP port 51820 appears on automated block-lists used by multiple Iranian ISPs.
- DNS servers `1.1.1.1` and `8.8.8.8` are often blocked or rate-limited for
  UDP/53 queries, so even a working tunnel cannot resolve hostnames.
- A single blocked IP (no failover) means all users lose access simultaneously.

## Recommended Protocol Stack (Best → Fallback)

### 1. VLESS + Reality (Xray-core) — **Best choice**

| Property | Value |
|---|---|
| DPI resistance | Excellent |
| Iran suitability | Excellent |
| Speed | High |
| Blocks the IP? | Survives — looks like HTTPS to `sni` domain |
| CDN support | Not needed (direct) |
| Port | 443/TCP |

**How it works:** Xray's Reality extension re-uses a real TLS 1.3 certificate
from a popular domain you configure as `serverName` (e.g. `www.microsoft.com`).
The DPI inspector sees a standard TLS handshake to that domain. Without the
correct private key (which only your Xray server holds), the handshake is
indistinguishable from legitimate HTTPS traffic at the wire level.

**Install:**
```bash
sudo WG_XRAY_REALITY_SNI=www.microsoft.com bash deploy/install-xray.sh
```

**Add a client:**
```bash
sudo bash deploy/xray-client-add.sh USERNAME
```

**Client apps (in order of recommendation):**
- iOS: Hiddify, Streisand
- Android: Hiddify, v2rayNG, NekoBox
- Windows: Hiddify, v2rayN, Nekoray
- macOS: Hiddify, V2Box, Clash Verge Rev
- Linux: Hiddify, v2rayA, sing-box CLI

---

### 2. VLESS + WebSocket + TLS behind Cloudflare CDN — **Best when IP is blocked**

| Property | Value |
|---|---|
| DPI resistance | Excellent |
| Iran suitability | Excellent (even if server IP is blocked) |
| Speed | Moderate (CDN routing adds 30-80ms) |
| Blocks the IP? | IP block is bypassed via CDN |
| CDN support | Required (Cloudflare Free works) |
| Port | 443/TCP (via CDN) |

**How it works:** Traffic goes to Cloudflare's IP (which is never blocked in
Iran because every major Iranian website uses it). Cloudflare decrypts the TLS,
sees a WebSocket upgrade on `/vless`, and proxies it to your server.

**Setup:**
1. Point a subdomain to your server IP in Cloudflare (enable the orange proxy cloud).
2. Run `install-xray.sh` with `WG_XRAY_WS_DOMAIN=your.subdomain.com`.
3. Use the `nginx-panels-hardened.conf.template` and enable the Xray WebSocket
   block at the bottom.

---

### 3. Hysteria2 — **Best for high bandwidth**

| Property | Value |
|---|---|
| DPI resistance | Good (QUIC/UDP, looks like HTTPS) |
| Iran suitability | Good (UDP must reach server) |
| Speed | Excellent (QUIC multiplex + BBR) |
| Port | 443/UDP |

Hysteria2 is not included in this install script yet. You can install it
separately from [github.com/apernet/hysteria](https://github.com/apernet/hysteria).

---

### 4. Shadowsocks 2022 — **Simple fallback**

| Property | Value |
|---|---|
| DPI resistance | Moderate (no TLS fingerprint) |
| Iran suitability | Moderate |
| Speed | High |
| Port | 8388/TCP+UDP |

Included in `install-xray.sh` as the Shadowsocks inbound (Xray's built-in SS
2022 implementation). No separate installation needed.

---

### 5. WireGuard (existing) — **Keep for users who can reach it**

Some Iranian corporate networks, universities, and mobile ISPs do not block
WireGuard. Keep WireGuard running for these users. Do not remove it.

For users who cannot reach WireGuard from Iran, point them to the Xray client
configs instead.

---

## Choosing the Right SNI for Reality

The Reality `serverName` (SNI) must point to a real HTTPS server that:

1. Is on the same IP block or can be reached from your server (no SNI mismatch).
2. Is not blocked in Iran (otherwise the DPI fingerprint comparison fails).
3. Supports TLSv1.3.
4. Has a high Alexa/Tranco rank (popular sites are less suspicious).

**Good choices:** `www.microsoft.com`, `www.amazon.com`, `www.cloudflare.com`,
`www.apple.com`, `addons.mozilla.org`

**Avoid:** Iranian domains (blocked anyway), domains hosted on the same server
as your VPN (TLS fingerprint mismatch).

---

## DNS Configuration for Iran

Set `WG_DNS` in `/etc/wireguard/entry-server.env` to avoid blocked DNS servers.

**Options ranked by Iran reliability:**

| DNS | Address | Notes |
|---|---|---|
| Exit server local | `EXIT_SERVER_IP` | Best — resolver on your own exit server |
| Google secondary | `8.8.4.4` | Sometimes less filtered than `8.8.8.8` |
| Shecan (Iran) | `178.22.122.100` | Iranian filtered DNS — not recommended |
| 403 Online (Iran) | `10.202.10.202` | Iranian filtered DNS — not recommended |
| AdGuard | `94.140.14.14` | Sometimes reachable |

To run a local resolver on the exit server:
```bash
# On exit server:
apt install unbound -y
systemctl enable --now unbound
# Then set WG_DNS=EXIT_SERVER_IP on entry server
```

---

## Migration Plan for Existing Users

Existing WireGuard users do not need to migrate immediately.

1. Deploy Xray with `install-xray.sh` — WireGuard keeps running untouched.
2. For users who report connection issues from Iran, send them the Xray client
   config link from `xray-client-add.sh`.
3. Over time, direct new users to Xray configs by default.
4. Keep WireGuard active for users who need it (direct mode, mobile data, etc.).

---

## Security Notes

- The Xray server secrets are in `/etc/xray/server-secrets.env` (chmod 600).
  Back this file up — losing the Reality private key means all clients need
  new configs.
- The Shadowsocks password in the same file grants full tunnel access.
  Treat it like a master key.
- Rotate Reality keys quarterly or after any suspected compromise:
  ```bash
  sudo bash deploy/install-xray.sh  # will regenerate keys but preserve client UUIDs
  ```
