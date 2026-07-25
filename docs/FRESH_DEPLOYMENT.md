# Fresh-server deployment guide

Exact procedure for clean **entry** and **exit** servers. Production path:

`client device → entry → exit → internet` (websites must see the **exit** IP).

This repository assumes **no previous installation**. Installers refuse to overwrite an existing managed config — uninstall with `sudo wg-ops uninstall` first.

> Live servers are **not** modified by this repository checkout alone. Run the commands below deliberately, with console/out-of-band access available before changing firewall or WireGuard units.

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

Keep SSH allowed from your management network before applying host `ufw` rules.

---

## 4. Install operator CLI (each server)

```bash
curl -fsSL https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@main/deploy/wg-ops \
  -o /usr/local/bin/wg-ops && sudo chmod 755 /usr/local/bin/wg-ops
sudo wg-ops pull
```

Or clone the repo and use `deploy/wg-ops` from the checkout.

---

## 5–6. Configuration and secrets

Copy and edit locally (do **not** commit secrets):

```bash
# Local workstation
cp deploy/config.env.example /tmp/wg-prod.env
# Edit WG_ENTRY_PUBLIC_IP, WG_EXIT_PUBLIC_IP, WG_ADMIN_PASS, …
```

Documentation examples use RFC 5737 addresses (`198.51.100.0/24`, `203.0.113.0/24`). Replace with your real public IPs at install time.

Generate a strong admin password locally; keep it in a password manager.

---

## 7–10. Exit server install + validation

```bash
# On EXIT server
sudo WG_EXIT_PUBLIC_IP=EXIT_PUBLIC_IP \
  WG_TUNNEL_PORT=51821 \
  WG_CLIENT_CIDR=10.10.10.0/24 \
  wg-ops install-exit
```

**Save:** tunnel public key (`/etc/wireguard/tunnel-server.pub`) and `EXIT_IP:51821`.

```bash
# On EXIT
sudo wg-ops test --role exit
sudo wg-ops diagnose --role exit
sudo wg-ops validate --role exit
```

Expect `[HEALTHY]` for NAT, forwarding, and public egress IP.

---

## 11–12. Entry server install + validation

```bash
# On ENTRY server
sudo WG_ENTRY_PUBLIC_IP=ENTRY_PUBLIC_IP \
  WG_EXIT_PUBLIC_IP=EXIT_PUBLIC_IP \
  WG_EXIT_TUNNEL_PUB='PASTE_EXIT_TUNNEL_PUBKEY' \
  WG_ADMIN_PASS='STRONG_PASSWORD' \
  WG_CLIENT_CIDR=10.10.10.0/24 \
  WG_SKIP_XRAY=1 \
  wg-ops install-entry
```

Omit `WG_SKIP_XRAY=1` and set `WG_XRAY_REALITY_SNI=…` only if you need DPI bypass for **client→entry**; Xray must not sit in the WireGuard two-hop data path.

**Save:** entry tunnel public key (`/etc/wireguard/tunnel-entry.pub`).

```bash
# On ENTRY
sudo wg-ops test --role entry
sudo wg-ops diagnose --role entry
sudo wg-ops validate --role entry
```

---

## 13. Entry↔exit link

```bash
# On EXIT
sudo wg-ops add-peer 'ENTRY_TUNNEL_PUBKEY' 'ENTRY_PUBLIC_IP'
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
sudo wg-ops diagnose --role entry
# Anti-leak DROP and policy table 100 should be HEALTHY
```

---

## 20–21. MTU and performance baseline

```bash
# On ENTRY and EXIT
sudo wg-ops tune
sudo wg-ops measure --role guide
```

Follow the printed hop plan (`iperf3` single/multi-stream, UDP, latency). Record results; do not assume a fixed Mbps target — ISP, CPU, and peering dominate.

---

## 22. Production acceptance checklist

- [ ] Client public IP = exit IP  
- [ ] `wg-ops diagnose` on entry and exit: **0 FAILED**  
- [ ] Tunnel handshake recent  
- [ ] No subnet MASQUERADE on entry  
- [ ] MSS clamp unit enabled  
- [ ] SSH still reachable on both hosts  
- [ ] Operational backup taken (`sudo wg-ops backup`) if desired  

---

## 23. Operational backup

```bash
# On ENTRY (and EXIT if desired)
sudo wg-ops backup
# Copies under /etc/wireguard/backups/
```

---

## 24. Recovery

1. Prefer fixing the current stack with `sudo wg-ops diagnose` and `sudo wg-ops fix-routing`.
2. For a bad deploy, uninstall both servers (`sudo wg-ops uninstall`) and reinstall from this guide.
3. Optionally copy specific files from an operational backup under `/etc/wireguard/backups/` if you took one.

**Risk note:** Changing cloud firewall or `ufw` can lock you out. Validate SSH from console before restricting management ports.
