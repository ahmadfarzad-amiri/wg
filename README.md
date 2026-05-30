# WireGuard Access Panels

Client and admin web panels for managing WireGuard VPN users.  
**Fully configurable** — domain, IP, brand, and ports are set during install (nothing hardcoded).

## Quick start (two servers)

| Server | Role | Command |
|--------|------|---------|
| Exit (public VPN) | WireGuard + optional reverse proxy | `sudo bash deploy/install-exit-server.sh` |
| Panel (management) | Web UI, SSH to exit for `wg-client` | `sudo bash deploy/install-panel-server.sh` |

One-liner from GitHub (replace `OWNER/REPO`):

```bash
curl -fsSL https://raw.githubusercontent.com/OWNER/REPO/main/deploy/install-exit-server.sh | sudo bash
curl -fsSL https://raw.githubusercontent.com/OWNER/REPO/main/deploy/install-panel-server.sh | sudo bash
```

Full guide: **[deploy/README-DEPLOY.md](deploy/README-DEPLOY.md)**

## What you will be asked

- GitHub repo URL (if not running from a clone)
- **Public IP** and **UDP port** for WireGuard
- **Domain name** for nginx
- **Panel brand** name
- Exit server **SSH** (`user@host`)
- **Admin username / password**
- Optional TLS certificate paths

Client configs use the endpoint written to `/etc/wireguard/wg-endpoint` at install time.

## Projects

| Directory | Description |
|-----------|-------------|
| `client-panel/` | User login, config download, QR, requests |
| `admin-panel/` | Client/user management, online list |
| `deploy/` | Install scripts, nginx templates, examples |

## Test after install

```bash
bash deploy/test-connectivity.sh --role exit   # on exit server
bash deploy/test-connectivity.sh --role panel # on panel server
```

See `deploy/config.env.example` for all environment variables.
