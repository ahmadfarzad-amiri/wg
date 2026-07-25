# Operations guide

Step-by-step tasks for **server operators** who install and maintain the WireGuard entry/exit stack on clean servers.

> Panel UI tasks → [Admin guide](ADMIN_GUIDE.md). End-user actions → [User guide](USER_GUIDE.md).

---

## Operator CLI (`wg-ops`)

Run with no arguments for an interactive menu:

```bash
curl -fsSL https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@main/deploy/wg-ops \
  -o /usr/local/bin/wg-ops && sudo chmod 755 /usr/local/bin/wg-ops

sudo wg-ops
```

Menu covers **install**, **update**, and **delete**:

| Action | Menu |
|--------|------|
| Install exit / entry | 1 / 2 |
| Update all (scripts + panels + tools) | 3 |
| Update scripts only | 4 |
| Update panels only | 5 |
| Uninstall server | 6 |
| Uninstall Xray only | 7 |

Non-interactive examples:

```bash
sudo wg-ops update
sudo wg-ops test --role entry
sudo wg-ops uninstall
sudo wg-ops status
```

---

## Prerequisites

Before you start, prepare:

- **Two VPS servers** — one entry, one exit (or one for single-server testing)
- Ubuntu / Debian Linux with root or sudo access
- **Firewall ports open:**
  - Entry: UDP `51820` (clients), TCP `80`/`443` (optional, for HTTPS)
  - Exit: UDP `51821` (tunnel — restrict to entry IP when possible)
- (Optional) A domain name pointed at the entry server IP

Install the operator CLI on each server first:

```bash
curl -fsSL https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@main/deploy/wg-ops \
  -o /usr/local/bin/wg-ops && sudo chmod 755 /usr/local/bin/wg-ops
sudo wg-ops pull
```

---

## Step 1 — Install the exit server

Run on the **exit** VPS.

Interactive: `sudo wg-ops` → **1**

Or non-interactive:

```bash
sudo WG_EXIT_PUBLIC_IP=YOUR_EXIT_IP wg-ops install-exit
```

> **Save from the output:**
> - Tunnel **public key** (printed at the end, also at `/etc/wireguard/tunnel-server.pub`)
> - Exit endpoint: `EXIT_IP:51821`

Optional environment variables:

| Variable | Default | Use |
|----------|---------|-----|
| `WG_EXIT_PUBLIC_IP` | auto-detect | Your exit server's public IP |
| `WG_TUNNEL_PORT` | `51821` | Tunnel UDP port |
| `WG_CLIENT_CIDR` | `10.10.10.0/24` | VPN client subnet |
| `WG_INSTALL_INTERACTIVE` | auto | `1` prompts; omit when env vars are set |

---

## Step 2 — Install the entry server

Interactive: `sudo wg-ops` → **2**

Or non-interactive:

```bash
sudo WG_ENTRY_PUBLIC_IP=YOUR_ENTRY_IP \
  WG_EXIT_PUBLIC_IP=YOUR_EXIT_IP \
  WG_EXIT_TUNNEL_PUB='PASTE_EXIT_TUNNEL_PUBKEY' \
  WG_ADMIN_PASS='choose-a-strong-password' \
  WG_XRAY_REALITY_SNI=www.microsoft.com \
  wg-ops install-entry
```

> Set `WG_ENTRY_PUBLIC_IP` when auto-detect picks a private address (common with VPS providers using `172.16.x.x` internally). Use the **public** IP that clients will connect to.

> **Save from the output:**
> - Entry tunnel **public key** (`/etc/wireguard/tunnel-entry.pub`)

Installed layout:

```
/opt/wg/
├── wg_common/          # shared library
├── client-panel/       # user panel — wg-panel.service (port 8088)
└── admin-panel/        # admin panel — wg-admin-panel.service (port 8090, /admin)

/etc/wireguard/
├── panel.db            # user accounts, sessions, config assignments
├── audit.db            # admin action log
├── admin.json          # admin credentials
├── wg-endpoint         # entry IP:51820 written into client configs
├── clients/            # WireGuard .conf files per client
└── state/              # .meta files (limits, expiry, VPN mode)

/etc/xray/             # only present if WG_XRAY_REALITY_SNI was set
├── config.json         # Xray inbounds (Reality :443, WebSocket, Shadowsocks :8388)
├── server-secrets.env  # XRAY_SERVER_IP, XRAY_REALITY_PUB, XRAY_SS_PASSWORD, …
└── clients/            # one .env per client with CLIENT_UUID
```

Full environment variable reference: `/opt/wg-ops/config.env.example` (after `wg-ops pull`), or [config.env.example](https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@main/deploy/config.env.example).

---

## Step 3 — Link the tunnel on the exit server

Run on the **exit** server:

```bash
sudo wg-ops add-peer 'ENTRY_TUNNEL_PUBKEY' 'ENTRY_PUBLIC_IP'
```

The peer is saved to `/etc/wireguard/wg-tunnel.conf` and survives reboots.

**Verify on entry:**

```bash
sudo wg show wg-tunnel
```

You should see a recent handshake (`latest handshakes:` within the last few seconds).

---

## Step 4 — Open the firewall

| Server | Port | Protocol | Allow from |
|--------|------|----------|-----------|
| Entry | 51820 | UDP | Anyone (all VPN clients) |
| Entry | 80, 443 | TCP | Anyone (if using HTTPS) |
| Exit | 51821 | UDP | Entry server egress IP only (recommended) |

```bash
sudo wg-ops open-ports --role entry
sudo wg-ops open-ports --role exit
```

# Or with a custom UDP range on entry:
# sudo WG_UDP_PORT_RANGE=51820:51830 wg-ops open-ports --role entry

> **Note:** If the entry server is behind NAT, the egress IP seen by the exit server may differ from `WG_ENTRY_PUBLIC_IP`. Check `wg show wg-tunnel` on the exit server for the actual endpoint IP and allow that in your cloud firewall.

---

## Step 5 — Verify connectivity

```bash
# On exit server
sudo wg-ops test --role exit

# On entry server
sudo wg-ops test --role entry
```

**End-to-end test** — run from a client device with VPN connected (not the server):

```bash
curl -4 https://api.ipify.org
```

For `twohop` clients this shows the **exit** server IP. For `direct` clients it shows the **entry** server IP.

---

## Step 6 — First admin login

1. Open `http://ENTRY_IP:8090/admin/login` (or your nginx URL).
2. Log in with username `admin` and the `WG_ADMIN_PASS` set at install.
3. Create a test client under **Clients → Add client**.
4. Register a test user on the client panel at `:8088`, then approve under **Users**.

---

## Service management (entry server)

```bash
# Check status
sudo systemctl status wg-panel wg-admin-panel

# Restart
sudo systemctl restart wg-panel
sudo systemctl restart wg-admin-panel

# Follow logs
journalctl -u wg-panel -u wg-admin-panel -f
```

**Manual run (debugging):**

```bash
sudo PYTHONPATH=/opt/wg:/opt/wg/client-panel:/opt/wg/admin-panel \
  python3 /opt/wg/client-panel/app.py
```

### Fix "502 Bad Gateway" on the client panel

nginx cannot reach the Python app. Diagnose in order:

```bash
# 1. Check for import errors (look for ModuleNotFoundError)
sudo journalctl -u wg-panel -n 50 --no-pager

# 2. Sync wg_common and repair units, then restart
sudo wg-ops update-panels

# 3. Direct health check (bypasses nginx)
curl -fsS http://127.0.0.1:8088/health
ls -la /opt/wg/wg_common/__init__.py
```

If `wg_common/__init__.py` is missing, re-run `wg-ops update-panels`. If the install is corrupted, uninstall and reinstall on a clean server.

---

## HTTPS (optional but recommended)

1. Point your domain A record to the entry server IP.
2. During install the certbot/nginx integration is set up automatically if `WG_DOMAIN` is set. To add it later:
   ```bash
   sudo certbot --nginx -d your-domain.com
   ```
3. nginx proxies to:
   - `127.0.0.1:8088` — client panel
   - `127.0.0.1:8090` — admin panel (path prefix `/admin`)

Panels also work over raw HTTP without a domain.

---

## Operational backup

Create a snapshot of the current production WireGuard configs, env files, and panel database:

```bash
sudo wg-ops backup
```

Backups are saved under `/etc/wireguard/backups/TIMESTAMP-label/`.

**When to back up:**
- Before changing entry or exit server addresses
- Before bulk client deletion
- Before major configuration edits

To recover from a bad config change, copy files back from a backup directory manually, then restart interfaces and run `sudo wg-ops fix-routing`.

---

## Update the panels

```bash
sudo wg-ops update-panels
# or full update (scripts + panels + tools):
sudo wg-ops update
```

Syncs code from the repo to `/opt/wg/`, refreshes CLI tools, and restarts both panels.

### Fix panel CSS or layout

If the panel looks wrong after an update (broken layout, overlapping cards, wrong language):

```bash
sudo wg-ops styles
sudo wg-ops styles --fix
```

After syncing, hard-refresh your browser (`Ctrl+Shift+R`) to clear the cached CSS.

---

## Change the entry server IP

When the entry VPS IP or port changes:

```bash
sudo wg-ops change-entry --new NEW_IP:51820
# Optional: --old OLD_IP to replace only that specific IP in config files
```

Or use **Admin panel → Tools → Change entry**.

After this: update your cloud firewall, DNS records, and ask users to reconnect. Client `.conf` files on disk are rewritten automatically.

---

## Change the exit server

**On the entry server:**

```bash
sudo WG_EXIT_PUBLIC_IP=NEW_EXIT_IP WG_EXIT_TUNNEL_PUB='NEW_EXIT_PUBKEY' \
  wg-ops change-exit
```

**On the new exit server:**

```bash
sudo wg-ops add-peer 'ENTRY_TUNNEL_PUBKEY' 'ENTRY_PUBLIC_IP'
```

**On the old exit server** (if decommissioning): remove the stale entry peer from `/etc/wireguard/wg-tunnel.conf` and run `sudo wg syncconf wg-tunnel /etc/wireguard/wg-tunnel.conf`.

Or use **Admin panel → Tools → Change exit** for the entry-side steps.

---

## Fix one-way traffic (TX up, no internet on client)

Symptom: `wg show wg-clients` on entry shows incoming traffic but the client has no internet.

| Check | Command | Expected result |
|-------|---------|-----------------|
| Exit routes client subnet | `ip route get 10.10.10.2` on exit | output: `dev wg-tunnel` |
| Entry routes client subnet | `ip route get 10.10.10.2` on entry | output: `dev wg-clients` |
| Entry tunnel alive | `wg show wg-tunnel` on entry | recent handshake |
| rp_filter on entry | `sysctl net.ipv4.conf.wg-tunnel.rp_filter` | `0` |
| Docker bypass on entry | `iptables -L DOCKER-USER -n -v` | ACCEPT for `wg-clients ↔ wg-tunnel` |

Auto-fix:

```bash
sudo wg-ops fix-routing --role entry
sudo wg-ops fix-routing --role exit
sudo wg-ops diagnose --role entry
```

---

## Uninstall

> **Warning:** This removes WireGuard, both panels, `panel.db`, `audit.db`, all keys, and client configs managed by the current install.

```bash
sudo wg-ops uninstall
# Non-interactive:
sudo WG_UNINSTALL_CONFIRM=yes wg-ops uninstall
```

Optional snapshot before removal: add `WG_UNINSTALL_BACKUP=1`. Run on **both** entry and exit servers for full teardown. System packages (wireguard-tools, nginx, python3, certbot) are not removed.

If the installer reports an existing install conflict, uninstall first, then run a fresh install on the clean server.

---

## Environment variable reference

Main config file on the entry server: `/etc/wireguard/entry-server.env`

| Variable | Default | Purpose |
|----------|---------|---------|
| `WG_DATA_DIR` | `/etc/wireguard` | Root data directory |
| `WG_PANEL_PORT` | `8088` | Client panel port |
| `WG_ADMIN_PORT` | `8090` | Admin panel port |
| `WG_ADMIN_BASE` | `/admin` | Admin URL prefix |
| `WG_IF` | `wg-clients` | WireGuard client interface name |
| `WG_CLIENT_MTU` | `1380` | Fallback client config MTU |
| `WG_CLIENT_MTU_TWOHOP` | `1380` | Twohop client MTU |
| `WG_CLIENT_MTU_DIRECT` | `1420` | Diagnostic direct-mode client MTU |
| `WG_SERVER_MTU` | `1420` | Default server WG MTU |
| `WG_CLIENTS_MTU` | `WG_SERVER_MTU` | Entry `wg-clients` MTU |
| `WG_TUNNEL_MTU` | `WG_SERVER_MTU` | `wg-tunnel` MTU |
| `WG_ENTRY_ANTILEAK` | `1` | DROP client→WAN on entry unless direct-mode |
| `WG_ENABLE_BBR` | `1` | Enable TCP BBR (if available) + large max buffers |
| `WG_ENABLE_MSS_CLAMP` | `1` | Persistent TCP MSS clamp (`wg-mss-clamp.service`) |

Full list: `/opt/wg-ops/config.env.example` or https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@main/deploy/config.env.example

---

## Quick health checklist

Run on the **entry** server:

| Check | Command | Expected |
|-------|---------|----------|
| Client WireGuard interface | `sudo wg show wg-clients` | Peers listed |
| Tunnel to exit | `sudo wg show wg-tunnel` | Recent handshake |
| Panel services | `systemctl is-active wg-panel wg-admin-panel` | `active` on both |
| Endpoint file | `cat /etc/wireguard/wg-endpoint` | `IP:51820` |
| Database | `ls -la /etc/wireguard/panel.db` | File exists and is readable |
| Direct panel health | `curl -fsS http://127.0.0.1:8088/health` | `200 OK` |

Panel service repair (run when services are in a bad state):

```bash
sudo wg-ops fix-panels
```

---

## Related guides

- [Architecture](ARCHITECTURE.md) — how the stack works
- [Admin guide](ADMIN_GUIDE.md) — admin panel UI tasks
- [Performance guide](PERFORMANCE.md) — speed tuning
- [deploy/README-DEPLOY.md](../deploy/README-DEPLOY.md) — detailed script reference
