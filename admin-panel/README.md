# Admin Panel

WireGuard admin web panel (structured layout, mirrors client-panel architecture).

Deployed path: **`/opt/wg/admin-panel/`**

## Layout

```
/opt/wg/
├── client-panel/
└── admin-panel/          ← this project
    ├── app.py
    ├── static/
    └── admin_panel/
        ├── config/
        ├── db/
        ├── core/
        ├── components/
        ├── views/
        ├── actions/
        └── server/
```

## Run

Production (systemd):

```bash
sudo systemctl restart wg-admin-panel
sudo systemctl status wg-admin-panel
```

Direct (localhost only):

```bash
sudo python3 /opt/wg/admin-panel/app.py
```

Public URL: **https://access.bsla.dev/admin/** (nginx → `127.0.0.1:8090`)

## Deploy

From the repo root on your build machine:

```bash
bash client-panel/deploy/export-bundle.sh wg-production.tar.gz
```

Copy to the server and extract under `/opt/wg/`. WireGuard CLI tools (`wg-client`, etc.) must be installed in `/usr/local/bin` with data in `/etc/wireguard`.

## Environment

| Variable | Default |
|----------|---------|
| `WG_DATA_DIR` | `/etc/wireguard` |
| `WG_BIN_DIR` | `/usr/local/bin` |
| `WG_ADMIN_HOST` | `127.0.0.1` |
| `WG_ADMIN_PORT` | `8090` |
| `WG_ADMIN_BASE` | `/admin` |
| `WG_IF` | `wg-ir` |
| `WG_ADMIN_DEFAULT_DAYS` | `30` |
| `WG_ADMIN_DEFAULT_LIMIT` | `20G` |

## Pages

- **داشبورد** — overview KPIs
- **کلاینت‌ها** — add/enable/disable/renew/remove WireGuard clients
- **کاربران** — approve/reject registered users
- **درخواست‌ها** — process renewal/enable requests
- **آنلاین** — active connections + disconnect
- **ابزارها** — enforce, restart client panel, import configs
- **تنظیمات** — change admin password, logout
