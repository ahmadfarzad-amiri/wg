# /opt/wg layout

Target structure on the entry server:

```
/opt/wg/
├── wg_common/             # shared status, passwords, client status logic
├── client-panel/          # user VPN panel (port 8088)
│   ├── app.py
│   └── client_panel/
└── admin-panel/           # admin panel (port 8090, /admin)
    ├── app.py             # canonical entry point
    └── admin_panel/
```

Shared data: `/etc/wireguard/panel.db`

| Panel | systemd unit | Port |
|-------|--------------|------|
| Client | `wg-panel.service` | 8088 |
| Admin | `wg-admin-panel.service` | 8090 |

## Manual run

```bash
python3 /opt/wg/client-panel/app.py
python3 /opt/wg/admin-panel/app.py
```

`admin-panel/admin_app.py` is a legacy alias for `app.py`.

## One-time migration from old paths

If panels lived under `/opt/wg-panel` or `/opt/wg-admin-panel`:

```bash
sudo bash /opt/wg/client-panel/deploy/migrate-to-opt-wg.sh
```

See **[../../docs/OPERATIONS.md](../../docs/OPERATIONS.md)** for full operator steps.
