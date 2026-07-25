# Admin Panel

WireGuard admin web panel. Runs on the **entry** server alongside the client panel.

**Deployed path:** `/opt/wg/admin-panel/`  
**Default URL:** `http://ENTRY_IP:8090/admin/login`

---

## Install (production)

```bash
curl -fsSL https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@v1.0.12/deploy/wg-ops \
  -o /usr/local/bin/wg-ops && sudo chmod 755 /usr/local/bin/wg-ops
sudo wg-ops pull

sudo WG_ENTRY_PUBLIC_IP=... WG_EXIT_PUBLIC_IP=... WG_EXIT_TUNNEL_PUB='...' \
  WG_ADMIN_PASS='...' wg-ops install-entry
```

See [../docs/DEPLOYMENT.md](../docs/DEPLOYMENT.md) to install, [../docs/OPERATIONS.md](../docs/OPERATIONS.md) for day-2 ops, and [../docs/ADMIN_GUIDE.md](../docs/ADMIN_GUIDE.md) for panel usage.

```bash
sudo wg-ops update          # CDN pinned-tag scripts + panel refresh
```

---

## Run locally (development)

```bash
cd admin-panel
PYTHONPATH=.. python3 app.py
```

The admin panel reads live WireGuard status via `wg show wg-clients` on the entry server. In a local dev environment without WireGuard installed, status pages will show "interface down" — this is expected.

---

## Manage the service (after production install)

```bash
sudo systemctl status wg-admin-panel
sudo systemctl restart wg-admin-panel
journalctl -u wg-admin-panel -f
```

---

## Environment variables

Set in `/etc/wireguard/entry-server.env` during install. See `/opt/wg-ops/config.env.example` or https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@v1.0.12/deploy/config.env.example

| Variable | Default | Purpose |
|----------|---------|---------|
| `WG_DATA_DIR` | `/etc/wireguard` | Root data directory |
| `WG_IF` | `wg-clients` | WireGuard interface to monitor |
| `WG_ADMIN_HOST` | `127.0.0.1` | Bind address (nginx reverse-proxied) |
| `WG_ADMIN_PORT` | `8090` | Listen port |
| `WG_ADMIN_BASE` | `/admin` | URL path prefix |
| `WG_ADMIN_BRAND` | (set at install) | Panel title shown in the header |

---

## Key features

- **User management** — approve registrations, assign / unassign WireGuard configs, reset passwords
- **Client management** — create, enable/disable, set data limits and expiry; **Edit** opens a detail page
- **Bulk client creation** — add up to 50 clients at once from the Clients tab
- **Support requests** — approve or reject user renew/enable requests
- **Active connections** — live WireGuard handshake view and disconnect
- **More menu** — Tools (entry/exit + maintenance + audit), Xray, Settings
- **Audit log** — every admin action logged with actor username, source IP, and timestamp (50 recent)
- **Bilingual** — Persian (RTL) and English (LTR); language on login and in the header
