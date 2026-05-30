# Deployment guide

Install scripts always pull from **[github.com/ahmadfarzad-amiri/wg](https://github.com/ahmadfarzad-amiri/wg)**.  
Site-specific values (IP, domain, brand) are entered during install.

## Architecture

```
Users → your-domain.com (DNS → exit server)
          ↓ nginx reverse proxy (optional)
        panel server :8088 / :8090
          ↓ SSH
        exit server — WireGuard wg-ir (UDP)
```

## 1. Exit server (run first)

```bash
curl -fsSL https://raw.githubusercontent.com/ahmadfarzad-amiri/wg/main/deploy/install-exit-server.sh | sudo bash
```

Clones `https://github.com/ahmadfarzad-amiri/wg.git` (default — press Enter to accept).

Asks for: public IP, UDP port, optional nginx proxy + domain.

Save the printed **Client Endpoint** for step 2.

## 2. Panel server (run second)

```bash
curl -fsSL https://raw.githubusercontent.com/ahmadfarzad-amiri/wg/main/deploy/install-panel-server.sh | sudo bash
```

Asks for: exit SSH, WireGuard endpoint, domain, brand, admin password, ports.

Add the printed SSH public key to the exit server when prompted.

## 3. DNS

Point your domain A record to the server that serves nginx (usually the **exit** server if using reverse proxy).

## 4. TLS (optional)

```bash
sudo certbot --nginx -d your-domain.com
```

Or provide cert paths when the panel installer asks for HTTPS.

## 5. Connection tests

```bash
# Exit server
wg show wg-ir
bash deploy/test-connectivity.sh --role exit

# Panel server
bash deploy/test-connectivity.sh --role panel
ssh -i /root/.ssh/wg_exit root@YOUR_EXIT_IP 'wg show wg-ir'
```

## Source configuration

Official repo URL is defined once in **`deploy/repo.conf`**:

```
GITHUB_REPO_URL=https://github.com/ahmadfarzad-amiri/wg.git
```

Forks can edit that file; install scripts read it automatically.

See also `deploy/config.env.example` for runtime environment variables.
