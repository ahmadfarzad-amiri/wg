# Deployment guide

**Documentation:** [docs/README.md](../docs/README.md) · [Operations guide](../docs/OPERATIONS.md) · [Fresh deployment](../docs/FRESH_DEPLOYMENT.md) · [Performance guide](../docs/PERFORMANCE.md)

**Traffic path:** devices → **entry server** (`wg-clients`) → **encrypted tunnel** → **exit server** → internet

Install scripts pull from [github.com/ahmadfarzad-amiri/wg](https://github.com/ahmadfarzad-amiri/wg).

Install on clean entry and exit servers. If a managed config already exists, uninstall first.

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

## Install operator CLI (each server)

```bash
curl -fsSL https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@main/deploy/wg-ops \
  -o /usr/local/bin/wg-ops && sudo chmod 755 /usr/local/bin/wg-ops
sudo wg-ops pull
```

Interactive menu: `sudo wg-ops`.

## Step 1 — Exit server (run first)

```bash
sudo WG_EXIT_PUBLIC_IP=203.0.113.50 wg-ops install-exit
```

Replace `203.0.113.50` with your exit public IP. Override with env vars: `WG_EXIT_PUBLIC_IP`, `WG_TUNNEL_PORT`, `WG_CLIENT_CIDR`. Interactive: `WG_INSTALL_INTERACTIVE=1` or menu → **1**.

If a previous install is detected, uninstall first: `sudo wg-ops uninstall`.

**Save from output:**
- Tunnel public key (`tunnel-server.pub`)
- `ExitIP:51821`

## Step 2 — Entry server (run second)

```bash
sudo WG_ENTRY_PUBLIC_IP=198.51.100.10 \
  WG_EXIT_PUBLIC_IP=203.0.113.50 \
  WG_EXIT_TUNNEL_PUB='paste-exit-pubkey' \
  WG_ADMIN_PASS='your-password' \
  WG_XRAY_REALITY_SNI=www.microsoft.com \
  wg-ops install-entry
```

`WG_XRAY_REALITY_SNI` installs VLESS+Reality, WebSocket, and Shadowsocks 2022 alongside WireGuard. Omit to skip Xray; install later with `sudo WG_XRAY_REALITY_SNI=… wg-ops install-xray`.

Set `WG_ENTRY_PUBLIC_IP` when auto-detect picks a private address. Use the **public** IP clients will connect to.

Interactive: `WG_INSTALL_INTERACTIVE=1` or menu → **2**. Full env list: `/opt/wg-ops/config.env.example` or https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@main/deploy/config.env.example

**Save from output:**
- Entry tunnel public key (`tunnel-entry.pub`)

## Step 3 — Link tunnel on exit server

Run **on the exit server only**:

```bash
sudo wg-ops add-peer 'ENTRY_TUNNEL_PUBKEY' 'ENTRY_PUBLIC_IP'
```

The peer is persisted in `/etc/wireguard/wg-tunnel.conf` (survives reboot).

## Cloud firewall

| Server | Open ports |
|--------|------------|
| Entry | UDP **51820** (all clients share this one port); UDP **51822** (entry tunnel return path); or open range **51820–51830** |
| Exit | UDP 51821 — restrict to entry server egress IP when possible |

All client configs connect to the **same** `ENTRY_IP:51820`.

```bash
sudo WG_UDP_PORT_RANGE=51820:51830 wg-ops open-ports --role entry
```

Note: entry servers behind NAT may connect to exit from a **different egress IP** than `WG_ENTRY_PUBLIC_IP`. Allow the IP shown as `endpoint` in `wg show wg-tunnel` on exit.

## Validate / repair / backup

Prefer the operator menu after install:

```bash
sudo wg-ops
```

Or non-interactive:

```bash
# Refresh scripts from the repo
sudo wg-ops pull

# Validate + diagnose
sudo wg-ops validate --role runtime
sudo wg-ops diagnose --role entry

# Repair routing (safe to re-run on the current stack)
sudo wg-ops fix-routing --role entry   # or exit | auto

# Update client Endpoint after changing entry public IP
sudo wg-ops fix-endpoint --old OLD_ENTRY_IP --new NEW_ENTRY_IP:51820

# Operational backup of production configs
sudo wg-ops backup
sudo wg-ops update-panels
sudo wg-ops styles
sudo wg-ops styles --fix
```

Or call scripts directly under `/opt/wg-ops/` (after `wg-ops pull`). Install scripts apply routing for the current architecture. Use `fix-routing` after manual iptables changes or if client traffic is one-way.

## Performance tuning

After install or when users report slow speeds:

```bash
sudo wg-ops tune --role entry   # on entry
sudo wg-ops tune --role exit    # on exit
sudo wg-ops measure --role guide  # hop-by-hop test plan
```

See **[docs/PERFORMANCE.md](../docs/PERFORMANCE.md)**.

Production clients stay on **twohop** (exit IP). `direct` mode is only for short diagnostic A/B tests.

## Uninstall (remove everything)

Removes WireGuard interfaces, web panels, `panel.db`, admin config, all keys and client configs under `/etc/wireguard`, nginx panel site, systemd units, CLI tools in `/usr/local/bin`, and `/opt/wg` + `/opt/wg-src`. Auto-detects entry vs exit server.

```bash
sudo WG_UNINSTALL_CONFIRM=yes wg-ops uninstall
```

Optional snapshot before removal: `WG_UNINSTALL_BACKUP=1` (saved under `/root/wg-backup-*`). Interactive confirm: run without `WG_UNINSTALL_CONFIRM` and type `uninstall` when prompted.

System packages (wireguard-tools, nginx, python3, certbot) are **not** removed. Run on **both** entry and exit servers to fully tear down the stack.

## Connection tests

```bash
sudo wg-ops test --role exit
sudo wg-ops test --role entry
```

**End-to-end (on a connected client device, not the server):**

```bash
curl -4 https://api.ipify.org
```

Should show the **exit** server public IP for **twohop** clients.

## Change entry / exit server

On the **entry** server:

```bash
sudo wg-ops change-entry --old OLD_IP --new ENTRY_IP:51820
sudo WG_EXIT_PUBLIC_IP=NEW_EXIT WG_EXIT_TUNNEL_PUB='...' wg-ops change-exit
```

After changing exit, on the **new** exit: `sudo wg-ops add-peer` with this entry's tunnel public key.

## Multiple configs per user

Admin assigns one or more WireGuard clients per panel user. Users download all assigned `.conf` files from the client panel as **`/configs.zip`**.

Per-client routing: `wg-client add NAME --vpn-mode direct|twohop`.

## Troubleshooting one-way traffic (TX up, RX stuck)

| Check | Command | Expected |
|-------|---------|----------|
| Exit routes client subnet via tunnel | `ip route get 10.10.10.2` on exit | `dev wg-tunnel` |
| Entry routes client subnet via wg-clients | `ip route get 10.10.10.2` on entry | `dev wg-clients` |
| Entry tunnel to exit | `wg show wg-tunnel` on entry | recent handshake |
| rp_filter on entry | `sysctl net.ipv4.conf.wg-tunnel.rp_filter` | `0` |
| Docker on entry | `iptables -L DOCKER-USER -n -v` | ACCEPT rules for `wg-clients ↔ wg-tunnel` |

Common causes fixed by `sudo wg-ops fix-routing`:

1. **Exit:** client subnet routed via default NIC instead of `wg-tunnel`
2. **Entry:** same subnet routed via provider LAN instead of `wg-clients`
3. **Entry:** `rp_filter=2` on `wg-tunnel` drops asymmetric return traffic
4. **Entry:** Docker `DOCKER-USER` chain blocks forwarded packets

Run `sudo wg-ops diagnose --role entry` for a full report.

## DNS and HTTPS (optional)

**No domain:** panels at `http://ENTRY_IP:8088/login` and `http://ENTRY_IP:8090/admin/login`.

**With domain:** point A record to entry IP; enable Let's Encrypt during install or run `certbot --nginx -d your-domain.com`.

## Config files

| File | Server |
|------|--------|
| `/etc/wireguard/wg-endpoint` | Entry — `ENTRY_IP:51820` for client configs |
| `/etc/wireguard/entry-server.env` | Entry — panel + routing env |
| `/etc/wireguard/exit-server.env` | Exit — tunnel metadata |
| `/etc/sysctl.d/99-z-wg-entry-vpn.conf` | Entry — `rp_filter=0` for VPN forwarding |
| `/etc/systemd/system/wg-docker-forward.service` | Entry — Docker bypass (if Docker installed) |

See `/opt/wg-ops/config.env.example` or https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@main/deploy/config.env.example
