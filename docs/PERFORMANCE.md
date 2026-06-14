# Performance guide

How to improve connection speed and reduce server load for the two-hop WireGuard stack.

> See [Architecture](ARCHITECTURE.md) for traffic paths and [Operations guide](OPERATIONS.md) for install steps.

---

## Quick start

Run on **each** server (entry and exit) after install:

```bash
sudo bash deploy/tune-vpn-performance.sh
```

This applies routing repair, TCP MSS clamp, BBR congestion control, UDP buffer sizing, and syncs VPN modes on entry.

Verify from a **connected client device** (not the server itself):

```bash
curl -4 https://api.ipify.org
```

---

## 1. Fix routing first

Broken routing looks identical to a slow or dead VPN. Before tuning anything else:

```bash
# On entry server
sudo bash deploy/fix-vpn-routing.sh --role entry
sudo bash deploy/diagnose-vpn.sh --role entry

# On exit server
sudo bash deploy/fix-vpn-routing.sh --role exit
```

The install scripts and `tune-vpn-performance.sh` apply these automatically. Run `fix-vpn-routing.sh` manually if you change iptables rules or install Docker after initial setup.

Common routing fixes applied automatically:

- Client subnet routed via `wg-clients` on entry
- Policy routing table 100 for twohop egress
- `rp_filter=0` on WireGuard interfaces
- Docker `DOCKER-USER` bypass on entry (if Docker is installed)

---

## 2. VPN mode: speed vs privacy

| Mode | Path | Latency | Egress IP |
|------|------|---------|-----------|
| **direct** | Device → entry → internet | Fastest (single hop) | Entry server |
| **twohop** (default) | Device → entry → tunnel → exit → internet | Extra RTT + CPU | Exit server |

**direct** skips the tunnel entirely — no double encryption, no extra hop.
**twohop** hides the exit server from users and gives a separate egress IP.

### Change VPN mode for a user

**Admin panel:** Clients → select client → VPN mode dropdown.

**CLI on entry server:**

```bash
# Single client
sudo wg-client set-mode alice direct
sudo wg-client set-mode bob twohop

# Apply routing for all clients after bulk changes
sudo wg-client sync-vpn-modes
```

**Verify** from the client device:

```bash
curl -4 https://api.ipify.org
```

- Shows entry IP → `direct` mode is active.
- Shows exit IP → `twohop` mode is active.

---

## 3. Server placement

| Decision | Recommendation |
|----------|----------------|
| Entry location | Close to **your users** — minimises UDP latency on port 51820 |
| Exit location | Good peering or close to **target content**; or co-locate with entry |
| Co-location | Entry + exit in the same datacenter cuts tunnel RTT while keeping separate IPs |
| Entry CPU | More important for `twohop` (entry encrypts traffic twice) |
| Exit bandwidth | All `twohop` users share exit egress — size for aggregate throughput |

If `wg show wg-clients transfer` grows but user speeds plateau, upgrade the VPS tier.

---

## 4. MTU settings

Default values in `/etc/wireguard/entry-server.env`:

| Variable | Default | Mode |
|----------|---------|------|
| `WG_CLIENT_MTU` | 1280 | Fallback |
| `WG_CLIENT_MTU_DIRECT` | 1420 | Single hop |
| `WG_CLIENT_MTU_TWOHOP` | 1280 | Double encapsulation |

`twohop` needs a lower MTU because packets are encapsulated twice.

### Change MTU defaults

1. Edit `/etc/wireguard/entry-server.env`.
2. Create new clients or renew existing ones:
   ```bash
   sudo wg-client renew alice --days 30
   ```

### Override MTU for a single client

```bash
sudo wg-client add bob --vpn-mode direct --mtu 1420
```

**TCP MSS clamp** (enabled by `tune-vpn-performance.sh`) prevents fragmentation when MTU is increased on twohop paths.

---

## 5. OS-level tuning

Enabled automatically during install (`WG_ENABLE_BBR=1`, `WG_ENABLE_MSS_CLAMP=1`).

| Setting | Location | Effect |
|---------|----------|--------|
| TCP BBR | `/etc/sysctl.d/99-wg-performance.conf` | Better throughput under packet loss |
| UDP buffers | Same file (`rmem_max`, `wmem_max`) | Handles burst traffic |
| MSS clamp | `iptables -t mangle … TCPMSS --clamp-mss-to-pmtu` | Avoids IP fragmentation |

### Disable if needed

```bash
WG_ENABLE_BBR=0 WG_ENABLE_MSS_CLAMP=0 sudo bash deploy/tune-vpn-performance.sh
```

Or set `WG_ENABLE_BBR=0` in `entry-server.env` / `exit-server.env` and re-run the tune script.

---

## 6. Application-level performance

The Python panels have several built-in optimisations that reduce server load at scale.

### WireGuard status caching

| Cache | TTL | Protects against |
|-------|-----|-----------------|
| `wg_interface_up()` | 5 s | Repeated `wg show` kernel calls on every page load |
| `wg_map()` (transfer, endpoints, handshakes) | 2 s | O(1) kernel calls per map type |
| `statuses_for_user()` | — | Builds **one** WireGuard snapshot for all clients (3 calls total, not 3 per client) |

All caches use `threading.Lock` for thread safety under `ThreadingHTTPServer`.

### Session purge throttle

`DELETE FROM sessions WHERE expires_at <= ?` runs at most **once per 60 seconds** regardless of traffic. This prevents write-lock storms on the sessions SQLite database under high concurrent load.

### Schema check flag

`ensure_user_configs_schema()` sets a module-level flag after the first successful run — no DDL executes on subsequent DB reads within the same process lifetime.

### Database indexes

Added indexes on high-frequency query columns:

| Table | Column | Query type |
|-------|--------|-----------|
| `sessions` | `expires_at` | Purge and expiry checks |
| `requests` | `user_id` | Per-user request list |
| `requests` | `status` | Pending filter |
| `users` | `status` | Pending/approved filter |
| `audit_log` | `created_at DESC` | Recent entries in Tools tab |

### SQLite WAL mode

All databases (`panel.db`, `audit.db`) open with:
```sql
PRAGMA journal_mode=WAL;
PRAGMA busy_timeout=3000;
```
WAL allows concurrent reads during writes. `busy_timeout=3000` retries for up to 3 seconds before returning "database is locked" — eliminates spurious errors under normal concurrent traffic.

---

## 7. Measure before and after

**From a connected client device** (not the VPS):

```bash
ping -c 20 ENTRY_PUBLIC_IP          # latency baseline
curl -4 https://api.ipify.org       # confirm VPN mode
# Browser: fast.com or speedtest.net for throughput
```

**From the entry server:**

```bash
sudo wg show wg-clients transfer    # per-client TX/RX
sudo wg show wg-tunnel transfer     # tunnel throughput
sudo bash deploy/diagnose-vpn.sh --role entry
```

Compare direct vs twohop for the same user at the same time of day.

---

## 8. Larger architecture options

If the steps above are insufficient:

| Option | Effect | Trade-off |
|--------|--------|-----------|
| All users on **direct** mode | Removes tunnel hop; fastest possible | Exit server unused for egress; entry IP visible |
| **Single VPS** | One WireGuard hop; simplest setup | No separate egress IP |
| **Multi-exit routing** | Different exit per user group | Not built into the panels today |

The built-in per-client `direct` vs `twohop` selection is the recommended compromise.

---

## Related guides

- [Operations guide](OPERATIONS.md) — install and maintenance
- [Admin guide](ADMIN_GUIDE.md) — set VPN mode per client in the admin panel
- [Architecture](ARCHITECTURE.md) — full traffic path and caching details
- [deploy/README-DEPLOY.md](../deploy/README-DEPLOY.md) — routing troubleshooting
