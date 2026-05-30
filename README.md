# WireGuard Access Panels

Client and admin web panels for managing WireGuard VPN users.

**Official repository:** [github.com/ahmadfarzad-amiri/wg](https://github.com/ahmadfarzad-amiri/wg)

## Install (two servers)

Run on the **exit server** (public VPN, outside):

```bash
curl -fsSL https://raw.githubusercontent.com/ahmadfarzad-amiri/wg/main/deploy/install-exit-server.sh | sudo bash
```

Run on the **panel server** (management, inside):

```bash
curl -fsSL https://raw.githubusercontent.com/ahmadfarzad-amiri/wg/main/deploy/install-panel-server.sh | sudo bash
```

Each script clones from **ahmadfarzad-amiri/wg** (press Enter to accept the default repo URL) and asks for **your** IP, domain, brand, and passwords.

Full guide: **[deploy/README-DEPLOY.md](deploy/README-DEPLOY.md)**

## What you configure at install time

- WireGuard public IP and UDP port
- Domain name and panel brand
- Exit server SSH (`user@host`)
- Admin username and password
- Optional TLS certificate paths

Client configs use the endpoint saved to `/etc/wireguard/wg-endpoint`.

## Test after install

On the exit server:

```bash
bash deploy/test-connectivity.sh --role exit
```

On the panel server:

```bash
bash deploy/test-connectivity.sh --role panel
```

## Repo layout

| Directory | Description |
|-----------|-------------|
| `client-panel/` | User login, config download, QR |
| `admin-panel/` | Client/user management |
| `deploy/` | Install scripts — source URL in `deploy/repo.conf` |
