# Client Panel

WireGuard user-facing web panel. Runs on the **entry** server (where client devices connect).

**Deployed path:** `/opt/wg/client-panel/`  
**Default URL:** `http://ENTRY_IP:8088/login`

---

## Install (production)

```bash
curl -fsSL https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@latest/deploy/wg-ops \
  -o /usr/local/bin/wg-ops && sudo chmod 755 /usr/local/bin/wg-ops
sudo wg-ops pull

sudo WG_ENTRY_PUBLIC_IP=... WG_EXIT_PUBLIC_IP=... WG_EXIT_TUNNEL_PUB='...' \
  WG_ADMIN_PASS='...' wg-ops install-entry
```

See [../docs/DEPLOYMENT.md](../docs/DEPLOYMENT.md) to install, [../docs/OPERATIONS.md](../docs/OPERATIONS.md) for day-2 ops, and [../docs/USER_GUIDE.md](../docs/USER_GUIDE.md) for end-user instructions.

```bash
sudo wg-ops update          # CDN @latest scripts + panel refresh
```

---

## Run locally (development)

```bash
cd client-panel
PYTHONPATH=.. python3 app.py
```

---

## Manage the service (after production install)

```bash
sudo systemctl status wg-panel
sudo systemctl restart wg-panel
journalctl -u wg-panel -f
```

---

## Environment variables

Set in `/etc/wireguard/entry-server.env` during install. See `/opt/wg-ops/config.env.example` or https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@latest/deploy/config.env.example

| Variable | Default | Purpose |
|----------|---------|---------|
| `WG_DATA_DIR` | `/etc/wireguard` | Root data directory |
| `WG_PANEL_HOST` | `0.0.0.0` | Bind address |
| `WG_PANEL_PORT` | `8088` | Listen port |
| `WG_PANEL_BRAND` | (set at install) | Panel title shown in the header |
| `WG_DEFAULT_ENDPOINT` | `ENTRY_IP:51820` | Fallback endpoint for client configs |

Client configs use the endpoint stored in `/etc/wireguard/wg-endpoint` on the entry server.

---

## Key features

- **Registration and login** — with PBKDF2-SHA256 password hashing; language toggle on login
- **Connect-first dashboard** — download, QR, and copy before usage metrics
- **Config download** — single `.conf` file or ZIP of all assigned configs
- **QR code** — scan directly with the WireGuard mobile app (per-config when multiple)
- **Import / subscription link** (`/sub/TOKEN`) — unauthenticated URL for config import; rotatable from the dashboard
- **Server status** — server-side check of WireGuard interface, exit ping, and DNS (not device connectivity)
- **Support requests** — submit renew/enable requests; track status
- **Optional Xray links** — copy alternative protocol URLs when enabled
- **Bilingual** — Persian (RTL) and English (LTR) with full layout switching
