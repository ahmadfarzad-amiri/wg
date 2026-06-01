# Deployment guide

**Traffic path:** devices → **entry server** (`wg-clients`) → **encrypted tunnel** → **exit server** → internet

Install scripts pull from [github.com/ahmadfarzad-amiri/wg](https://github.com/ahmadfarzad-amiri/wg).

## Architecture

```
┌─────────────┐     UDP 51820      ┌──────────────────┐   tunnel 51821   ┌─────────────────┐
│   devices   │ ─────────────────► │ Entry VPS        │ ───────────────► │ Exit VPS        │ ──► internet
└─────────────┘   client Endpoint  │ wg-clients+panels│   wg-tunnel      │ NAT + egress    │
                                   └──────────────────┘                  └─────────────────┘
```

| Server | Role | Interface | Who connects |
|--------|------|-----------|--------------|
| Entry VPS | Entry | `wg-clients`, `wg-tunnel` (to exit) | Users + admin panels |
| Exit VPS | Exit | `wg-tunnel` (from entry) | Entry server only — not end users |

Default client subnet: `10.10.10.0/24` (override with `WG_CLIENT_CIDR` on both servers).

## Step 1 — Exit server (run first)

Non-interactive by default:

```bash
curl -fsSL https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@main/deploy/install-exit-server.sh -o /tmp/install-exit-server.sh
sudo WG_EXIT_PUBLIC_IP=YOUR_EXIT_IP bash /tmp/install-exit-server.sh
```

Override with env vars: `WG_EXIT_PUBLIC_IP`, `WG_TUNNEL_PORT`, `WG_CLIENT_CIDR`. Interactive: `WG_INSTALL_INTERACTIVE=1`.

**Save from output:**
- Tunnel public key (`tunnel-server.pub`)
- `ExitIP:51821`

## Step 2 — Entry server (run second)

Download the script first — env vars on `curl` do **not** reach `sudo bash` in a pipe:

```bash
curl -fsSL https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@main/deploy/install-entry-server.sh -o /tmp/install-entry-server.sh
sudo WG_ENTRY_PUBLIC_IP=YOUR_ENTRY_IP \
  WG_EXIT_PUBLIC_IP=YOUR_EXIT_IP \
  WG_EXIT_TUNNEL_PUB='paste-exit-pubkey' \
  WG_ADMIN_PASS='your-password' \
  bash /tmp/install-entry-server.sh
```

Set `WG_ENTRY_PUBLIC_IP` when auto-detect picks a private address (common on VPS hosts: `172.16.x.x`). Use the **public** IP clients will connect to.

Interactive: `WG_INSTALL_INTERACTIVE=1`. Full env list: [config.env.example](config.env.example).

**Save from output:**
- Entry tunnel public key (`tunnel-entry.pub`)

## Step 3 — Link tunnel on exit server

Run **on the exit server only**:

```bash
curl -fsSL https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@main/deploy/add-entry-peer.sh -o /tmp/add-entry-peer.sh
sudo bash /tmp/add-entry-peer.sh 'ENTRY_TUNNEL_PUBKEY' 'ENTRY_PUBLIC_IP'
```

The peer is persisted in `/etc/wireguard/wg-tunnel.conf` (survives reboot).

## Cloud firewall

| Server | Open ports |
|--------|------------|
| Entry | UDP **51820** (all clients share this one port); UDP **51822** (entry tunnel return path); or open range **51820–51830** |
| Exit | UDP 51821 — restrict to entry server egress IP when possible |

All client configs connect to the **same** `ENTRY_IP:51820`. You do not need a separate port per user unless you run custom multi-interface setups.

Open a UDP range on the entry VPS (ufw + provider panel):

```bash
curl -fsSL .../open-firewall-ports.sh -o /tmp/open-ports.sh
sudo WG_UDP_PORT_RANGE=51820:51830 bash /tmp/open-ports.sh --role entry
```

Note: entry servers behind NAT may connect to exit from a **different egress IP** than `WG_ENTRY_PUBLIC_IP`. Allow the IP shown as `endpoint` in `wg show wg-tunnel` on exit.

## Upgrade / repair / backup

```bash
# Upgrade (preserve keys and client peers)
curl -fsSL .../install-exit-server.sh -o /tmp/install-exit-server.sh
sudo WG_INSTALL_MODE=upgrade WG_EXIT_PUBLIC_IP=... bash /tmp/install-exit-server.sh

curl -fsSL .../install-entry-server.sh -o /tmp/install-entry-server.sh
sudo WG_INSTALL_MODE=upgrade WG_ENTRY_PUBLIC_IP=... WG_EXIT_PUBLIC_IP=... \
  WG_EXIT_TUNNEL_PUB='...' bash /tmp/install-entry-server.sh

# Repair routing only (safe to re-run anytime)
curl -fsSL .../fix-vpn-routing.sh -o /tmp/fix-vpn-routing.sh
sudo bash /tmp/fix-vpn-routing.sh --role entry   # or exit | auto

# Deep diagnostics
curl -fsSL .../diagnose-vpn.sh -o /tmp/diagnose-vpn.sh
sudo bash /tmp/diagnose-vpn.sh --role entry

# Wrong Endpoint IP in client configs (e.g. old 216.x → current 31.x)
curl -fsSL .../fix-client-endpoint.sh -o /tmp/fix-ep.sh
sudo bash /tmp/fix-ep.sh 31.25.93.168:51820
# or: sudo bash /tmp/fix-ep.sh --old 216.147.121.53 --new 31.25.93.168:51820

sudo bash deploy/backup.sh
sudo bash deploy/update-panels.sh
sudo bash deploy/restore.sh /etc/wireguard/backups/TIMESTAMP-label
```

Install and upgrade scripts automatically apply routing fixes. Use `fix-vpn-routing.sh` after manual iptables changes or if client traffic is one-way.

## Uninstall (remove everything)

Removes WireGuard interfaces, web panels, `panel.db`, admin config, all keys and client configs under `/etc/wireguard`, nginx panel site, systemd units, CLI tools in `/usr/local/bin`, and `/opt/wg` + `/opt/wg-src`. Auto-detects entry vs exit server.

```bash
curl -fsSL https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@main/deploy/uninstall-server.sh -o /tmp/uninstall-server.sh
sudo WG_UNINSTALL_CONFIRM=yes bash /tmp/uninstall-server.sh
```

Optional backup before removal: `WG_UNINSTALL_BACKUP=1` (saved under `/root/wg-backup-*`). Interactive confirm: run without `WG_UNINSTALL_CONFIRM` and type `uninstall` when prompted.

System packages (wireguard-tools, nginx, python3, certbot) are **not** removed. Run on **both** entry and exit servers to fully tear down the stack.

## Connection tests

Quick checks:

```bash
curl -fsSL .../test-connectivity.sh -o /tmp/test-connectivity.sh
sudo bash /tmp/test-connectivity.sh --role exit
sudo bash /tmp/test-connectivity.sh --role entry
```

**End-to-end (on a connected client device, not the server):**

```bash
curl -4 https://api.ipify.org
```

Should show the **exit** server public IP for **twohop** clients (`VPN_MODE=twohop`, default), or the **entry** server public IP for **direct** clients (`VPN_MODE=direct`).

Do **not** use `curl ifconfig.me` on the VPS itself to test VPN — that checks the server's own internet path and may return HTTP 403.

## Change entry / exit server

On the **entry** server:

```bash
sudo bash deploy/change-entry-server.sh --new ENTRY_IP:51820
sudo WG_EXIT_PUBLIC_IP=NEW_EXIT WG_EXIT_TUNNEL_PUB='...' bash deploy/change-exit-server.sh
```

After changing exit, on the **new** exit: `add-entry-peer.sh` with this entry's tunnel public key. Remove the old entry peer on the previous exit if replacing it.

## Multiple configs per user

Admin assigns one or more WireGuard clients per panel user. Users download all assigned `.conf` files from the client panel as **`/configs.zip`**.

Per-client routing: `wg-client add NAME --vpn-mode direct|twohop` (admin **Clients** form includes VPN path).

## Troubleshooting one-way traffic (TX up, RX stuck)

Symptoms: `wg show wg-clients` on entry shows high **received**, tiny **sent**; client has no internet.

| Check | Command | Expected |
|-------|---------|----------|
| Exit routes client subnet via tunnel | `ip route get 10.10.10.2` on exit | `dev wg-tunnel` |
| Entry routes client subnet via wg-clients | `ip route get 10.10.10.2` on entry | `dev wg-clients` |
| Entry tunnel to exit | `wg show wg-tunnel` on entry | recent handshake |
| rp_filter on entry | `sysctl net.ipv4.conf.wg-tunnel.rp_filter` | `0` |
| Docker on entry | `iptables -L DOCKER-USER -n -v` | ACCEPT rules for `wg-clients ↔ wg-tunnel` |

Common causes fixed automatically by `fix-vpn-routing.sh`:

1. **Exit:** client subnet routed via default NIC instead of `wg-tunnel`
2. **Entry:** same subnet routed via provider LAN (`ens160` / `172.16.x.x`) instead of `wg-clients`
3. **Entry:** `rp_filter=2` on `wg-tunnel` drops asymmetric return traffic
4. **Entry:** Docker `DOCKER-USER` chain blocks forwarded packets before WireGuard rules

Run `sudo bash deploy/diagnose-vpn.sh --role entry` for a full report.

## DNS and HTTPS (optional)

**No domain:** panels at `http://ENTRY_IP:8088/login` and `http://ENTRY_IP:8090/admin/login`.

**With domain:** point A record to entry IP; enable Let's Encrypt during install or run `certbot --nginx -d your-domain.com`.

## Legacy script

`install-panel-server.sh` redirects to `install-entry-server.sh`.

## Config files

| File | Server |
|------|--------|
| `/etc/wireguard/wg-endpoint` | Entry — `ENTRY_IP:51820` for client configs |
| `/etc/wireguard/entry-server.env` | Entry — panel + routing env |
| `/etc/wireguard/exit-server.env` | Exit — tunnel metadata |
| `/etc/sysctl.d/99-z-wg-entry-vpn.conf` | Entry — `rp_filter=0` for VPN forwarding |
| `/etc/systemd/system/wg-docker-forward.service` | Entry — Docker bypass (if Docker installed) |

See `deploy/config.env.example`.
