# WireGuard Panel Deployment

Two-server layout for Iran + exit node abroad.

## Architecture

```
Users (Iran)
    |
    | HTTPS (your domain)
    v
+---------------------------+     SSH (management)      +---------------------------+
| EXIT server (outside)     | <------------------------ | PANEL server (inside Iran) |
| - WireGuard wg-ir :51820  |                           | - client panel :8088       |
| - nginx reverse proxy     | ------------------------> | - admin panel  :8090       |
| - /etc/wireguard (master) |     HTTP proxy (optional) | - panel.db, admin login    |
+---------------------------+                           +---------------------------+
```

| Server | Role | Script |
|--------|------|--------|
| Outside Iran | WireGuard VPN + optional reverse proxy | `deploy/install-exit-server.sh` |
| Inside Iran | Web panels + SSH to exit for `wg-client` | `deploy/install-panel-server.sh` |

## 1. Push to GitHub (on your laptop)

```bash
cd /path/to/wg
git init
git add .
git commit -m "Production WireGuard panels with two-server deploy scripts"
git branch -M main
gh repo create YOUR_USER/wg --private --source=. --push
# or manually:
# git remote add origin git@github.com:YOUR_USER/wg.git
# git push -u origin main
```

**Important:** Copy `wg-client` into `client-panel/bin/` before pushing (see `client-panel/bin/README.md`).

## 2. Exit server (outside Iran)

```bash
curl -fsSL https://raw.githubusercontent.com/YOUR_USER/wg/main/deploy/install-exit-server.sh -o install-exit-server.sh
sudo bash install-exit-server.sh
```

Or clone first:

```bash
git clone https://github.com/YOUR_USER/wg.git /opt/wg-src
sudo bash /opt/wg-src/deploy/install-exit-server.sh
```

The script will:
- Install WireGuard and create `/etc/wireguard/wg-ir.conf`
- Open UDP 51820, enable IP forwarding
- Install CLI tools from `client-panel/bin/`
- Print the public **Endpoint** (`IP:51820`) for client configs

### Reverse proxy on exit server (optional)

Point your domain to the **exit** server IP, then proxy to the **inside** panel server:

```bash
sudo cp deploy/nginx-exit-proxy.conf.template /etc/nginx/sites-available/wg-proxy.conf
sudo sed -i 's/INSIDE_PANEL_IP/YOUR_INSIDE_SERVER_IP/g' /etc/nginx/sites-available/wg-proxy.conf
sudo sed -i 's/access.bsla.dev/your.domain/g' /etc/nginx/sites-available/wg-proxy.conf
sudo ln -sf /etc/nginx/sites-available/wg-proxy.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d your.domain
```

## 3. Panel server (inside Iran)

```bash
curl -fsSL https://raw.githubusercontent.com/YOUR_USER/wg/main/deploy/install-panel-server.sh -o install-panel-server.sh
sudo bash install-panel-server.sh
```

Prompts:
- GitHub repo URL
- Exit server SSH (`root@EXIT_IP`)
- WireGuard endpoint (`EXIT_PUBLIC_IP:51820`)
- Domain, admin password, ports

The script will:
- Clone panels to `/opt/wg/`
- Set up SSH key → exit server
- Install `wg-client` wrapper (runs on exit via SSH)
- Sync `client-state/` and `clients/` from exit every 2 minutes
- Start systemd services + nginx

**Before continuing:** add the printed SSH public key to `/root/.ssh/authorized_keys` on the exit server.

## 4. Connection tests

On exit server:

```bash
bash deploy/test-connectivity.sh --role exit
```

On panel server:

```bash
bash deploy/test-connectivity.sh --role panel
```

Manual checks:

```bash
# Exit — WireGuard up
wg show wg-ir
ss -ulnp | grep 51820

# Panel — services up
systemctl status wg-panel wg-admin-panel nginx
curl -fsS http://127.0.0.1:8088/login
curl -fsS http://127.0.0.1:8090/admin/login

# Panel — SSH to exit
ssh -i /root/.ssh/wg_exit root@EXIT_IP 'wg show wg-ir'

# Panel — remote client add (runs on exit)
wg-client list

# End-to-end — from a client device after downloading config
ping 10.10.10.1
```

## Environment files

| File | Server | Purpose |
|------|--------|---------|
| `/etc/wireguard/exit-server.env` | Exit | Public endpoint metadata |
| `/etc/wireguard/panel-server.env` | Panel | Panel + SSH settings |

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `wg-client not found in repo` | Copy `wg-client` to `client-panel/bin/` and redeploy |
| Panel cannot add clients | Check SSH: `ssh -i /root/.ssh/wg_exit root@EXIT_IP wg-client list` |
| Online list empty | Exit `wg-ir` must be up; panel needs `WG_EXIT_SSH` in env file |
| Domain shows nginx error | Configure exit nginx proxy to inside server IP:8088 / :8090 |
