# WireGuard Access Panels

Client and admin web panels for a WireGuard VPN that can run as:

- **Two-hop** — entry + exit (tunnel); Standard and Direct paths available
- **Standalone** — entry only (no exit); Direct path only (websites see the entry IP)

```
# Two-hop
devices  →  entry VPS (wg-clients + panels)  →  tunnel  →  exit VPS  →  internet

# Standalone
devices  →  entry VPS (wg-clients + panels + NAT)  →  internet
```

**Repository:** [github.com/ahmadfarzad-amiri/wg](https://github.com/ahmadfarzad-amiri/wg)

Fresh install on clean servers. Full walkthrough: **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)**.

---

## Install (short)

On **each** server:

```bash
curl -fsSL https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@v1.0.20/deploy/wg-ops \
  -o /usr/local/bin/wg-ops && sudo chmod 755 /usr/local/bin/wg-ops
sudo wg-ops pull
```

Scripts are served from a **pinned** jsDelivr tag (`@v1.0.20`). If update is stuck on an old release, force:  
`sudo WG_RAW_BASE='https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@v1.0.20' wg-ops pull`

### Two-hop (entry + exit)

1. **Exit first:** `sudo WG_EXIT_PUBLIC_IP=YOUR_EXIT_IP wg-ops install-exit` — save the tunnel public key  
2. **Entry second:** set `WG_ENTRY_PUBLIC_IP`, `WG_EXIT_PUBLIC_IP`, `WG_EXIT_TUNNEL_PUB`, `WG_ADMIN_PASS`, then `wg-ops install-entry` — save the entry tunnel public key  
3. **Link on exit:** `sudo wg-ops add-peer 'ENTRY_TUNNEL_PUBKEY' 'ENTRY_PUBLIC_IP'`

### Standalone (entry only)

```bash
sudo WG_ENTRY_PUBLIC_IP=YOUR_ENTRY_IP \
  WG_ADMIN_PASS='ADMIN_PASSWORD' \
  wg-ops install-entry
```

Omit `WG_EXIT_*`. Clients use **direct** egress (entry public IP). Attach an exit later with `sudo wg-ops change-exit`.

Or use `sudo wg-ops` (role-aware menu) on each host.

---

## After install

| Item | Value |
|------|-------|
| Client panel URL | `http://ENTRY_IP:8088/login` |
| Admin panel URL | `http://ENTRY_IP:8090/admin/login` |
| VPN endpoint for users | `ENTRY_IP:51820` |
| Internet exit (two-hop) | Exit VPS (**twohop** default) |
| Internet exit (standalone) | Entry VPS (**direct** only) |

### Cloud firewall

| Server | Open |
|--------|------|
| Entry | UDP **51820** (all users share this port), TCP **80/443** (optional, for HTTPS); UDP **51822** if using a tunnel |
| Exit | UDP **51821** — restrict to entry server egress IP when possible |

---

## What users get

- **WireGuard config download** — as `.conf` file or ZIP (multiple configs)
- **QR code** — scan with WireGuard mobile app directly from the dashboard
- **Subscription link** — share a URL for automatic config imports in compatible apps
- **Connection test** — checks WireGuard interface, exit server reachability, and DNS from the Support page
- **Support requests** — submit renew or enable requests; admin handles them in the admin panel

---

## Admin features

- **Approve users and assign configs** — single or bulk
- **Bulk client creation** — create up to 50 clients at once from the Clients tab
- **Xray protocol management** — VLESS+Reality, WebSocket, and Shadowsocks 2022 via the Xray tab
- **Audit log** — every admin action recorded with username, IP, and timestamp
- **Server tools** — change entry/exit IP from the panel UI or CLI

---

## Common operations

```bash
sudo wg-ops                 # interactive menu
sudo wg-ops pull            # refresh scripts from pinned CDN tag
sudo wg-ops update          # pull + panels/tools
sudo wg-ops test --role entry
sudo wg-ops uninstall       # full remove on this host
sudo wg-ops status
```

> WireGuard’s native tool remains `wg` (e.g. `sudo wg show`).
> Day-2 update details: [docs/OPERATIONS.md](docs/OPERATIONS.md).

### Change entry or exit server

```bash
sudo wg-ops change-entry --old OLD_IP --new NEW_IP:51820
sudo WG_EXIT_PUBLIC_IP=NEW_EXIT_IP WG_EXIT_TUNNEL_PUB='...' wg-ops change-exit
```

Or use **Admin panel → Tools**.

### Per-client VPN mode

| Mode | Egress IP | When |
|------|-----------|------|
| `twohop` | Exit VPS | Default when an exit is configured |
| `direct` | Entry VPS | Default when standalone; also available with an exit |

```bash
sudo wg-client set-mode CLIENT_NAME twohop   # needs exit
sudo wg-client set-mode CLIENT_NAME direct
sudo wg-client sync-vpn-modes
```

### Uninstall

```bash
sudo wg-ops uninstall
# or: sudo WG_UNINSTALL_CONFIRM=yes wg-ops uninstall
```

---

## Documentation

| Guide | Audience |
|-------|----------|
| **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** | First-time install (step by step) |
| **[docs/OPERATIONS.md](docs/OPERATIONS.md)** | Backup, update, troubleshoot, uninstall |
| **[docs/README.md](docs/README.md)** | Documentation index |
| **[docs/USER_GUIDE.md](docs/USER_GUIDE.md)** | VPN users (client panel) |
| **[docs/ADMIN_GUIDE.md](docs/ADMIN_GUIDE.md)** | Administrators (admin panel) |
| **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** | How the two-hop stack works |
