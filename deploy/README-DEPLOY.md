# Deployment guide

**Traffic path:** phone/laptop → **entry server** (`wg-ir`) → **encrypted tunnel** → **exit server** → internet

Install scripts pull from [github.com/ahmadfarzad-amiri/wg](https://github.com/ahmadfarzad-amiri/wg).

## Architecture

```
┌─────────────┐     UDP 51820      ┌──────────────────┐   tunnel 51821   ┌─────────────────┐
│ phone/laptop│ ─────────────────► │ Entry VPS        │ ───────────────► │ Exit VPS        │ ──► internet
└─────────────┘   client Endpoint  │ wg-ir + panels   │   wg-tunnel      │ NAT + egress    │
                                   └──────────────────┘                  └─────────────────┘
```

| Server | Role | Interface | Who connects |
|--------|------|-----------|--------------|
| Entry VPS | Entry | `wg-ir` (clients), `wg-tunnel` (to exit) | Users + admin panels |
| Exit VPS | Exit | `wg-tunnel` (from entry) | Entry server only — not end users |

## Step 1 — Exit server (run first)

```bash
curl -fsSL https://raw.githubusercontent.com/ahmadfarzad-amiri/wg/main/deploy/install-exit-server.sh | sudo bash
```

Prompts: exit public IP, tunnel UDP port (default `51821`).

**Save from output:**
- Tunnel public key
- `ExitIP:51821`

## Step 2 — Entry server (run second)

```bash
curl -fsSL https://raw.githubusercontent.com/ahmadfarzad-amiri/wg/main/deploy/install-entry-server.sh | sudo bash
```

Prompts:
- Entry public IP (this becomes **client Endpoint** in phone configs)
- Exit server IP and tunnel public key (from step 1)
- Panel domain, brand, admin password

**Save from output:**
- Entry tunnel public key

## Step 3 — Link tunnel on exit server

```bash
sudo bash deploy/add-entry-peer.sh ENTRY_TUNNEL_PUBLIC_KEY
```

Or run interactively (paste key when asked):

```bash
curl -fsSL https://raw.githubusercontent.com/ahmadfarzad-amiri/wg/main/deploy/add-entry-peer.sh | sudo bash
```

## DNS

Point your panel domain A record to the **entry** server IP (panels run there).

## TLS (optional)

On the entry server after DNS works:

```bash
sudo certbot --nginx -d your-domain.com
```

## Connection tests

Exit server:

```bash
wg show wg-tunnel
```

```bash
bash deploy/test-connectivity.sh --role exit
```

Entry server:

```bash
wg show wg-ir
```

```bash
wg show wg-tunnel
```

```bash
bash deploy/test-connectivity.sh --role entry
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
