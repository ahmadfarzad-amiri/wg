# WireGuard Access Panels

Client and admin web panels for managing WireGuard VPN users.

## Projects

| Directory | Description |
|-----------|-------------|
| `client-panel/` | User login, config download, QR code, requests |
| `admin-panel/` | Client/user management, online list, approvals |
| `deploy/` | Production install scripts (two-server setup) |

## Production deployment

See **[deploy/README-DEPLOY.md](deploy/README-DEPLOY.md)** for the full guide.

**Exit server (outside Iran):**

```bash
sudo bash deploy/install-exit-server.sh
```

**Panel server (inside Iran):**

```bash
sudo bash deploy/install-panel-server.sh
```

**Test connectivity:**

```bash
bash deploy/test-connectivity.sh --role exit   # on exit server
bash deploy/test-connectivity.sh --role panel  # on panel server
```

## Requirements

- Python 3 (stdlib only)
- Linux servers (Debian/Ubuntu recommended)
- WireGuard on exit server
- `wg-client` and related tools in `client-panel/bin/` → `/usr/local/bin`

## Data paths (production)

| Path | Purpose |
|------|---------|
| `/etc/wireguard/wg-ir.conf` | WireGuard server config (exit server) |
| `/etc/wireguard/client-state/` | Client metadata |
| `/etc/wireguard/clients/` | Client `.conf` files |
| `/etc/wireguard/panel.db` | User database (panel server) |
| `/etc/wireguard/admin-panel.json` | Admin login (panel server) |
| `/opt/wg/client-panel/` | Client panel code |
| `/opt/wg/admin-panel/` | Admin panel code |

## Pack tarball (alternative to git clone on server)

```bash
bash client-panel/deploy/export-bundle.sh wg-production.tar.gz
```
