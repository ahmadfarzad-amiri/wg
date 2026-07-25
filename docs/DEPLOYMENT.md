# Deployment guide

Clean **entry** and **exit** server install for the two-hop VPN:

`client device → entry → exit → internet` (websites must see the **exit** IP).

This repository assumes **no previous installation**. Installers refuse to overwrite an existing managed config — uninstall with `sudo wg-ops uninstall` first.

> Live servers are **not** modified by a repository checkout alone. Run the commands below deliberately, with console/out-of-band access available before changing firewall or WireGuard units.

**Also see:** [Operations](OPERATIONS.md) (day-2 ops) · [Performance](PERFORMANCE.md) · [Architecture](ARCHITECTURE.md)

---

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

---

## 1. Minimum requirements

| Role | vCPU | RAM | Disk | Network |
|------|------|-----|------|---------|
| Entry | 2 | 2 GB | 20 GB | Public IPv4, UDP open |
| Exit | 2 | 1 GB | 20 GB | Public IPv4, good egress |

**Recommended:** 4 vCPU entry (double crypto), exit sized for aggregate client bandwidth, same provider region for entry↔exit when possible.

**OS:** Ubuntu 22.04 / 24.04 LTS or Debian 12 (wireguard-tools + iptables).

**Kernel:** `CONFIG_WIREGUARD` / wireguard module, IPv4 forwarding, iptables/nft compatibility for iptables.

---

## 2. DNS preparation (optional)

If using HTTPS panels:

```text
A  vpn.example.com  →  ENTRY_PUBLIC_IP
```

**No domain:** panels at `http://ENTRY_IP:8088/login` and `http://ENTRY_IP:8090/admin/login`.

**With domain:** enable Let's Encrypt during install (`WG_DOMAIN` / `WG_ENABLE_SSL`) or run `certbot --nginx -d your-domain.com` later.

---

## 3. Cloud firewall

| Host | Allow |
|------|-------|
| Entry | UDP `51820` (clients), UDP `51822` (tunnel return), or range `51820–51830`; TCP `22`; TCP `80`/`443` if HTTPS |
| Exit | UDP `51821` **from entry egress IP only**, TCP `22` |

Keep SSH allowed from your management network before applying host `ufw` rules.

```bash
# Optional helper after install
sudo WG_UDP_PORT_RANGE=51820:51830 wg-ops open-ports --role entry
```

Note: entry servers behind NAT may connect to exit from a **different egress IP** than `WG_ENTRY_PUBLIC_IP`. Allow the IP shown as `endpoint` in `wg show wg-tunnel` on exit.

---

## 4. Install operator CLI (each server)

```bash
curl -fsSL https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@main/deploy/wg-ops \
  -o /usr/local/bin/wg-ops && sudo chmod 755 /usr/local/bin/wg-ops
sudo wg-ops pull
```

Scripts and examples land under `/opt/wg-ops/`.

The interactive menu (`sudo wg-ops`) detects the host role automatically (`none` / `entry` / `exit` / `both`) and only lists relevant actions. Preview with `wg-ops list-menu`.

| Detected role | Menu shows |
|---------------|------------|
| `none` | Install exit / entry, pull scripts |
| `entry` | Panels, admin, Xray, entry VPN ops |
| `exit` | Add peer, exit VPN ops |
| `both` | Combined entry + exit options |

---

## 5. Configuration and secrets

Copy and edit (do **not** commit secrets):

```bash
# On the server after wg-ops pull:
cp /opt/wg-ops/config.env.example /tmp/wg-prod.env

# Or download from CDN (any machine):
curl -fsSL https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@main/deploy/config.env.example \
  -o /tmp/wg-prod.env

# Edit WG_ENTRY_PUBLIC_IP, WG_EXIT_PUBLIC_IP, WG_ADMIN_PASS, …
```

Documentation examples use RFC 5737 addresses (`198.51.100.0/24`, `203.0.113.0/24`). Replace with your real public IPs at install time.

Generate a strong admin password locally; keep it in a password manager.

Full env list: `/opt/wg-ops/config.env.example` or https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@main/deploy/config.env.example

---

## 6. Exit server install + validation

Run **first**, on the exit VPS. Interactive: clean-server menu → **Install exit server**.

```bash
sudo WG_EXIT_PUBLIC_IP=203.0.113.50 \
  WG_TUNNEL_PORT=51821 \
  WG_CLIENT_CIDR=10.10.10.0/24 \
  wg-ops install-exit
```

Replace `203.0.113.50` with your exit public IP. If a previous install is detected: `sudo wg-ops uninstall` first.

**Save:** tunnel public key (`/etc/wireguard/tunnel-server.pub`) and `EXIT_IP:51821`.

```bash
sudo wg-ops test --role exit
sudo wg-ops diagnose --role exit
sudo wg-ops validate --role exit
```

Expect `[HEALTHY]` for NAT, forwarding, and public egress IP.

---

## 7. Entry server install + validation

Run **second**, on the entry VPS. Interactive: clean-server menu → **Install entry server**.

```bash
sudo WG_ENTRY_PUBLIC_IP=198.51.100.10 \
  WG_EXIT_PUBLIC_IP=203.0.113.50 \
  WG_EXIT_TUNNEL_PUB='PASTE_EXIT_TUNNEL_PUBKEY' \
  WG_ADMIN_PASS='STRONG_PASSWORD' \
  WG_CLIENT_CIDR=10.10.10.0/24 \
  WG_XRAY_REALITY_SNI=www.microsoft.com \
  wg-ops install-entry
```

- Set `WG_ENTRY_PUBLIC_IP` when auto-detect picks a private address. Use the **public** IP clients will connect to.
- `WG_XRAY_REALITY_SNI` installs VLESS+Reality, WebSocket, and Shadowsocks 2022 alongside WireGuard. Omit or set `WG_SKIP_XRAY=1` to skip; install later with `sudo WG_XRAY_REALITY_SNI=… wg-ops install-xray`.
- Xray must not sit in the WireGuard two-hop data path.

**Save:** entry tunnel public key (`/etc/wireguard/tunnel-entry.pub`).

```bash
sudo wg-ops test --role entry
sudo wg-ops diagnose --role entry
sudo wg-ops validate --role entry
```

---

## 8. Entry↔exit link

Run **on the exit server only**:

```bash
sudo wg-ops add-peer 'ENTRY_TUNNEL_PUBKEY' 'ENTRY_PUBLIC_IP'
```

The peer is persisted in `/etc/wireguard/wg-tunnel.conf` (survives reboot).

```bash
# On ENTRY — expect recent handshake
sudo wg show wg-tunnel
ping -c 5 10.200.0.1
```

---

## 9. Client creation and import

```bash
# On ENTRY
sudo wg-client add alice --days 30 --vpn-mode twohop
sudo wg-client show alice
# Deliver /etc/wireguard/clients/alice.conf (or QR / panel download)
```

Import on the **client device** with the WireGuard app. Do not edit `Endpoint` away from `ENTRY_IP:51820`.

Admin can assign one or more WireGuard clients per panel user. Users download all assigned `.conf` files as **`/configs.zip`**. Per-client routing: `wg-client add NAME --vpn-mode direct|twohop` (`direct` is diagnostic only).

---

## 10. Two-hop verification

```bash
# On CLIENT device (VPN connected)
curl -4 https://api.ipify.org
# MUST equal EXIT_PUBLIC_IP

dig +short example.com
curl -4 https://ifconfig.me
```

```bash
# On ENTRY
sudo wg-ops diagnose --role entry
# Anti-leak DROP and policy table 100 should be HEALTHY
```

---

## 11. Performance baseline

```bash
# On ENTRY and EXIT
sudo wg-ops tune
sudo wg-ops measure --role guide
```

Follow the printed hop plan. See [PERFORMANCE.md](PERFORMANCE.md). Production clients stay on **twohop** (exit IP).

---

## 12. Production acceptance checklist

- [ ] Client public IP = exit IP  
- [ ] `wg-ops diagnose` on entry and exit: **0 FAILED**  
- [ ] Tunnel handshake recent  
- [ ] No subnet MASQUERADE on entry  
- [ ] MSS clamp unit enabled  
- [ ] SSH still reachable on both hosts  
- [ ] Operational backup taken (`sudo wg-ops backup`) if desired  

---

## 13. Validate / repair / backup

```bash
sudo wg-ops                    # role-aware menu
sudo wg-ops pull
sudo wg-ops validate --role runtime
sudo wg-ops diagnose --role entry
sudo wg-ops fix-routing --role entry   # or exit | auto
sudo wg-ops fix-endpoint --old OLD_ENTRY_IP --new NEW_ENTRY_IP:51820
sudo wg-ops backup
sudo wg-ops update-panels              # entry only
sudo wg-ops styles --fix
```

Scripts also live under `/opt/wg-ops/` after `wg-ops pull`.

```bash
# On ENTRY (and EXIT if desired)
sudo wg-ops backup
# Copies under /etc/wireguard/backups/
```

---

## 14. Change entry / exit server

On the **entry** server:

```bash
sudo wg-ops change-entry --old OLD_IP --new ENTRY_IP:51820
sudo WG_EXIT_PUBLIC_IP=NEW_EXIT WG_EXIT_TUNNEL_PUB='...' wg-ops change-exit
```

After changing exit, on the **new** exit: `sudo wg-ops add-peer` with this entry's tunnel public key.

---

## 15. Uninstall

Removes WireGuard interfaces, web panels, `panel.db`, admin config, all keys and client configs under `/etc/wireguard`, nginx panel site, systemd units, CLI tools, and `/opt/wg`. Auto-detects entry vs exit.

```bash
sudo WG_UNINSTALL_CONFIRM=yes wg-ops uninstall
```

Optional snapshot: `WG_UNINSTALL_BACKUP=1`. System packages (wireguard-tools, nginx, python3, certbot) are **not** removed. Run on **both** servers for full teardown.

---

## 16. Recovery

1. Prefer fixing the current stack with `sudo wg-ops diagnose` and `sudo wg-ops fix-routing`.
2. For a bad deploy, uninstall both servers and reinstall from this guide.
3. Optionally restore specific files from `/etc/wireguard/backups/` if you took a backup.

**Risk note:** Changing cloud firewall or `ufw` can lock you out. Validate SSH from console before restricting management ports.

---

## 17. Troubleshooting one-way traffic (TX up, RX stuck)

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

---

## 18. Important config files

| File | Server |
|------|--------|
| `/etc/wireguard/wg-endpoint` | Entry — `ENTRY_IP:51820` for client configs |
| `/etc/wireguard/entry-server.env` | Entry — panel + routing env |
| `/etc/wireguard/exit-server.env` | Exit — tunnel metadata |
| `/etc/sysctl.d/99-z-wg-entry-vpn.conf` | Entry — `rp_filter=0` for VPN forwarding |
| `/etc/systemd/system/wg-docker-forward.service` | Entry — Docker bypass (if Docker installed) |
| `/opt/wg-ops/config.env.example` | Example install/runtime env vars |
