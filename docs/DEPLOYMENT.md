# Deployment guide

Get a working two-hop VPN on **two clean servers**. Follow the steps in order.

```
Your phone / laptop  →  Entry VPS  →  Exit VPS  →  Internet
                         (panels)     (public IP websites see)
```

You need two Ubuntu/Debian VPS machines with public IPv4. Installers only work on **clean** servers (no previous install). To start over: `sudo wg-ops uninstall`.

Examples use placeholders (`ENTRY_IP`, `EXIT_IP`, `CLIENT_NAME`, …). Replace them with your real values.

---

## Before you start

Collect these values:

| What | Placeholder | Notes |
|------|-------------|--------|
| Entry public IP | `ENTRY_IP` | IP clients will connect to |
| Exit public IP | `EXIT_IP` | IP websites will see |
| Admin password | `ADMIN_PASSWORD` | At least 8 characters |

Open these ports in your **cloud firewall** (keep SSH open):

| Server | Ports |
|--------|--------|
| Entry | UDP `51820`, UDP `51822`, TCP `22` (add TCP `80`/`443` if you want HTTPS) |
| Exit | UDP `51821` from the entry IP only, TCP `22` |

Optional: point a DNS A record at the entry IP if you want HTTPS panels later.

**Hardware (minimum):** entry 2 vCPU / 2 GB RAM; exit 2 vCPU / 1 GB RAM. Ubuntu 22.04/24.04 or Debian 12.

---

## Step 1 — Install `wg-ops` on both servers

Run on **entry** and **exit**:

```bash
curl -fsSL https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@v1.0.14/deploy/wg-ops \
  -o /usr/local/bin/wg-ops && sudo chmod 755 /usr/local/bin/wg-ops
sudo wg-ops pull
```

`@v1.0.14` is the current pinned release on jsDelivr (see `deploy/repo.conf`).  
`wg-ops pull` downloads the full script set into `/opt/wg-ops` from that same CDN base.

Then either:

- Interactive: `sudo wg-ops` (menu shows only options for this server’s role), or  
- Copy-paste the commands below.

---

## Step 2 — Install the exit server (do this first)

On the **exit** VPS:

```bash
sudo WG_EXIT_PUBLIC_IP=EXIT_IP wg-ops install-exit
```

Or: `sudo wg-ops` → **Install exit server**.

**Write down from the output** (printed at the very end of install):

1. Exit tunnel public key (also in `/etc/wireguard/tunnel-server.pub` — `sudo cat /etc/wireguard/tunnel-server.pub`)
2. Exit endpoint: `EXIT_IP:51821`

Quick check:

```bash
sudo wg-ops test --role exit
```

---

## Step 3 — Install the entry server

On the **entry** VPS (use the exit key from Step 2):

```bash
sudo WG_ENTRY_PUBLIC_IP=ENTRY_IP \
  WG_EXIT_PUBLIC_IP=EXIT_IP \
  WG_EXIT_TUNNEL_PUB='EXIT_TUNNEL_PUBKEY' \
  WG_ADMIN_PASS='ADMIN_PASSWORD' \
  WG_SKIP_XRAY=1 \
  wg-ops install-entry
```

Or: `sudo wg-ops` → **Install entry server**.

Notes:

- `WG_ENTRY_PUBLIC_IP` must be the **public** IP clients use (not a private `10.x` / `172.16.x` LAN IP).
- `WG_SKIP_XRAY=1` skips alternate protocols for a simpler first install. To enable Xray later: set `WG_XRAY_REALITY_SNI=www.microsoft.com` and run `sudo wg-ops install-xray`.

**Write down:** entry tunnel public key (printed at the end of install, also in `/etc/wireguard/tunnel-entry.pub`). If the screen already returned to the `wg-ops` menu, run: `sudo cat /etc/wireguard/tunnel-entry.pub`.

Quick check:

```bash
sudo wg-ops test --role entry
```

### If GitHub clone fails during entry install

The installer needs the repo under `/opt/wg-src`. It tries GitHub, then `gh-proxy.com` (5s each).

**Easiest fix — copy the repo yourself, then install:**

```bash
# From your laptop (in this project directory)
rsync -a ./ root@ENTRY_IP:/opt/wg-src/
# On entry
sudo wg-ops install-entry
```

Or force the proxy:

```bash
sudo WG_GITHUB_REPO='https://gh-proxy.com/https://github.com/ahmadfarzad-amiri/wg.git' \
  wg-ops install-entry
```

---

## Step 4 — Link entry ↔ exit

On the **exit** VPS (use the entry tunnel key from Step 3):

```bash
sudo wg-ops add-peer 'ENTRY_TUNNEL_PUBKEY' 'ENTRY_IP'
```

On the **entry** VPS, confirm a recent handshake:

```bash
sudo wg show wg-tunnel
ping -c 3 10.200.0.1
```

---

## Step 5 — Create a test client and log in

On **entry**:

```bash
sudo wg-client add CLIENT_NAME --days 30 --vpn-mode twohop
sudo wg-client show CLIENT_NAME
```

1. Open admin: `http://ENTRY_IP:8090/admin/login`  
   User `admin` / password from `WG_ADMIN_PASS`
2. Open client panel: `http://ENTRY_IP:8088/login`  
   Register a user, then approve them in admin and assign the `CLIENT_NAME` config
3. On your phone/laptop: import `/etc/wireguard/clients/CLIENT_NAME.conf` (or QR / panel download) into the WireGuard app  
   Leave **Endpoint** as `ENTRY_IP:51820`

---

## Step 6 — Verify it works

On the **client device** (VPN connected):

```bash
curl -4 https://api.ipify.org
```

That IP must be your **exit** public IP (not the entry IP).

On **entry**:

```bash
sudo wg-ops diagnose --role entry
```

Optional speed/MTU baseline on both servers:

```bash
sudo wg-ops tune
sudo wg-ops measure --role guide
```

---

## You’re done when

- [ ] `curl` on the client shows the **exit** IP  
- [ ] `wg show wg-tunnel` on entry has a recent handshake  
- [ ] Admin and client panels load  
- [ ] `wg-ops diagnose` reports no `FAILED` checks  

| What | Where |
|------|--------|
| Client panel | `http://ENTRY_IP:8088/login` |
| Admin panel | `http://ENTRY_IP:8090/admin/login` |
| VPN endpoint | `ENTRY_IP:51820` |

---

## Next steps

| Task | Guide |
|------|--------|
| Day-2 ops (backup, update, change IP, uninstall, troubleshoot) | [Operations](OPERATIONS.md) |
| How the stack works | [Architecture](ARCHITECTURE.md) |
| Admin panel UI | [Admin guide](ADMIN_GUIDE.md) |
| End-user help | [User guide](USER_GUIDE.md) |

Full environment variable list: after `wg-ops pull`, see `/opt/wg-ops/config.env.example`  
or https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@v1.0.14/deploy/config.env.example
