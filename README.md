# WireGuard Access Panels

Client and admin web panels for a **two-hop VPN** stack:

```
devices  →  entry VPS (wg-clients + panels)  →  encrypted tunnel  →  exit VPS  →  internet
```

**Repository:** [github.com/ahmadfarzad-amiri/wg](https://github.com/ahmadfarzad-amiri/wg)

Fresh install on clean entry and exit servers.

---

## Install order

On **each** server, install the operator CLI once:

```bash
curl -fsSL https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@main/deploy/wg-ops \
  -o /usr/local/bin/wg-ops && sudo chmod 755 /usr/local/bin/wg-ops
sudo wg-ops pull
```

### 1. Exit VPS first

Interactive menu: `sudo wg-ops` → **1. Install exit server**

Or non-interactive:

```bash
sudo WG_EXIT_PUBLIC_IP=YOUR_EXIT_IP wg-ops install-exit
```

Save the **tunnel public key** and **exit IP:51821** printed at the end.

### 2. Entry VPS second

Interactive menu: `sudo wg-ops` → **2. Install entry server**

Or non-interactive:

```bash
sudo WG_ENTRY_PUBLIC_IP=YOUR_ENTRY_IP \
  WG_EXIT_PUBLIC_IP=YOUR_EXIT_IP \
  WG_EXIT_TUNNEL_PUB='PASTE_EXIT_TUNNEL_PUBKEY' \
  WG_ADMIN_PASS='your-admin-password' \
  WG_XRAY_REALITY_SNI=www.microsoft.com \
  wg-ops install-entry
```

Save the **entry tunnel public key** printed at the end.

> Full env var list: `/opt/wg-ops/config.env.example` (after `wg-ops pull`), or https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@main/deploy/config.env.example

### 3. Link the tunnel on the exit VPS

```bash
sudo wg-ops add-peer 'ENTRY_TUNNEL_PUBKEY' 'ENTRY_PUBLIC_IP'
```

Or menu → **27. Add entry peer**.

---

## After install

| Item | Value |
|------|-------|
| Client panel URL | `http://ENTRY_IP:8088/login` |
| Admin panel URL | `http://ENTRY_IP:8090/admin/login` |
| VPN endpoint for users | `ENTRY_IP:51820` |
| Internet exit | Exit VPS (**twohop** production default) |

### Cloud firewall

| Server | Open |
|--------|------|
| Entry | UDP **51820** (all users share this port), TCP **80/443** (optional, for HTTPS) |
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
sudo wg-ops update          # scripts + panels + tools
sudo wg-ops test --role entry
sudo wg-ops uninstall       # full remove on this host
sudo wg-ops status
```

> WireGuard’s native tool remains `wg` (e.g. `sudo wg show`).

### Change entry or exit server

```bash
sudo wg-ops change-entry --old OLD_IP --new NEW_IP:51820
sudo WG_EXIT_PUBLIC_IP=NEW_EXIT_IP WG_EXIT_TUNNEL_PUB='...' wg-ops change-exit
```

Or use **Admin panel → Tools**.

### Per-client VPN mode

| Mode | Egress IP | Use when |
|------|-----------|----------|
| `twohop` (default) | Exit VPS | **Production** — required architecture |
| `direct` | Entry VPS | Diagnostic A/B only (not a speed fix) |

```bash
sudo wg-client set-mode alice twohop
sudo wg-client set-mode alice direct   # diagnostic only
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
| **[docs/README.md](docs/README.md)** | Documentation index |
| **[docs/USER_GUIDE.md](docs/USER_GUIDE.md)** | VPN users (client panel) |
| **[docs/ADMIN_GUIDE.md](docs/ADMIN_GUIDE.md)** | Administrators (admin panel) |
| **[docs/OPERATIONS.md](docs/OPERATIONS.md)** | Server install, ops, troubleshooting |
| **[docs/PERFORMANCE.md](docs/PERFORMANCE.md)** | Two-hop throughput — MTU, BBR, hop measurements |
| **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** | How the two-hop stack works |
| **[docs/FRESH_DEPLOYMENT.md](docs/FRESH_DEPLOYMENT.md)** | Clean entry/exit install procedure |
| **[deploy/README-DEPLOY.md](deploy/README-DEPLOY.md)** | Detailed script reference |
