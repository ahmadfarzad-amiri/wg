# Admin Panel

WireGuard admin web panel. Runs on the **entry** server with the client panel.

Deployed path: **`/opt/wg/admin-panel/`**

## Install

From GitHub (recommended):

```bash
curl -fsSL https://raw.githubusercontent.com/ahmadfarzad-amiri/wg/main/deploy/install-entry-server.sh | sudo bash
```

From a cloned repo:

```bash
sudo bash deploy/install-entry-server.sh
```

See **[../deploy/README-DEPLOY.md](../deploy/README-DEPLOY.md)** and **[../docs/ADMIN_GUIDE.md](../docs/ADMIN_GUIDE.md)**.

## Run locally (development)

```bash
cd admin-panel
PYTHONPATH=. python3 app.py
```

## Run (after install)

```bash
sudo systemctl restart wg-admin-panel
```

```bash
sudo systemctl status wg-admin-panel
```

## Environment

Set in `/etc/wireguard/entry-server.env` during install. See `deploy/config.env.example`.

| Variable | Default |
|----------|---------|
| `WG_DATA_DIR` | `/etc/wireguard` |
| `WG_IF` | `wg-clients` |
| `WG_ADMIN_HOST` | `127.0.0.1` |
| `WG_ADMIN_PORT` | `8090` |
| `WG_ADMIN_BASE` | `/admin` |
| `WG_ADMIN_BRAND` | set at install |

The admin panel reads live client status from local `wg show wg-clients` on the entry server.
