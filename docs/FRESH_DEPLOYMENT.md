# Fresh-server deployment guide

Exact procedure for clean **entry** and **exit** servers. Production path remains:

`client device → entry → exit → internet` (websites must see the **exit** IP).

> Live servers are **not** modified by this repository checkout alone. Run the commands below deliberately, with console/out-of-band access available before changing firewall or WireGuard units.

---

## 1. Minimum requirements

| Role | vCPU | RAM | Disk | Network |
|------|------|-----|------|---------|
| Entry | 2 | 2 GB | 20 GB | Public IPv4, UDP open |
| Exit | 2 | 1 GB | 20 GB | Public IPv4, good egress |

**Recommended:** 4 vCPU entry (double crypto), exit sized for aggregate client bandwidth, same provider region for entry↔exit when possible.

**OS:** Ubuntu 22.04 / 24.04 LTS or Debian 12 (wireguard-tools + iptables).

---

## 2. DNS preparation (local workstation)

If using HTTPS panels:

```text
A  vpn.example.com  →  ENTRY_PUBLIC_IP
```

---

## 3. Firewall preparation (provider panel)

| Host | Allow |
|------|-------|
| Entry | UDP `51820` (clients), UDP `51822` (tunnel return), TCP `22`, TCP `80`/`443` if HTTPS |
| Exit | UDP `51821` **from entry egress IP only**, TCP `22` |

Keep SSH allowed from your management IP before applying host `ufw` rules.

---

## 4. Repository checkout (optional on each server)

Prefer curl installers (below). Or:

```bash
# On ENTRY or EXIT
git clone --depth 1 https://github.com/ahmadfarzad-amiri/wg.git /opt/wg-src
cd /opt/wg-src
```

---

## 5–6. Configuration and secrets

Copy and edit locally (do **not** commit secrets):

```bash
# Local workstation
cp deploy/config.env.example /tmp/wg-prod.env
# Edit WG_ENTRY_PUBLIC_IP, WG_EXIT_PUBLIC_IP, WG_ADMIN_PASS, …
```

Generate a strong admin password locally; keep it in a password manager.

---

## 7–10. Exit server install + validation

```bash
# On EXIT server
curl -fsSL https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@main/deploy/install-exit-server.sh \
  -o /tmp/install-exit-server.sh

sudo WG_EXIT_PUBLIC_IP=EXIT_PUBLIC_IP \
  WG_TUNNEL_PORT=51821 \
  WG_CLIENT_CIDR=10.10.10.0/24 \
  bash /tmp/install-exit-server.sh
```

**Save:** tunnel public key (`/etc/wireguard/tunnel-server.pub`) and `EXIT_IP:51821`.

```bash
# On EXIT
sudo bash /opt/wg-src/deploy/validate-config.sh --role exit   # if repo checked out
# or after install helpers are present:
sudo bash deploy/test-connectivity.sh --role exit
sudo bash deploy/diagnose-vpn.sh --role exit
```

Expect `[HEALTHY]` for NAT, forwarding, and public egress IP.

---

## 11–12. Entry server install + validation

```bash
# On ENTRY server
curl -fsSL https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@main/deploy/install-entry-server.sh \
  -o /tmp/install-entry-server.sh

sudo WG_ENTRY_PUBLIC_IP=ENTRY_PUBLIC_IP \
  WG_EXIT_PUBLIC_IP=EXIT_PUBLIC_IP \
  WG_EXIT_TUNNEL_PUB='PASTE_EXIT_TUNNEL_PUBKEY' \
  WG_ADMIN_PASS='STRONG_PASSWORD' \
  WG_CLIENT_CIDR=10.10.10.0/24 \
  WG_SKIP_XRAY=1 \
  bash /tmp/install-entry-server.sh
```

Omit `WG_SKIP_XRAY=1` and set `WG_XRAY_REALITY_SNI=…` only if you need DPI bypass for **client→entry**; Xray must not sit in the WireGuard two-hop data path.

**Save:** entry tunnel public key (`/etc/wireguard/tunnel-entry.pub`).

```bash
# On ENTRY
sudo bash deploy/test-connectivity.sh --role entry
sudo bash deploy/diagnose-vpn.sh --role entry
```

---

## 13. Entry↔exit link

```bash
# On EXIT
curl -fsSL https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@main/deploy/add-entry-peer.sh \
  -o /tmp/add-entry-peer.sh
sudo bash /tmp/add-entry-peer.sh 'ENTRY_TUNNEL_PUBKEY' 'ENTRY_PUBLIC_IP'
```

```bash
# On ENTRY — expect recent handshake
sudo wg show wg-tunnel
ping -c 5 10.200.0.1
```

---

## 14–15. Client creation and import

```bash
# On ENTRY
sudo wg-client add alice --days 30 --vpn-mode twohop
sudo wg-client show alice
# Deliver /etc/wireguard/clients/alice.conf (or QR / panel download)
```

Import on the **client device** with the WireGuard app. Do not edit `Endpoint` away from `ENTRY_IP:51820`.

---

## 16–19. Two-hop verification

```bash
# On CLIENT device (VPN connected)
curl -4 https://api.ipify.org
# MUST equal EXIT_PUBLIC_IP

# DNS
dig +short example.com

# Leak check (IPv4): public IP must stay EXIT while VPN is up
curl -4 https://ifconfig.me
```

```bash
# On ENTRY
sudo bash deploy/diagnose-vpn.sh --role entry
# Anti-leak DROP and policy table 100 should be HEALTHY
```

---

## 20–21. MTU and performance baseline

```bash
# On ENTRY and EXIT
sudo bash deploy/tune-vpn-performance.sh
sudo bash deploy/measure-vpn-bandwidth.sh --role guide
```

Follow the printed hop plan (`iperf3` single/multi-stream, UDP, latency). Record results; do not assume a fixed Mbps target — ISP, CPU, and peering dominate.

---

## 22. Production acceptance checklist

- [ ] Client public IP = exit IP  
- [ ] `diagnose-vpn.sh` on entry and exit: **0 FAILED**  
- [ ] Tunnel handshake recent  
- [ ] No subnet MASQUERADE on entry  
- [ ] MSS clamp unit enabled  
- [ ] SSH still reachable on both hosts  
- [ ] Backup taken (`deploy/backup.sh`)  

---

## 23. Backup

```bash
# On ENTRY (and EXIT if desired)
sudo bash deploy/backup.sh
# Copies under /etc/wireguard/backups/
```

---

## 24. Rollback

1. Restore `/etc/wireguard` from `backups/<timestamp>-…`  
2. `sudo wg-quick down wg-tunnel; sudo wg-quick up wg-tunnel` (and `wg-clients` on entry)  
3. `sudo bash deploy/fix-vpn-routing.sh --role entry|exit`  
4. Or reinstall with `WG_INSTALL_MODE=upgrade` to preserve keys  

**Risk note:** Changing cloud firewall or `ufw` can lock you out. Validate SSH from console before restricting management ports.
