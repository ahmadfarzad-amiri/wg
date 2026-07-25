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
| Refresh scripts from CDN (pinned tag) | `sudo wg-ops pull` |
| Update scripts + panels + tools | `sudo wg-ops update` |
| Update panels only (entry) | `sudo wg-ops update-panels` |
| Test / diagnose / repair | `sudo wg-ops test` · `diagnose` · `fix-routing` |
| Backup | `sudo wg-ops backup` |
| Uninstall this host | `sudo wg-ops uninstall` |

Native WireGuard CLI remains `wg` (example: `sudo wg show`).

---

## Install and update sources

| What | Source | Notes |
|------|--------|--------|
| `wg-ops` bootstrap + `pull` / `update` scripts | jsDelivr **pinned tag** (e.g. `@v1.0.16`) | Avoid `@latest` — jsDelivr purge is often throttled and can stick on an old release |
| Panel code (`update-panels`, entry install) | Git branch `main` | Clone into `/opt/wg-src` (GitHub or `gh-proxy.com`) |

Default CDN base (bump with each release in `deploy/repo.conf`):

`https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@v1.0.16`

If `wg-ops update` still shows an old version (stuck `@latest` cache), force one pull:

```bash
sudo WG_RAW_BASE='https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@v1.0.16' wg-ops pull
```

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
sudo wg-ops pull            # scripts from CDN pinned tag → /opt/wg-ops
sudo wg-ops update-panels   # panel code from git main → /opt/wg
sudo wg-ops update          # pull + panels (entry) + optional tune
sudo wg-ops styles          # check CSS/JS sync
sudo wg-ops styles --fix
```

`update` = `pull` first, then on entry also `update-panels` (and optional performance repair).

After a style fix, hard-refresh the browser (`Ctrl+Shift+R`).

New **script** fixes only appear after you pull a newer pinned release tag. Panel UI fixes can land sooner via `update-panels` from `main`.

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

Get `ENTRY_TUNNEL_PUBKEY` from entry: `sudo cat /etc/wireguard/tunnel-entry.pub`.

On the **old exit** (if retiring it): remove the stale peer from `/etc/wireguard/wg-tunnel.conf`, then:

```bash
sudo wg syncconf wg-tunnel <(wg-quick strip /etc/wireguard/wg-tunnel.conf)
```

### No handshake after changing exit

Handshake needs **both** sides. `change-exit` only updates the entry; `add-peer` must run on the **new** exit.

```bash
# Entry — peer must show new exit IP + recent handshake
sudo wg show wg-tunnel
sudo grep -E '^(PublicKey|Endpoint)' /etc/wireguard/wg-tunnel.conf

# New exit — must list entry tunnel pubkey as peer
sudo wg show wg-tunnel
sudo cat /etc/wireguard/tunnel-entry.pub   # compare with entry's tunnel-entry.pub

# From entry — force traffic
ping -c 3 10.200.0.1
```

Also verify cloud firewall: exit UDP `51821` from entry IP; entry UDP `51822` open for return path.

If entry config looks right but handshake stays `(none)`, re-run on new exit:

```bash
sudo wg-ops add-peer "$(cat /path/to/entry-tunnel-entry.pub)" ENTRY_IP
```

Then on entry: `sudo wg-ops fix-routing --role entry` and `sudo wg show wg-tunnel`.

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

## Troubleshooting: `wg-quick: already exists` / status shows Stopped

Symptom: menu shows `wg-tunnel` / `wg-clients` as **Stopped** (or **Orphan**), but `systemctl start` fails with `wg-quick: '…' already exists`.

The interface is still up outside systemd. Clear it, then start:

**Entry:**
```bash
sudo wg-quick down wg-clients; sudo wg-quick down wg-tunnel
sudo ip link del wg-clients 2>/dev/null; sudo ip link del wg-tunnel 2>/dev/null
sudo systemctl reset-failed 'wg-quick@wg-clients' 'wg-quick@wg-tunnel'
sudo wg-ops start
```

**Exit:**
```bash
sudo wg-quick down wg-tunnel
sudo ip link del wg-tunnel 2>/dev/null
sudo systemctl reset-failed 'wg-quick@wg-tunnel'
sudo wg-ops start
```

Or: `sudo wg-ops restart` (clears orphans automatically on current `wg-ops`).

### `wg-clients` fails on `ip route replace … scope link`

`Address = 10.10.10.1/24` already installs the connected route. A clients `PostUp` that repeats `ip route replace 10.10.10.0/24 dev wg-clients` often fails and leaves an orphan. Remove those hooks (or run `sudo wg-ops fix-routing --role entry` / `sudo wg-ops restart` on v1.0.4+), then start again.

### Unit fails after wg-quick succeeds (rp_filter drop-in)

If the journal ends at `ip link set mtu … up` with no PostUp error, an old `ExecStartPost` in `/etc/systemd/system/wg-quick@*.service.d/rpfilter.conf` may be exiting 1 when the peer iface is not up yet. Fix:

```bash
sudo tee /etc/systemd/system/wg-quick@wg-clients.service.d/rpfilter.conf /etc/systemd/system/wg-quick@wg-tunnel.service.d/rpfilter.conf >/dev/null <<'EOF'
[Service]
ExecStartPost=-/bin/sh -c 'echo 0 > /proc/sys/net/ipv4/conf/wg-clients/rp_filter 2>/dev/null || true'
ExecStartPost=-/bin/sh -c 'echo 0 > /proc/sys/net/ipv4/conf/wg-tunnel/rp_filter 2>/dev/null || true'
EOF
sudo systemctl daemon-reload
sudo wg-ops restart
```

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
or https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@v1.0.16/deploy/config.env.example

---

## Releases and CDN tags

Install and `wg-ops pull` / `update` use a **pinned** jsDelivr tag (see `GITHUB_CDN_REF` in `deploy/repo.conf`), not `@latest`. Git clone for panels still uses branch `main`.

For each release:

1. Bump `GITHUB_CDN_REF` / `GITHUB_RAW_BASE` / docs URLs to the new tag (e.g. `v1.0.16`).
2. Commit, then `git tag` / `git push` that same version.
3. On servers still stuck on an old `@latest` cache, pull once with an explicit base:

```bash
sudo WG_RAW_BASE='https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@v1.0.16' wg-ops pull
sudo wg-ops update
```

Optional purge (often throttled):

```bash
curl 'https://purge.jsdelivr.net/gh/ahmadfarzad-amiri/wg@v1.0.16/deploy/wg-ops'
```

Or use the [jsDelivr purge tool](https://www.jsdelivr.com/tools/purge).

---

## Related

- [Deployment](DEPLOYMENT.md) — first install  
- [Architecture](ARCHITECTURE.md) — design  
- [Admin guide](ADMIN_GUIDE.md) · [User guide](USER_GUIDE.md)  
