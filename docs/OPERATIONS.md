# Operations guide

Step-by-step tasks for **server operators** who install and maintain the WireGuard entry/exit stack.

For panel UI tasks, see [Admin guide](ADMIN_GUIDE.md). For end-user actions, see [User guide](USER_GUIDE.md).

Detailed script reference: [deploy/README-DEPLOY.md](../deploy/README-DEPLOY.md).

---

## Prerequisites

- Two VPS instances (or one for testing only on entry — exit required for two-hop)
- Ubuntu/Debian-style Linux with root/sudo
- UDP ports: **51820** (entry clients), **51821** (tunnel, exit side)
- Optional: domain pointing to entry IP for HTTPS

---

## Step 1 — Install exit server (first)

Run on the **exit** VPS:

```bash
curl -fsSL https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@main/deploy/install-exit-server.sh -o /tmp/install-exit-server.sh
sudo WG_EXIT_PUBLIC_IP=YOUR_EXIT_PUBLIC_IP bash /tmp/install-exit-server.sh
```

**Save from output:**

- Exit tunnel **public key** (`tunnel-server.pub`)
- Exit endpoint: `EXIT_IP:51821`

Non-interactive by default. For prompts: `WG_INSTALL_INTERACTIVE=1`.

---

## Step 2 — Install entry server (second)

Download the script first (env vars in a pipe do not reach `sudo bash` reliably):

```bash
curl -fsSL https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@main/deploy/install-entry-server.sh -o /tmp/install-entry-server.sh
sudo WG_ENTRY_PUBLIC_IP=YOUR_ENTRY_PUBLIC_IP \
  WG_EXIT_PUBLIC_IP=YOUR_EXIT_IP \
  WG_EXIT_TUNNEL_PUB='PASTE_EXIT_TUNNEL_PUBKEY' \
  WG_ADMIN_PASS='choose-a-strong-password' \
  bash /tmp/install-entry-server.sh
```

**Save from output:**

- Entry tunnel **public key** (`tunnel-entry.pub`)

**Installed layout:**

```
/opt/wg/
├── client-panel/     → wg-panel.service (port 8088)
└── admin-panel/      → wg-admin-panel.service (port 8090, /admin)
/etc/wireguard/       → keys, clients, panel.db, env files
```

---

## Step 3 — Link tunnel on exit

On the **exit** server:

```bash
curl -fsSL https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@main/deploy/add-entry-peer.sh -o /tmp/add-entry-peer.sh
sudo bash /tmp/add-entry-peer.sh 'ENTRY_TUNNEL_PUBKEY' 'ENTRY_PUBLIC_IP'
```

Verify on entry: `sudo wg show wg-tunnel` — recent handshake.

---

## Step 4 — Firewall

| Server | Open |
|--------|------|
| Entry | UDP **51820** (all clients); TCP **80/443** if using nginx |
| Exit | UDP **51821** — restrict to entry egress IP when possible |

```bash
curl -fsSL https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@main/deploy/open-firewall-ports.sh -o /tmp/open-ports.sh
sudo WG_UDP_PORT_RANGE=51820:51830 bash /tmp/open-ports.sh --role entry
```

---

## Step 5 — Verify connectivity

On each server:

```bash
curl -fsSL https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@main/deploy/test-connectivity.sh -o /tmp/test.sh
sudo bash /tmp/test.sh --role exit   # on exit
sudo bash /tmp/test.sh --role entry  # on entry
```

**End-to-end (on a phone/laptop with VPN connected):**

```bash
curl -4 https://api.ipify.org
```

Should show **exit** IP for `twohop` clients.

---

## Step 6 — First admin login

1. Open admin URL: `http://ENTRY_IP:8090/admin/login` (or nginx URL).
2. Log in with admin user + `WG_ADMIN_PASS` from install.
3. Create a test client under **Clients**.
4. Register a test user on client panel `:8088`, approve under **Users**.

---

## Service management (entry server)

```bash
sudo systemctl status wg-panel wg-admin-panel
sudo systemctl restart wg-panel
sudo systemctl restart wg-admin-panel
journalctl -u wg-panel -u wg-admin-panel -f
```

Manual run (debug):

```bash
sudo -E PYTHONPATH=/opt/wg:/opt/wg/client-panel:/opt/wg/admin-panel \
  python3 /opt/wg/client-panel/app.py
```

**502 Bad Gateway on client panel:** nginx cannot reach the Python app. On the entry server:

```bash
# 1) Check service (look for ModuleNotFoundError: wg_common)
sudo journalctl -u wg-panel -n 50 --no-pager

# 2) Repair units + sync wg_common, then restart
sudo bash deploy/update-panels.sh
# or: sudo bash deploy/fix-panel-services.sh

# 3) Direct health check (bypass nginx)
curl -fsS http://127.0.0.1:8088/health
ls -la /opt/wg/wg_common/__init__.py
```

Admin panel entry point: `/opt/wg/admin-panel/app.py` (not `admin_app.py` — legacy alias only).

---

## Backup and restore

### Backup

```bash
sudo bash /opt/wg-src/deploy/backup.sh
# or from cloned repo:
sudo bash deploy/backup.sh
```

Backups land under `/etc/wireguard/backups/TIMESTAMP-label/`.

### Restore

```bash
sudo bash deploy/restore.sh /etc/wireguard/backups/TIMESTAMP-label
sudo systemctl restart wg-panel wg-admin-panel
```

**When to backup:** Before exit migration, panel upgrades, or bulk client deletes.

---

## Update panels (entry only)

```bash
sudo bash deploy/update-panels.sh
```

Restarts systemd units after syncing code to `/opt/wg/`.

### Check and fix panel UI (CSS / layout)

If the client or admin panel looks wrong (overlapping cards, broken language toggle), run on the **entry** server:

```bash
# 1) Check installed CSS vs expected layout markers
sudo bash deploy/check-sync-panel-styles.sh

# 2) Sync from /opt/wg-src (or repo) and restart panels, then re-check
sudo bash deploy/check-sync-panel-styles.sh --fix
```

From the repo on the server (recommended — no curl):

```bash
sudo bash /opt/wg-src/deploy/check-sync-panel-styles.sh --fix
```

From GitHub (note `@main`, not `/main`):

```bash
curl -fsSL https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@main/deploy/check-sync-panel-styles.sh -o /tmp/check-panel-styles.sh
sudo bash /tmp/check-panel-styles.sh --fix
```

Ensure the repo is current before `--fix`:

```bash
cd /opt/wg-src && sudo git pull
sudo WG_REPO_DIR=/opt/wg-src bash /tmp/check-panel-styles.sh --fix
```

After a successful sync, hard-refresh the browser (Ctrl+Shift+R) so cached `panel.css?v=…` reloads.

---

## Change entry server IP

When the entry public IP or port changes:

```bash
sudo bash deploy/change-entry-server.sh --new NEW_IP:51820
# optional: sudo bash deploy/change-entry-server.sh --old OLD_IP --new NEW_IP:51820
```

Or use admin **Tools → Change entry**.

Update cloud firewall and DNS. Users must reconnect; configs are rewritten on disk.

---

## Change exit server

On **entry**:

```bash
sudo WG_EXIT_PUBLIC_IP=NEW_EXIT_IP WG_EXIT_TUNNEL_PUB='NEW_EXIT_PUBKEY' \
  bash deploy/change-exit-server.sh
```

On **new exit**: run `add-entry-peer.sh` with entry tunnel key.

On **old exit**: remove stale entry peer if decommissioning.

Admin **Tools → Change exit** runs the same scripts.

---

## Upgrade install (preserve keys)

```bash
sudo WG_INSTALL_MODE=upgrade WG_EXIT_PUBLIC_IP=... bash /tmp/install-exit-server.sh
sudo WG_INSTALL_MODE=upgrade WG_ENTRY_PUBLIC_IP=... WG_EXIT_PUBLIC_IP=... \
  WG_EXIT_TUNNEL_PUB='...' bash /tmp/install-entry-server.sh
```

---

## Fix routing (one-way traffic)

Symptoms: client connects, TX increases on server, no internet on device.

```bash
sudo bash deploy/fix-vpn-routing.sh --role entry
sudo bash deploy/fix-vpn-routing.sh --role exit
sudo bash deploy/diagnose-vpn.sh --role entry
```

Common causes: wrong route on exit, `rp_filter`, Docker `DOCKER-USER` blocking forwards on entry.

---

## Migrate legacy paths to /opt/wg

If panels were installed under `/opt/wg-panel` or `/opt/wg-admin-panel`:

```bash
sudo bash /opt/wg/client-panel/deploy/migrate-to-opt-wg.sh
```

---

## Uninstall

**Warning:** Removes WireGuard, panels, `panel.db`, keys, and `/opt/wg`.

```bash
curl -fsSL https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@main/deploy/uninstall-server.sh -o /tmp/uninstall-server.sh
sudo WG_UNINSTALL_CONFIRM=yes bash /tmp/uninstall-server.sh
```

Run on **both** entry and exit for full removal. Optional backup: `WG_UNINSTALL_BACKUP=1`.

---

## Environment file reference

`/etc/wireguard/entry-server.env` — full list in `deploy/config.env.example`.

| Variable | Purpose |
|----------|---------|
| `WG_DATA_DIR` | `/etc/wireguard` |
| `WG_PANEL_PORT` | Client panel (8088) |
| `WG_ADMIN_PORT` | Admin panel (8090) |
| `WG_ADMIN_BASE` | `/admin` URL prefix |
| `WG_IF` | Client interface (`wg-clients`) |

---

## HTTPS (optional)

1. Point domain A record to entry IP.
2. During install, enable certbot/nginx, or:
   `sudo certbot --nginx -d your-domain.com`
3. Proxy to `127.0.0.1:8088` (client) and `127.0.0.1:8090` (admin).

Panels work over HTTP on raw ports without a domain.

---

## VPN performance tuning

After install, on **each** server:

```bash
sudo bash deploy/tune-vpn-performance.sh
```

See **[docs/PERFORMANCE.md](docs/PERFORMANCE.md)** for VPN mode (`direct` vs `twohop`), MTU, BBR, and server placement.

---

## Troubleshooting checklist

| Check | Command (entry) | Expected |
|-------|-----------------|----------|
| Client interface up | `wg show wg-clients` | peers listed |
| Tunnel up | `wg show wg-tunnel` | recent handshake |
| Panel services | `systemctl is-active wg-panel wg-admin-panel` | active |
| Endpoint file | `cat /etc/wireguard/wg-endpoint` | `IP:51820` |
| Database | `ls -la /etc/wireguard/panel.db` | exists, readable |

Panel service repair:

```bash
sudo bash deploy/fix-panel-services.sh
```

---

## Related docs

- [Architecture](ARCHITECTURE.md)
- [Admin guide](ADMIN_GUIDE.md)
- [deploy/README-DEPLOY.md](../deploy/README-DEPLOY.md)
