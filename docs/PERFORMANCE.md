# Performance guide

How to improve **two-hop** WireGuard throughput while keeping:

`device → entry → exit → internet` (websites must see the **exit** IP).

> See [Architecture](ARCHITECTURE.md), [Assessment](ASSESSMENT.md), [Fresh deployment](FRESH_DEPLOYMENT.md).
> Do **not** treat single-hop / direct mode as the production speed fix.

---

## Quick start

On **each** server (entry and exit) after install or upgrade:

```bash
sudo bash deploy/migrate-vpn-stack.sh --role auto      # existing installs
sudo bash deploy/tune-vpn-performance.sh
sudo bash deploy/diagnose-vpn.sh --role auto
sudo bash deploy/measure-vpn-bandwidth.sh --role guide
```

From a **connected twohop client**:

```bash
curl -4 https://api.ipify.org   # must show EXIT public IP
```

---

## MTU model (configurable)

WireGuard IPv4 overhead is about **60 bytes** per encapsulation.

| Variable | Default | Meaning |
|----------|---------|---------|
| `WG_SERVER_MTU` | `1420` | Default for server WG interfaces |
| `WG_CLIENTS_MTU` | `WG_SERVER_MTU` | Entry `wg-clients` |
| `WG_TUNNEL_MTU` | `WG_SERVER_MTU` | `wg-tunnel` on entry and exit |
| `WG_CLIENT_MTU_TWOHOP` | `1380` | Client .conf for production |
| `WG_CLIENT_MTU_DIRECT` | `1420` | Diagnostic direct clients only |

On a 1500-byte underlay, two hops imply client payload ≈ `1500 − 60 − 60 = 1380`. Raise toward 1420 only after `ping -M do` / path MTU tests succeed. Valid range enforced by install/validate: **1280–1500**.

TCP MSS uses **clamp-to-PMTU** on FORWARD (`wg-mss-clamp.service`) — one rule, duplicates removed by migrate/tune.

---

## Dataplane simplifications

- Entry `wg-clients` PostUp is **route-only** (no broad FORWARD ACCEPT).
- Forwarding is limited to `wg-clients ↔ wg-tunnel`.
- Entry **anti-leak** DROP for `wg-clients → WAN` (direct mode inserts ACCEPT).
- Internet **NAT only on exit** for the client subnet.
- Idempotent iptables (`-C || -A`) in install PostUp and repair scripts.
- Sysctl via managed files under `/etc/sysctl.d/` (not fragile `sysctl.conf` appends).
- Socket **max** buffers 64MB; defaults left modest to avoid RAM waste.
- BBR enabled only when `tcp_bbr` is available.

---

## Measure which hop is slow

```bash
sudo bash deploy/measure-vpn-bandwidth.sh --role guide
```

| Test | Isolates |
|------|----------|
| Exit → internet | Exit plan / peering |
| Entry → exit public iperf3 | Underlay between VPS |
| Entry → exit via `10.200.0.1` | Tunnel MTU/CPU/WG |
| Client full twohop | Production path |
| Optional direct A/B | Client↔entry vs twohop (lab only) |

Actual Mbps depends on client ISP, VPS CPU, PPS limits, distance, loss, and shaping. This project does **not** claim a fixed throughput number.

---

## Related

- [Operations](OPERATIONS.md) — install / migration  
- [Fresh deployment](FRESH_DEPLOYMENT.md) — clean servers  
- [deploy/diagnose-vpn.sh](../deploy/diagnose-vpn.sh) — HEALTHY/WARNING/FAILED  
- [deploy/migrate-vpn-stack.sh](../deploy/migrate-vpn-stack.sh) — upgrade dataplane  
