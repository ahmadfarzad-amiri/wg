# WireGuard panels

| Path | Service | Port |
|------|---------|------|
| `client-panel/` | `wg-panel.service` | 8088 |
| `admin-panel/` | `wg-admin-panel.service` | (see admin config) |

## Client panel

```bash
python3 /opt/wg/client-panel/app.py
```

## Admin panel

```bash
python3 /opt/wg/admin-panel/admin_app.py
```

Shared data: `/etc/wireguard/panel.db`
