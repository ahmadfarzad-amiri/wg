# Performance guide

How to improve **two-hop** WireGuard throughput while keeping the mandatory path:

`device → entry → exit → internet` (websites must see the **exit** IP).

> See [Architecture](ARCHITECTURE.md) for traffic paths and [Operations guide](OPERATIONS.md) for install steps.
> Do **not** treat single-hop / direct mode as the production speed fix.

---

## Quick start

Run on **each** server (entry and exit) after install or upgrade:

```bash
sudo bash deploy/tune-vpn-performance.sh
```

This applies:

- Routing repair (policy table 100, forward rules, `rp_filter`)
- Persistent TCP MSS clamp (`wg-mss-clamp.service`)
- BBR + **64 MB** UDP socket buffers
- Server WireGuard interface MTU (`WG_SERVER_MTU`, default 1420)
- One-shot VPN mode sync on entry (not every minute)

Then measure hops (do not rely only on browser speed tests):

```bash
sudo bash deploy/measure-vpn-bandwidth.sh --role guide
sudo bash deploy/diagnose-vpn.sh --role entry   # on entry
sudo bash deploy/diagnose-vpn.sh --role exit    # on exit
```

From a **connected twohop client**:

```bash
curl -4 https://api.ipify.org   # must show EXIT public IP
```

---

## 1. Fix routing first

Broken routing looks identical to a slow or dead VPN:

```bash
sudo bash deploy/fix-vpn-routing.sh --role entry
sudo bash deploy/fix-vpn-routing.sh --role exit
```

Automatic fixes include:

- Client subnet → `wg-clients` on entry
- Policy routing table **100** for twohop egress via `wg-tunnel`
- `rp_filter=0` on WireGuard interfaces
- Docker `DOCKER-USER` bypass on entry (only if Docker is installed — prefer **no Docker** on VPN hosts)

---

## 2. Measure which hop is slow

A drop from hundreds of Mbps to ~tens of Mbps is usually **path capacity, loss, or ISP shaping** — not “two-hop crypto” alone.

| Test | Where | What it isolates |
|------|--------|------------------|
| Exit → internet | Exit host | Exit plan / peering |
| Entry → exit (public IP, iperf3) | Entry→exit underlay | Provider path between VPS |
| Entry → exit (`10.200.0.1` via tunnel) | `wg-tunnel` | Tunnel MTU/CPU/WG path |
| Client full twohop | Client device | End-to-end production path |
| Optional direct A/B | One test client only | Client↔entry vs full twohop |

Full command list: `deploy/measure-vpn-bandwidth.sh`.

**Interpretation (keep twohop in production):**

- Exit native slow → upgrade exit bandwidth / provider
- Entry↔exit underlay slow → co-locate entry+exit or change peering
- Underlay fast but tunnel slow → MTU/MSS/CPU on servers
- Twohop slow but underlay+tunnel fast → client↔entry (often DPI on WireGuard UDP); keep twohop egress, consider Reality/Hysteria2 for **hop 1 only** (see [Iran protocol strategy](IRAN-PROTOCOL-STRATEGY.md))

Optional **direct** mode (`wg-client set-mode NAME direct`) is for **lab comparison only**. It egresses via the entry IP and is **not** the production architecture.

---

## 3. Server placement (twohop)

| Decision | Recommendation |
|----------|----------------|
| Entry location | Close to **users** (UDP 51820 latency) |
| Exit location | Good egress peering / close to target content |
| Co-location | Same DC/region for entry+exit cuts tunnel RTT while keeping a separate exit IP |
| Entry CPU | Double crypto (decrypt client + encrypt tunnel) — prefer dedicated vCPU |
| Exit bandwidth | All twohop users share exit egress — size for **aggregate** demand |

---

## 4. MTU settings

Defaults written to `/etc/wireguard/entry-server.env` on install:

| Variable | Default | Purpose |
|----------|---------|---------|
| `WG_SERVER_MTU` | 1420 | `wg-clients` / `wg-tunnel` on servers |
| `WG_CLIENT_MTU_TWOHOP` | 1380 | Client configs (twohop) |
| `WG_CLIENT_MTU_DIRECT` | 1420 | Diagnostic direct clients only |
| `WG_CLIENT_MTU` | 1380 | Fallback |

1380 leaves headroom for double WireGuard on a typical 1500 underlay (including mild PPPoE). Raise toward 1420 only after `ping -M do` path tests succeed.

### Change MTU defaults

1. Edit `/etc/wireguard/entry-server.env` (and `WG_SERVER_MTU` on exit env if needed).
2. Re-run `sudo bash deploy/tune-vpn-performance.sh` on both servers (applies server MTU).
3. Renew clients so `.conf` files pick up the new client MTU:
   ```bash
   sudo wg-client renew alice --days 30
   ```

**TCP MSS clamp** is installed as `wg-mss-clamp.service` so it survives reboot.

---

## 5. OS-level tuning

Enabled by default (`WG_ENABLE_BBR=1`, `WG_ENABLE_MSS_CLAMP=1`).

| Setting | Location | Effect |
|---------|----------|--------|
| TCP BBR + fq | `/etc/sysctl.d/99-wg-performance.conf` | Better TCP under loss |
| UDP buffers 64 MB | Same file | Fewer drops under tunnel bursts |
| `netdev_max_backlog` | Same file | Softnet queue depth |
| MSS clamp | `wg-mss-clamp.service` + mangle FORWARD | Avoids blackhole PMTU issues |

Disable if needed:

```bash
WG_ENABLE_BBR=0 WG_ENABLE_MSS_CLAMP=0 sudo bash deploy/tune-vpn-performance.sh
```

---

## 6. What we removed / do not do for speed

| Practice | Status |
|----------|--------|
| Switching production users to **direct** mode | **Not recommended** — breaks exit-IP twohop requirement |
| Calling `sync-vpn-modes` every minute from enforce | **Removed** — sync on mode change / boot / routing fix only |
| 2.5 MB UDP buffers / client MTU 1280 defaults | **Replaced** with 64 MB / 1380 |
| Non-persistent MSS (lost on reboot) | **Fixed** via systemd unit |
| Docker on the VPN datapath | **Avoid** — bypass exists only as a safety net |
| Extra userspace proxies between entry and exit | **Do not add** for “speed” |

---

## 7. Application-level performance

Panel optimisations (status caching, session purge throttle, WAL SQLite) reduce control-plane load. They are **not** on the WireGuard forward path.

Quota enforcement (`wg-client-enforce.timer`) still runs every minute for expiry / data limits / single-device locks — it no longer rewrites routing for every client on each tick.

---

## 8. If twohop is still slow after tuning

Keep two hops; change the weak layer:

| Option | Effect | Trade-off |
|--------|--------|-----------|
| Co-locate / upgrade entry↔exit | Raises tunnel ceiling | Provider change |
| Upgrade exit egress plan | Raises shared internet ceiling | Cost |
| Alternate **client→entry** transport (Xray Reality / Hysteria2) when WG UDP is shaped | Often restores speed under DPI | Different client apps; hop 2 stays WG to exit |
| Multi-exit (future) | Capacity split | Not built into panels today |

---

## Related guides

- [Operations guide](OPERATIONS.md) — install and maintenance
- [Admin guide](ADMIN_GUIDE.md) — clients and VPN mode
- [Architecture](ARCHITECTURE.md) — traffic path
- [Iran protocol strategy](IRAN-PROTOCOL-STRATEGY.md) — when WireGuard UDP is shaped
- [deploy/README-DEPLOY.md](../deploy/README-DEPLOY.md) — routing troubleshooting
- [deploy/measure-vpn-bandwidth.sh](../deploy/measure-vpn-bandwidth.sh) — hop bandwidth plan
)