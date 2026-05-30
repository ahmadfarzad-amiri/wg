# Client Panel

WireGuard client web panel. Runs on the **entry** server (where client devices connect).

Deployed path: **`/opt/wg/client-panel/`**

## Install

From GitHub (recommended):

```bash
curl -fsSL https://raw.githubusercontent.com/ahmadfarzad-amiri/wg/main/deploy/install-entry-server.sh | sudo bash
```

From a cloned repo:

```bash
sudo bash deploy/install-entry-server.sh
```

See **[../deploy/README-DEPLOY.md](../deploy/README-DEPLOY.md)**.

## Environment

Set in `/etc/wireguard/entry-server.env`. See `deploy/config.env.example`.

| Variable | Default |
|----------|---------|
| `WG_DATA_DIR` | `/etc/wireguard` |
| `WG_PANEL_HOST` | `0.0.0.0` |
| `WG_PANEL_PORT` | `8088` |
| `WG_PANEL_BRAND` | set at install |
| `WG_DEFAULT_ENDPOINT` | Entry server `IP:51820` |

Client configs use the endpoint in `/etc/wireguard/wg-endpoint` on the **entry** server.
