# Two-hop packet path and performance assessment

## Current architecture

```mermaid
flowchart LR
  C[Client device] -->|WG UDP 51820| E[Entry wg-clients]
  E -->|policy table 100| T[Entry wg-tunnel]
  T -->|WG UDP 51821| X[Exit wg-tunnel]
  X -->|MASQUERADE| I[Internet]
  I -->|return| X
  X --> T
  T --> E
  E --> C
```

| Hop | Interface | Encryption | NAT |
|-----|-----------|------------|-----|
| Client → entry | `wg-clients` | WireGuard (1) | None |
| Entry → exit | `wg-tunnel` | WireGuard (2) | None on entry |
| Exit → internet | WAN (`eth0`/…) | None | MASQUERADE client CIDR |

Panels (Python) and optional Xray run on the entry **control plane** only. They are not in the WireGuard forward path when disabled/unused.

## Packet path (detail)

1. **Client → entry:** UDP to `ENTRY:51820`. Kernel WireGuard decrypts on `wg-clients`.
2. **Entry routing:** `from CLIENT_CIDR lookup 100` → `default dev wg-tunnel`. No mark required.
3. **Entry firewall:** ACCEPT `wg-clients→wg-tunnel` and reverse; DROP `wg-clients→WAN` (anti-leak). MSS clamp on FORWARD.
4. **Entry→exit tunnel:** Encrypt on `wg-tunnel` to exit (`Table = off` so AllowedIPs `0.0.0.0/0` does not steal host routes).
5. **Exit decrypt:** `wg-tunnel` receives inner packets still sourced from `10.10.10.0/24`.
6. **Exit forward + NAT:** Route to WAN; `MASQUERADE -s CLIENT_CIDR -o WAN`.
7. **Return:** Reverse path; entry `rp_filter=0` on WG ifaces for asymmetric policy routing.

## Root causes of severe throughput loss (~18 Mbps vs ~400 Mbps native)

Observed / structural bottlenecks in this codebase (not mutually exclusive):

| Cause | Effect | Fix in this branch |
|-------|--------|--------------------|
| Duplicate iptables NAT/FORWARD/MSS from PostUp `-A` + repair scripts | Extra netfilter traversal, hard-to-reason state | Idempotent `-C \|\| -A`, migrate dedupe |
| Broad `FORWARD -i wg-clients -j ACCEPT` | Accidental WAN path / unclear policy | Route-only clients PostUp; narrow ACCEPT |
| Missing/weak anti-leak on entry | Direct egress if policy rule missing | DROP client→WAN; direct mode inserts ACCEPT |
| MSS clamp lost on reboot / duplicated | TCP blackholes / odd throughput | `wg-mss-clamp.service` + single-rule enforce |
| Undersized UDP buffers / no BBR check | Burst drops, poor TCP | 64MB max buffers, BBR if module exists |
| `rmem_default=16MB` | RAM pressure on small VPS | Only raise *max* buffers |
| Docker on VPN host | Extra DOCKER-USER hops | Detect/warn; bypass only if present |
| Control-plane churn (`sync-vpn-modes` every minute) | Was removed earlier | Keep sync on mode change / migrate only |
| Path/ISP/CPU limits | Real ceiling independent of config | Hop measurement guide — not “switch to direct” |

Double WireGuard crypto is expected overhead but does **not** alone explain ~20× loss when underlay is healthy; measure each hop.

## Feature classification

| Feature | Action |
|---------|--------|
| Two-hop WG + policy table 100 | **Keep** (production) |
| Exit-only internet NAT | **Keep** |
| Direct mode | **Keep diagnostic-only** |
| Xray/Hysteria/Reality | **Optional**, off WG datapath |
| Docker forward unit | **Keep as safety net**, prefer no Docker |
| Broad clients FORWARD | **Remove** |
| `install_exit_proxy_nginx` | **Removed** (panels on entry only) |
| Legacy sysctl append to `/etc/sysctl.conf` | **Replace** with managed drop-ins |

## Target dataplane (after this work)

- One client→entry WG hop + one entry→exit WG hop  
- NAT only on exit for twohop clients  
- Minimal FORWARD rules, idempotent  
- Configurable MTU (`WG_SERVER_MTU` / `WG_TUNNEL_MTU` / `WG_CLIENT_MTU_TWOHOP`)  
- MSS clamp-to-PMTU  
- Validated install + migrate path + read-only diagnostics  
