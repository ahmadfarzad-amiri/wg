# Admin Panel

WireGuard admin web panel.

Deployed path: **`/opt/wg/admin-panel/`**

## Install

Use the interactive installer (asks for domain, brand, credentials):

```bash
sudo bash deploy/install-panel-server.sh
```

See **[../deploy/README-DEPLOY.md](../deploy/README-DEPLOY.md)**.

## Run (after install)

```bash
sudo systemctl restart wg-admin-panel
sudo systemctl status wg-admin-panel
```

## Environment

All set in `/etc/wireguard/panel-server.env` during install. See `deploy/config.env.example`.

| Variable | Default |
|----------|---------|
| `WG_DATA_DIR` | `/etc/wireguard` |
| `WG_ADMIN_HOST` | `127.0.0.1` |
| `WG_ADMIN_PORT` | `8090` |
| `WG_ADMIN_BASE` | `/admin` |
| `WG_ADMIN_BRAND` | set at install |
| `WG_EXIT_SSH` | exit server for remote `wg show` |
