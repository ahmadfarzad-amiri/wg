# WireGuard Access Panels

Client and admin web panels for a **two-hop VPN** stack:

```
devices  →  entry VPS (wg-clients + panels)  →  encrypted tunnel  →  exit VPS  →  internet
```

**Repository:** [github.com/ahmadfarzad-amiri/wg](https://github.com/ahmadfarzad-amiri/wg)

---

## Install order

### 1. Exit VPS first

```bash
curl -fsSL https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@main/deploy/install-exit-server.sh \
  -o /tmp/install-exit-server.sh

sudo WG_EXIT_PUBLIC_IP=YOUR_EXIT_IP bash /tmp/install-exit-server.sh
```

Save the **tunnel public key** and **exit IP:51821** printed at the end.

### 2. Entry VPS second

```bash
curl -fsSL https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@main/deploy/install-entry-server.sh \
  -o /tmp/install-entry-server.sh

sudo WG_ENTRY_PUBLIC_IP=YOUR_ENTRY_IP \
  WG_EXIT_PUBLIC_IP=YOUR_EXIT_IP \
  WG_EXIT_TUNNEL_PUB='PASTE_EXIT_TUNNEL_PUBKEY' \
  WG_ADMIN_PASS='your-admin-password' \
  bash /tmp/install-entry-server.sh
```

Save the **entry tunnel public key** printed at the end.

> Interactive mode: add `WG_INSTALL_INTERACTIVE=1` before running. Full env var list: [deploy/config.env.example](deploy/config.env.example).

### 3. Link the tunnel on the exit VPS

Copy the entry tunnel public key from step 2, then on the **exit** server:

```bash
curl -fsSL https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@main/deploy/add-entry-peer.sh \
  -o /tmp/add-entry-peer.sh

sudo bash /tmp/add-entry-peer.sh 'ENTRY_TUNNEL_PUBKEY' 'ENTRY_PUBLIC_IP'
```

---

## After install

| Item | Value |
|------|-------|
| Client panel URL | `http://ENTRY_IP:8088/login` |
| Admin panel URL | `http://ENTRY_IP:8090/admin/login` |
| VPN endpoint for users | `ENTRY_IP:51820` |
| Internet exit | Exit VPS (two-hop, default) or Entry VPS (direct mode) |

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
- **Audit log** — every admin action recorded with username, IP, and timestamp
- **Server tools** — change entry/exit IP from the panel UI or CLI

---

## Common operations

```bash
# Backup
sudo bash deploy/backup.sh

# Restore
sudo bash deploy/restore.sh /etc/wireguard/backups/TIMESTAMP-label

# Update panels (entry server only)
sudo bash deploy/update-panels.sh

# Verify connectivity
sudo bash deploy/test-connectivity.sh --role entry
sudo bash deploy/test-connectivity.sh --role exit

# Tune performance (entry and exit)
sudo bash deploy/tune-vpn-performance.sh
```

### Change entry or exit server

```bash
# New entry IP — rewrites all client .conf files
sudo bash deploy/change-entry-server.sh --new NEW_IP:51820

# New exit VPS (then run add-entry-peer.sh on the new exit)
sudo WG_EXIT_PUBLIC_IP=NEW_EXIT_IP WG_EXIT_TUNNEL_PUB='...' bash deploy/change-exit-server.sh
```

Or use **Admin panel → Tools** for the same operations without SSH.

### Per-client VPN mode

| Mode | Egress IP | Use when |
|------|-----------|----------|
| `twohop` (default) | Exit VPS | User needs privacy, separate egress IP |
| `direct` | Entry VPS | User needs lower latency |

```bash
sudo wg-client set-mode alice direct
sudo wg-client set-mode bob twohop
sudo wg-client sync-vpn-modes
```

---

## Documentation

| Guide | Audience |
|-------|----------|
| **[docs/README.md](docs/README.md)** | Documentation index |
| **[docs/USER_GUIDE.md](docs/USER_GUIDE.md)** | VPN users (client panel) |
| **[docs/ADMIN_GUIDE.md](docs/ADMIN_GUIDE.md)** | Administrators (admin panel) |
| **[docs/OPERATIONS.md](docs/OPERATIONS.md)** | Server install, backup, migration |
| **[docs/PERFORMANCE.md](docs/PERFORMANCE.md)** | Speed tuning — VPN mode, MTU, BBR, app caches |
| **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** | How the two-hop stack works |
| **[deploy/README-DEPLOY.md](deploy/README-DEPLOY.md)** | Detailed script reference |
