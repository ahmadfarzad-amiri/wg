# Deployment guide

Generic two-server setup. **Every install asks for your own IP, domain, ports, and brand.**

## Architecture

```
Users → your-domain.com (DNS → exit server)
          ↓ nginx reverse proxy (optional)
        panel server :8088 / :8090
          ↓ SSH
        exit server — WireGuard wg-ir (UDP)
```

| Server | Script | Stores |
|--------|--------|--------|
| Exit | `install-exit-server.sh` | `/etc/wireguard/wg-ir.conf`, `wg-endpoint` |
| Panel | `install-panel-server.sh` | `/opt/wg/`, `panel.db`, admin login |

## 1. Push to GitHub

```bash
git remote add origin git@github.com:OWNER/REPO.git
git push -u origin main
```

Replace `OWNER/REPO` in curl commands below.

## 2. Exit server (run first)

```bash
curl -fsSL https://raw.githubusercontent.com/OWNER/REPO/main/deploy/install-exit-server.sh -o install-exit-server.sh
sudo bash install-exit-server.sh
```

Prompts include:
- WireGuard **public IP** (auto-detected, confirm or override)
- **UDP port** (default 51820)
- Optional **nginx proxy** → panel server IP + **your domain**

Save the printed **Client Endpoint** (`IP:port`) for step 3.

## 3. Panel server (run second)

```bash
curl -fsSL https://raw.githubusercontent.com/OWNER/REPO/main/deploy/install-panel-server.sh -o install-panel-server.sh
sudo bash install-panel-server.sh
```

Prompts include:
- GitHub repo (if not cloned)
- Exit server **SSH** (`root@EXIT_IP`)
- **WireGuard endpoint** (`EXIT_IP:51820`)
- **Domain**, **brand**, **ports**, **admin user/password**
- Optional **HTTPS** cert paths

Add the printed SSH public key to the exit server before continuing.

## 4. DNS

| Record | Points to |
|--------|-----------|
| `your-domain.com` A | Exit server IP (if using exit nginx proxy) |
| or | Panel server IP (if nginx only on panel server) |

## 5. TLS (optional)

On the server that serves nginx to the public:

```bash
sudo certbot --nginx -d your-domain.com
```

Or provide cert paths during panel install (`ENABLE_SSL=yes`).

## 6. Connection tests

```bash
# Exit server
wg show wg-ir
ss -ulnp | grep 51820
bash deploy/test-connectivity.sh --role exit

# Panel server
systemctl status wg-panel wg-admin-panel nginx
curl -fsS http://127.0.0.1:8088/login
curl -fsS http://127.0.0.1:8090/admin/login
ssh -i /root/.ssh/wg_exit root@EXIT_IP 'wg show wg-ir'
bash deploy/test-connectivity.sh --role panel
```

## Configuration files

| File | Purpose |
|------|---------|
| `/etc/wireguard/wg-endpoint` | `IP:port` in downloaded client configs |
| `/etc/wireguard/exit-server.env` | Exit server metadata |
| `/etc/wireguard/panel-server.env` | Panel systemd environment |
| `deploy/config.env.example` | Reference for all variables |

## Nginx templates

| Template | Use |
|----------|-----|
| `client-panel/deploy/nginx-panels.conf.template` | Panel server |
| `deploy/nginx-exit-proxy.conf.template` | Exit reverse proxy |

Placeholders are filled by the install scripts — do not edit templates on the server; re-run install or edit generated files under `/etc/nginx/sites-available/`.

## Troubleshooting

| Problem | Check |
|---------|--------|
| Wrong endpoint in client `.conf` | `cat /etc/wireguard/wg-endpoint` on exit server |
| Panel cannot add clients | `ssh -i /root/.ssh/wg_exit user@exit wg-client list` |
| Online list empty | Exit `wg-ir` up; `WG_EXIT_SSH` in panel-server.env |
| Domain 502 | Exit nginx → correct panel IP and ports |
