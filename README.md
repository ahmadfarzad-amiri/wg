# WireGuard Access Panels

Client and admin web panels for a **two-hop VPN**:

**devices → entry VPS → encrypted tunnel → exit VPS → internet**

**Official repository:** [github.com/ahmadfarzad-amiri/wg](https://github.com/ahmadfarzad-amiri/wg)

## Install order

### 1. Exit VPS (internet egress)

Non-interactive by default (auto-detects public IP):

```bash
curl -fsSL https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@main/deploy/install-exit-server.sh | sudo bash
```

Or with env vars:

```bash
WG_EXIT_PUBLIC_IP=203.0.113.50 WG_TUNNEL_PORT=51821 \
  curl -fsSL https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@main/deploy/install-exit-server.sh | sudo bash
```

Save the **tunnel public key** and **exit IP:port** printed at the end.

### 2. Entry VPS (clients + panels)

Non-interactive (recommended for automation):

```bash
WG_EXIT_PUBLIC_IP=203.0.113.50 \
WG_EXIT_TUNNEL_PUB='paste-exit-tunnel-pubkey' \
WG_ADMIN_PASS='your-admin-password' \
curl -fsSL https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@main/deploy/install-entry-server.sh | sudo bash
```

Interactive prompts: `WG_INSTALL_INTERACTIVE=1 sudo bash install-entry-server.sh`

See [deploy/config.env.example](deploy/config.env.example) for all env vars.

### 3. Exit VPS — link the tunnel

Copy the **entry tunnel public key** from step 2, then on the exit server:

```bash
curl -fsSL https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@main/deploy/add-entry-peer.sh | \
  sudo bash -s -- ENTRY_TUNNEL_PUBLIC_KEY ENTRY_PUBLIC_IP
```

## What users connect to

| Setting | Value |
|---------|--------|
| WireGuard Endpoint | **Entry server IP:51820** (not the exit server) |
| Web panels | Your domain on the **entry** server |
| Internet exit | **Exit** VPS (NAT) |

## Cloud firewall

| Server | Ports |
|--------|--------|
| Entry | UDP **51820** (clients), TCP **80/443** or panel ports |
| Exit | UDP **51821** (tunnel — restrict to entry IP when possible) |

## Test

```bash
curl -fsSL https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@main/deploy/test-connectivity.sh -o /tmp/test.sh
sudo bash /tmp/test.sh --role exit   # on exit
sudo bash /tmp/test.sh --role entry  # on entry
```

## Operations

```bash
sudo bash deploy/backup.sh
sudo bash deploy/restore.sh /etc/wireguard/backups/TIMESTAMP-label
sudo bash deploy/update-panels.sh   # entry server only
```

### Change entry or exit server

```bash
# New client endpoint (entry public IP:port) for all .conf files
sudo bash deploy/change-entry-server.sh --new 198.51.100.10:51820

# Point wg-tunnel at a new exit VPS (then run add-entry-peer.sh on the new exit)
sudo WG_EXIT_PUBLIC_IP=203.0.113.50 WG_EXIT_TUNNEL_PUB='...' sudo bash deploy/change-exit-server.sh
```

Admin panel: **Tools → Server infrastructure** (same scripts).

### Per-client VPN path (on entry server)

| Mode | Egress IP |
|------|-----------|
| `twohop` (default) | Exit VPS |
| `direct` | Entry VPS |

```bash
sudo wg-client add alice --vpn-mode direct
sudo wg-client set-mode bob twohop
sudo wg-client sync-vpn-modes
```

Users can have **multiple configs** assigned in the admin panel; the client panel downloads all assigned configs as a **ZIP** from Settings.

Full guide: **[deploy/README-DEPLOY.md](deploy/README-DEPLOY.md)**

## Documentation

Step-by-step guides for every role:

| Guide | Audience |
|-------|----------|
| **[docs/README.md](docs/README.md)** | Documentation index |
| **[docs/USER_GUIDE.md](docs/USER_GUIDE.md)** | VPN users (client panel) |
| **[docs/ADMIN_GUIDE.md](docs/ADMIN_GUIDE.md)** | Administrators (admin panel) |
| **[docs/OPERATIONS.md](docs/OPERATIONS.md)** | Server install, backup, migration |
| **[docs/PERFORMANCE.md](docs/PERFORMANCE.md)** | VPN speed tuning (MTU, BBR, direct vs twohop) |
| **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** | How the two-hop stack works |
