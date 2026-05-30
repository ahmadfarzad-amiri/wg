# Client Panel

WireGuard client web panel.

Deployed path: **`/opt/wg/client-panel/`**

## Install

```bash
sudo bash deploy/install-panel-server.sh
```

See **[../deploy/README-DEPLOY.md](../deploy/README-DEPLOY.md)**.

## Environment

Set in `/etc/wireguard/panel-server.env`. See `deploy/config.env.example`.

| Variable | Default |
|----------|---------|
| `WG_DATA_DIR` | `/etc/wireguard` |
| `WG_PANEL_HOST` | `0.0.0.0` |
| `WG_PANEL_PORT` | `8088` |
| `WG_PANEL_BRAND` | set at install |
| `WG_DEFAULT_ENDPOINT` | set at install (WireGuard `IP:port`) |

Client configs read endpoint from `/etc/wireguard/wg-endpoint` on the exit server.
