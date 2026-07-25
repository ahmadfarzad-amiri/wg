# Operations guide

Day-2 tasks after a successful install. For first-time setup, use the [Deployment guide](DEPLOYMENT.md).

`wg-ops` detects this host’s role (`none` / `entry` / `exit` / `both`) and filters the menu:

```bash
sudo wg-ops              # interactive menu
wg-ops list-menu         # preview without running anything
sudo wg-ops status
```

---

## Common commands

| Goal | Command |
|------|---------|
| Refresh scripts from CDN | `sudo wg-ops pull` |
| Update scripts + panels + tools | `sudo wg-ops update` |
| Update panels only (entry) | `sudo wg-ops update-panels` |
| Test / diagnose / repair | `sudo wg-ops test` · `diagnose` · `fix-routing` |
| Backup | `sudo wg-ops backup` |
| Uninstall this host | `sudo wg-ops uninstall` |

Native WireGuard CLI remains `wg` (example: `sudo wg show`).

---

## Backup

```bash
sudo wg-ops backup
```

Copies go to `/etc/wireguard/backups/TIMESTAMP-label/`.

Back up before changing entry/exit addresses, bulk deletes, or major config edits. To recover a bad edit, restore files from a backup, restart interfaces, then `sudo wg-ops fix-routing`.

---

## Update panels and styles

```bash
sudo wg-ops update-panels
sudo wg-ops update          # scripts + panels + tools
sudo wg-ops styles          # check CSS/JS sync
sudo wg-ops styles --fix
```

After a style fix, hard-refresh the browser (`Ctrl+Shift+R`).

---

## Services (entry)

```bash
sudo wg-ops status
sudo wg-ops restart
sudo wg-ops logs

# Or systemd directly:
sudo systemctl status wg-panel wg-admin-panel
sudo systemctl restart wg-panel wg-admin-panel
journalctl -u wg-panel -u wg-admin-panel -f
```

### 502 Bad Gateway

```bash
sudo journalctl -u wg-panel -n 50 --no-pager
sudo wg-ops update-panels
sudo wg-ops fix-panels
curl -fsS http://127.0.0.1:8088/health
ls -la /opt/wg/wg_common/__init__.py
```

If `wg_common` is missing, run `update-panels` again. If the install is corrupted, uninstall and reinstall from the [Deployment guide](DEPLOYMENT.md).

---

## HTTPS (optional)

1. Point a DNS A record at the entry IP.  
2. During install set `WG_DOMAIN` / `WG_ENABLE_SSL`, or later:

```bash
sudo certbot --nginx -d your-domain.com
```

nginx proxies `8088` (client panel) and `8090` (admin under `/admin`). Panels also work on raw HTTP without a domain.

---

## Change entry or exit server

### Entry IP / port

On **entry**:

```bash
sudo wg-ops change-entry --new NEW_IP:51820
# Optional: --old OLD_IP
```

Or **Admin → Tools → Change entry**. Update cloud firewall and DNS; users must reconnect. Client `.conf` files on disk are rewritten.

### Exit server

On **entry**:

```bash
sudo WG_EXIT_PUBLIC_IP=NEW_EXIT_IP WG_EXIT_TUNNEL_PUB='NEW_EXIT_PUBKEY' \
  wg-ops change-exit
```

On the **new exit**:

```bash
sudo wg-ops add-peer 'ENTRY_TUNNEL_PUBKEY' 'ENTRY_PUBLIC_IP'
```

On the **old exit** (if retiring it): remove the stale peer from `/etc/wireguard/wg-tunnel.conf`, then:

```bash
sudo wg syncconf wg-tunnel /etc/wireguard/wg-tunnel.conf
```

---

## Performance (two-hop)

Keep production clients on **twohop** (exit IP). `direct` mode is for short diagnostic tests only — not a speed fix.

```bash
# On entry and exit
sudo wg-ops tune
sudo wg-ops diagnose --role auto
sudo wg-ops measure --role guide
```

### MTU

WireGuard adds ~60 bytes per hop. Defaults:

| Variable | Default | Meaning |
|----------|---------|---------|
| `WG_SERVER_MTU` | `1420` | Server interfaces |
| `WG_CLIENT_MTU_TWOHOP` | `1380` | Production client configs |
| `WG_CLIENT_MTU_DIRECT` | `1420` | Diagnostic direct clients |

On a 1500-byte path: `1500 − 60 − 60 ≈ 1380`. Raise only after path-MTU tests succeed (valid range **1280–1500**). MSS clamp runs via `wg-mss-clamp.service`.

### Which hop is slow?

`wg-ops measure --role guide` prints a hop-by-hop plan (exit→internet, entry→exit underlay, tunnel, full twohop). Throughput depends on ISP, CPU, distance, and loss — there is no fixed Mbps target.

---

## Troubleshooting: connected but no internet

Symptom: `wg show wg-clients` shows TX/RX, but the client has no web access.

| Check | Where | Expected |
|-------|--------|----------|
| `ip route get 10.10.10.2` | Exit | `dev wg-tunnel` |
| `ip route get 10.10.10.2` | Entry | `dev wg-clients` |
| `wg show wg-tunnel` | Entry | Recent handshake |
| `sysctl net.ipv4.conf.wg-tunnel.rp_filter` | Entry | `0` |
| `iptables -L DOCKER-USER -n -v` | Entry (if Docker) | ACCEPT for `wg-clients` ↔ `wg-tunnel` |

```bash
sudo wg-ops fix-routing --role entry
sudo wg-ops fix-routing --role exit
sudo wg-ops diagnose --role entry
```

---

## Health checklist (entry)

| Check | Command | Expected |
|-------|---------|----------|
| Clients interface | `sudo wg show wg-clients` | Peers listed |
| Tunnel | `sudo wg show wg-tunnel` | Recent handshake |
| Panels | `systemctl is-active wg-panel wg-admin-panel` | `active` |
| Endpoint file | `cat /etc/wireguard/wg-endpoint` | `IP:51820` |
| Database | `ls -la /etc/wireguard/panel.db` | Exists |
| Health URL | `curl -fsS http://127.0.0.1:8088/health` | OK |

---

## Uninstall

Removes WireGuard, panels, databases, keys, client configs, nginx site, units, CLI tools, and `/opt/wg` on **this** host.

```bash
sudo wg-ops uninstall
# Non-interactive:
sudo WG_UNINSTALL_CONFIRM=yes wg-ops uninstall
```

Optional pre-remove snapshot: `WG_UNINSTALL_BACKUP=1`. System packages (wireguard-tools, nginx, python3, certbot) stay installed. Run on **both** entry and exit for a full teardown.

---

## Important paths

| Path | Role |
|------|------|
| `/opt/wg/` | Installed panels |
| `/opt/wg-ops/` | Cached operator scripts |
| `/opt/wg-src/` | Repo checkout used for panel sync |
| `/etc/wireguard/entry-server.env` | Entry runtime config |
| `/etc/wireguard/exit-server.env` | Exit runtime config |
| `/etc/wireguard/wg-endpoint` | Client Endpoint (`IP:51820`) |
| `/etc/wireguard/clients/` | Client `.conf` files |
| `/etc/wireguard/backups/` | `wg-ops backup` output |

---

## Environment variables (common)

Runtime file on entry: `/etc/wireguard/entry-server.env`

| Variable | Default | Purpose |
|----------|---------|---------|
| `WG_PANEL_PORT` | `8088` | Client panel |
| `WG_ADMIN_PORT` | `8090` | Admin panel |
| `WG_CLIENT_MTU_TWOHOP` | `1380` | Production client MTU |
| `WG_ENTRY_ANTILEAK` | `1` | Block client→WAN leak on entry |
| `WG_ENABLE_BBR` | `1` | TCP BBR when available |
| `WG_ENABLE_MSS_CLAMP` | `1` | MSS clamp service |

Full list: `/opt/wg-ops/config.env.example`  
or https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@latest/deploy/config.env.example

---

## Releases and jsDelivr `@latest`

Install URLs use `cdn.jsdelivr.net/.../wg@latest`, which resolves to the **highest semver Git tag** (e.g. `v1.0.0`). Git clone still uses branch `main`.

After tagging a new release:

```bash
git tag vX.Y.Z
git push origin vX.Y.Z
# Force CDN to pick up the new @latest (one URL at a time):
curl 'https://purge.jsdelivr.net/gh/ahmadfarzad-amiri/wg@latest/deploy/wg-ops'
```

Or use the [jsDelivr purge tool](https://www.jsdelivr.com/tools/purge).

---

## Related

- [Deployment](DEPLOYMENT.md) — first install  
- [Architecture](ARCHITECTURE.md) — design  
- [Admin guide](ADMIN_GUIDE.md) · [User guide](USER_GUIDE.md)  
