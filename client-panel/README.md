# Client Panel

WireGuard client web panel (structured layout).

Deployed path: **`/opt/wg/client-panel/`** (see `deploy/migrate-to-opt-wg.sh`).

## Repo layout under `/opt/wg`

```
/opt/wg/
├── client-panel/          ← this project
└── admin-panel/
```

## Package layout

```
client-panel/
├── app.py                 # entry point
├── static/                # CSS, JS, fonts
└── client_panel/
    ├── config/            # settings (env, paths)
    ├── db/                # SQLite
    ├── core/              # auth, wireguard, labels
    ├── components/        # layout, modals, forms, status
    ├── views/             # one file per page
    ├── actions/           # POST handlers (server actions)
    └── server/            # HTTP handler, session, responses
```

## Run

Production (systemd):

```bash
sudo systemctl restart wg-panel
sudo systemctl status wg-panel
```

Direct on the server (needs root for `/etc/wireguard/panel.db`):

```bash
sudo python3 /opt/wg/client-panel/app.py
```

### Localhost access

The app listens on `0.0.0.0:8088` by default, so on the server:

- **Direct:** http://127.0.0.1:8088/login
- **Via nginx (port 80):** run once as root:

```bash
sudo bash /opt/wg/client-panel/deploy/enable-localhost-nginx.sh
```

Then open http://localhost/login or http://127.0.0.1/login

Systemd: `ExecStart=/usr/bin/python3 /opt/wg/client-panel/app.py`

## Deploy

From the repo root:

```bash
bash client-panel/deploy/export-bundle.sh wg-production.tar.gz
```

Copy to the server and extract under `/opt/wg/`. Shared data lives in `/etc/wireguard/` (`panel.db`, client configs, WireGuard server config).

## Environment

| Variable | Default |
|----------|---------|
| `WG_DATA_DIR` | `/etc/wireguard` |
| `WG_BIN_DIR` | `/usr/local/bin` |
| `WG_PANEL_HOST` | `0.0.0.0` |
| `WG_PANEL_PORT` | `8088` |
| `WG_IF` | `wg-ir` |
| `WG_PANEL_BRAND` | `BSLA Access` |
