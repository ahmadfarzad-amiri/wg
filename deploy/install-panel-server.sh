#!/usr/bin/env bash
# Install client + admin panels on the INSIDE server (Iran).
# Connects to the EXIT server for WireGuard client management over SSH.
#
#   curl -fsSL https://raw.githubusercontent.com/USER/REPO/main/deploy/install-panel-server.sh | sudo bash
# Or:
#   sudo bash deploy/install-panel-server.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "$SCRIPT_DIR/lib/common.sh"

require_root

REPO_DIR="${WG_REPO_DIR:-/opt/wg-src}"
INSTALL_DIR="${WG_INSTALL_DIR:-/opt/wg}"
ENV_FILE="/etc/wireguard/panel-server.env"

log "=== WireGuard PANEL server installer (inside Iran) ==="

if [[ -f "$SCRIPT_DIR/../client-panel/app.py" ]]; then
  REPO_DIR="$SCRIPT_DIR/.."
  log "Using local repo at $REPO_DIR"
else
  prompt GITHUB_REPO "GitHub repo URL" "https://github.com/YOUR_USER/wg.git"
  prompt GITHUB_BRANCH "Git branch" "main"
  install_packages git curl rsync openssh-client
  clone_or_update_repo "$GITHUB_REPO" "$GITHUB_BRANCH" "$REPO_DIR"
fi

install_packages python3 nginx qrencode rsync openssh-client wireguard-tools curl git

prompt EXIT_SSH "Exit server SSH target (user@ip)" "root@EXIT_IP"
prompt WG_ENDPOINT "WireGuard public endpoint (ip:port)" "PUBLIC_IP:51820"
prompt PANEL_DOMAIN "Public domain for nginx (e.g. access.example.com)" "access.bsla.dev"
prompt PANEL_BRAND "Panel brand name" "BSLA Access"
prompt CLIENT_PORT "Client panel port" "8088"
prompt ADMIN_PORT "Admin panel port" "8090"

prompt_secret ADMIN_PASS "Admin panel password (min 8 chars)"
ADMIN_USER="admin"

ensure_wg_dirs
mkdir -p "$INSTALL_DIR"
rsync -a --delete \
  --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
  "$REPO_DIR/client-panel/" "$INSTALL_DIR/client-panel/"
rsync -a --delete \
  --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
  "$REPO_DIR/admin-panel/" "$INSTALL_DIR/admin-panel/"

install_bin_tools "$REPO_DIR/client-panel/bin"

# SSH key for managing WireGuard on exit server
SSH_DIR="/root/.ssh"
SSH_KEY="$SSH_DIR/wg_exit"
mkdir -p "$SSH_DIR"
chmod 700 "$SSH_DIR"
if [[ ! -f "$SSH_KEY" ]]; then
  ssh-keygen -t ed25519 -N "" -f "$SSH_KEY" -C "wg-panel@$(hostname -s)"
  log "Created SSH key $SSH_KEY"
  log "Add this public key to the exit server's authorized_keys:"
  echo "---"
  cat "${SSH_KEY}.pub"
  echo "---"
  read -r -p "Press Enter after adding the key to $EXIT_SSH ..." _
fi

SSH_OPTS=(-o BatchMode=yes -o StrictHostKeyChecking=accept-new -i "$SSH_KEY")

log "Testing SSH to exit server..."
SSH_CMD=(ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -i "$SSH_KEY")
"${SSH_CMD[@]}" "$EXIT_SSH" 'echo ok && wg show wg-ir | head -5' \
  || die "Cannot SSH to exit server or wg-ir is not up there."

cat > /usr/local/bin/wg-client <<EOF
#!/usr/bin/env bash
set -euo pipefail
exec ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -i "$SSH_KEY" "$EXIT_SSH" wg-client "\$@"
EOF
chmod 755 /usr/local/bin/wg-client

SYNC_SCRIPT="/usr/local/bin/wg-sync-from-exit"
cat > "$SYNC_SCRIPT" <<EOF
#!/usr/bin/env bash
set -euo pipefail
RSYNC_SSH="ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -i $SSH_KEY"
rsync -az --delete -e "\$RSYNC_SSH" ${EXIT_SSH}:/etc/wireguard/client-state/ /etc/wireguard/client-state/
rsync -az --delete -e "\$RSYNC_SSH" ${EXIT_SSH}:/etc/wireguard/clients/ /etc/wireguard/clients/
EOF
chmod 755 "$SYNC_SCRIPT"
"$SYNC_SCRIPT"

# Cron sync every 2 minutes
CRON_LINE="*/2 * * * * root $SYNC_SCRIPT >/dev/null 2>&1"
grep -qF "$SYNC_SCRIPT" /etc/cron.d/wg-sync 2>/dev/null || {
  echo "$CRON_LINE" > /etc/cron.d/wg-sync
  chmod 644 /etc/cron.d/wg-sync
}

write_env_file "$ENV_FILE" \
  WG_DATA_DIR /etc/wireguard \
  WG_BIN_DIR /usr/local/bin \
  WG_EXIT_SSH "$EXIT_SSH" \
  WG_EXIT_SSH_KEY "$SSH_KEY" \
  WG_ENDPOINT "$WG_ENDPOINT" \
  WG_PANEL_HOST 0.0.0.0 \
  WG_PANEL_PORT "$CLIENT_PORT" \
  WG_ADMIN_HOST 127.0.0.1 \
  WG_ADMIN_PORT "$ADMIN_PORT" \
  WG_ADMIN_BASE /admin \
  WG_PANEL_BRAND "$PANEL_BRAND" \
  WG_ADMIN_BRAND "$PANEL_BRAND"

# systemd units
cat > /etc/systemd/system/wg-panel.service <<EOF
[Unit]
Description=WireGuard Client Login Panel
After=network.target

[Service]
Type=simple
EnvironmentFile=$ENV_FILE
ExecStartPre=$SYNC_SCRIPT
ExecStart=/usr/bin/python3 $INSTALL_DIR/client-panel/app.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/wg-admin-panel.service <<EOF
[Unit]
Description=WireGuard Admin Web Panel
After=network.target

[Service]
Type=simple
EnvironmentFile=$ENV_FILE
ExecStartPre=$SYNC_SCRIPT
ExecStart=/usr/bin/python3 $INSTALL_DIR/admin-panel/app.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable wg-panel wg-admin-panel
systemctl restart wg-panel wg-admin-panel

# Admin password
export WG_DATA_DIR=/etc/wireguard
export ADMIN_USER ADMIN_PASS INSTALL_DIR
python3 <<'PY'
import os, sys
sys.path.insert(0, os.path.join(os.environ["INSTALL_DIR"], "admin-panel"))
from admin_panel.core.auth import set_admin_password
set_admin_password(os.environ["ADMIN_USER"], os.environ["ADMIN_PASS"])
print("Admin user configured:", os.environ["ADMIN_USER"])
PY

# nginx on inside (local access; exit server can reverse-proxy here)
NGINX_CONF="/etc/nginx/sites-available/wg-panels.conf"
sed "s/access.bsla.dev/${PANEL_DOMAIN}/g" \
  "$INSTALL_DIR/client-panel/deploy/access.bsla.dev.conf" > "$NGINX_CONF"
ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/wg-panels.conf
rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true
nginx -t
systemctl enable nginx
systemctl reload nginx

cat <<EOF

=== PANEL server ready ===
Client panel : http://127.0.0.1:${CLIENT_PORT}/login
Admin panel  : http://127.0.0.1:${ADMIN_PORT}/admin/login
Nginx        : http://${PANEL_DOMAIN}/login  (if DNS points here)

Admin user   : ${ADMIN_USER}
WG endpoint  : ${WG_ENDPOINT}
Exit SSH     : ${EXIT_SSH}

On the EXIT server, configure nginx reverse proxy to this server's IP:
  proxy client panel -> INSIDE_IP:${CLIENT_PORT}
  proxy /admin/      -> INSIDE_IP:${ADMIN_PORT}/

Connection tests:
  bash $SCRIPT_DIR/test-connectivity.sh --role panel

EOF

bash "$SCRIPT_DIR/test-connectivity.sh" --role panel || true
