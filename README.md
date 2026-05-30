# WireGuard Access Panels

Client and admin web panels for a **two-hop VPN**:

**devices → entry VPS → encrypted tunnel → exit VPS → internet**

**Official repository:** [github.com/ahmadfarzad-amiri/wg](https://github.com/ahmadfarzad-amiri/wg)

## Install order

### 1. Exit VPS (internet egress)

Non-interactive by default (auto-detects public IP). Recommended:

```bash
curl -fsSL https://raw.githubusercontent.com/ahmadfarzad-amiri/wg/main/deploy/install-exit-server.sh -o /tmp/install-exit.sh
sudo bash /tmp/install-exit.sh
```

Or one-liner:

```bash
curl -fsSL https://raw.githubusercontent.com/ahmadfarzad-amiri/wg/main/deploy/install-exit-server.sh | sudo bash
```

Override defaults with env vars if needed: `WG_EXIT_PUBLIC_IP`, `WG_TUNNEL_PORT`, `WG_CLIENT_CIDR`.

Save the **tunnel public key** and **exit IP:port** printed at the end.

### 2. Entry VPS (clients + panels)

```bash
curl -fsSL https://raw.githubusercontent.com/ahmadfarzad-amiri/wg/main/deploy/install-entry-server.sh | sudo bash
```

Enter your domain, entry IP, exit tunnel details, and admin password when prompted.

### 3. Exit VPS — link the tunnel

Copy the **entry tunnel public key** from step 2, then on the exit server:

```bash
curl -fsSL https://raw.githubusercontent.com/ahmadfarzad-amiri/wg/main/deploy/add-entry-peer.sh | sudo bash
```

Or from a clone:

```bash
sudo bash deploy/add-entry-peer.sh ENTRY_TUNNEL_PUBLIC_KEY
```

## What users connect to

| Setting | Value |
|---------|--------|
| WireGuard Endpoint | **Entry server IP:51820** (not the exit server) |
| Web panels | Your domain on the **entry** server |
| Internet exit | **Exit** VPS (NAT) |

## Test

On the exit server:

```bash
bash deploy/test-connectivity.sh --role exit
```

On the entry server:

```bash
bash deploy/test-connectivity.sh --role entry
```

Full guide: **[deploy/README-DEPLOY.md](deploy/README-DEPLOY.md)**
