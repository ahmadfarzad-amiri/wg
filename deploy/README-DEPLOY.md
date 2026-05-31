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

## Step 1 — Exit server (run first)

Non-interactive by default:

```bash
curl -fsSL https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@main/deploy/install-exit-server.sh | sudo bash
```

Override with env vars: `WG_EXIT_PUBLIC_IP`, `WG_TUNNEL_PORT`, `WG_CLIENT_CIDR`. Interactive: `WG_INSTALL_INTERACTIVE=1`.

**Save from output:**
- Tunnel public key
- `ExitIP:51821`

## Step 2 — Entry server (run second)

Non-interactive example (set env on `sudo bash`, not on `curl` — a pipe does not pass variables to the right-hand command):

```bash
curl -fsSL https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@main/deploy/install-entry-server.sh -o /tmp/install-entry-server.sh
sudo WG_ENTRY_PUBLIC_IP=203.0.113.10 \
  WG_EXIT_PUBLIC_IP=203.0.113.50 \
  WG_EXIT_TUNNEL_PUB='paste-exit-pubkey' \
  WG_ADMIN_PASS='your-password' \
  bash /tmp/install-entry-server.sh
```

Set `WG_ENTRY_PUBLIC_IP` when auto-detect picks a private address (e.g. `172.16.x.x` on some VPS hosts).

Interactive: `WG_INSTALL_INTERACTIVE=1`. Full env list: [config.env.example](config.env.example).

**Save from output:**
- Entry tunnel public key

## Step 3 — Link tunnel on exit server

```bash
sudo bash deploy/add-entry-peer.sh ENTRY_TUNNEL_PUBLIC_KEY ENTRY_PUBLIC_IP
```

The peer is persisted in `/etc/wireguard/wg-tunnel.conf` (survives reboot).

## Cloud firewall

| Server | Open ports |
|--------|------------|
| Entry | UDP 51820; TCP 80/443 (nginx) or 8088/8090 (direct) |
| Exit | UDP 51821 — restrict to entry server IP when possible |

## Upgrade / backup

```bash
WG_INSTALL_MODE=upgrade sudo bash deploy/install-entry-server.sh
sudo bash deploy/backup.sh
sudo bash deploy/update-panels.sh
sudo bash deploy/restore.sh /etc/wireguard/backups/TIMESTAMP-label
```

## DNS and HTTPS (optional)

**No domain:** press Enter at the domain prompt during install. Panels are available at:

- `http://ENTRY_IP:8088/login`
- `http://ENTRY_IP:8090/admin/login`

**With domain:** point your panel domain A record to the entry server IP. During install, choose **Yes** for Let's Encrypt — certbot installs the certificate automatically (DNS must already resolve).

Manual certbot later:

```bash
sudo certbot --nginx -d your-domain.com
```

## Connection tests

Exit server:

```bash
curl -fsSL https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@main/deploy/test-connectivity.sh -o /tmp/test-connectivity.sh
sudo bash /tmp/test-connectivity.sh --role exit
```

Entry server:

```bash
curl -fsSL https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@main/deploy/test-connectivity.sh -o /tmp/test-connectivity.sh
sudo bash /tmp/test-connectivity.sh --role entry
```

From a connected client, traffic should exit via the exit server (check with `curl ifconfig.me` on the client).

## Legacy script

`install-panel-server.sh` redirects to `install-entry-server.sh`.

## Config files

| File | Server |
|------|--------|
| `/etc/wireguard/wg-endpoint` | Entry — `ENTRY_IP:51820` for client configs |
| `/etc/wireguard/entry-server.env` | Entry — panel environment |
| `/etc/wireguard/exit-server.env` | Exit — tunnel metadata |

See `deploy/config.env.example`.
