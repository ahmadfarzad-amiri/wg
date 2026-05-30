#!/usr/bin/env bash
# Install client + admin panels on the management server.
#
# One-liner (official repo):
#   curl -fsSL https://raw.githubusercontent.com/ahmadfarzad-amiri/wg/main/deploy/install-panel-server.sh | sudo bash
set -euo pipefail

GITHUB_RAW_BASE="${GITHUB_RAW_BASE:-https://raw.githubusercontent.com/ahmadfarzad-amiri/wg/main}"

if [[ -f "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh" ]]; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  # shellcheck source=lib/common.sh
  source "$SCRIPT_DIR/lib/common.sh"
else
  _BOOT="$(mktemp -d)"
  mkdir -p "$_BOOT/deploy/lib"
  curl -fsSL "$GITHUB_RAW_BASE/deploy/repo.conf" -o "$_BOOT/deploy/repo.conf"
  curl -fsSL "$GITHUB_RAW_BASE/deploy/lib/common.sh" -o "$_BOOT/deploy/lib/common.sh"
  SCRIPT_DIR="$_BOOT/deploy"
  # shellcheck source=lib/common.sh
  source "$SCRIPT_DIR/lib/common.sh"
fi

require_root

REPO_DIR="${WG_REPO_DIR:-/opt/wg-src}"
INSTALL_DIR="${WG_INSTALL_DIR:-/opt/wg}"
ENV_FILE="/etc/wireguard/panel-server.env"

log "=== WireGuard panel server installer ==="
log "Source: ${GITHUB_REPO_URL}"
echo ""

if [[ -f "$SCRIPT_DIR/../client-panel/app.py" ]]; then
  REPO_DIR="$SCRIPT_DIR/.."
else
  install_packages git curl
  clone_repo_if_needed "$REPO_DIR"
fi

install_packages python3 nginx qrencode rsync openssh-client wireguard-tools curl git

prompt EXIT_SSH "Exit server SSH target (user@host)" ""
prompt WG_ENDPOINT "WireGuard public endpoint (ip:port for client configs)" ""
prompt PANEL_DOMAIN "Public domain for this server (e.g. vpn.example.com)" ""
prompt PANEL_BRAND "Brand name shown in panels" "VPN Access"
prompt CLIENT_PORT "Client panel port" "8088"
prompt ADMIN_PORT "Admin panel port" "8090"
prompt ADMIN_USER "Admin panel username" "admin"
prompt_secret ADMIN_PASS "Admin panel password (min 8 chars)"

prompt_yes_no ENABLE_SSL "Add HTTPS nginx block (requires existing cert paths)?" "N"
SSL_CERT=""
SSL_KEY=""
if [[ "$ENABLE_SSL" == "yes" ]]; then
  prompt SSL_CERT "Full path to TLS certificate (fullchain.pem)" ""
  prompt SSL_KEY "Full path to TLS private key (privkey.pem)" ""
fi

ensure_wg_dirs
mkdir -p "$INSTALL_DIR"
rsync -a --delete \
  --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
  "$REPO_DIR/client-panel/" "$INSTALL_DIR/client-panel/"
rsync -a --delete \
  --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
  "$REPO_DIR/admin-panel/" "$INSTALL_DIR/admin-panel/"

install_bin_tools "$REPO_DIR/client-panel/bin"

SSH_DIR="/root/.ssh"
SSH_KEY="$SSH_DIR/wg_exit"
mkdir -p "$SSH_DIR"
chmod 700 "$SSH_DIR"
if [[ ! -f "$SSH_KEY" ]]; then
  ssh-keygen -t ed25519 -N "" -f "$SSH_KEY" -C "wg-panel@$(hostname -s)"
  log "Add this public key to ${EXIT_SSH} authorized_keys:"
  echo "---"
  cat "${SSH_KEY}.pub"
  echo "---"
  read -r -p "Press Enter after the key is added on the exit server..." _
fi

SSH_CMD=(ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -i "$SSH_KEY")
log "Testing SSH to exit server..."
"${SSH_CMD[@]}" "$EXIT_SSH" 'echo ok && wg show wg-ir | head -5' \
  || die "Cannot SSH to exit server or wg-ir is not running there."

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

CRON_LINE="*/2 * * * * root $SYNC_SCRIPT >/dev/null 2>&1"
echo "$CRON_LINE" > /etc/cron.d/wg-sync
chmod 644 /etc/cron.d/wg-sync

write_env_file "$ENV_FILE" \
  WG_DATA_DIR /etc/wireguard \
  WG_BIN_DIR /usr/local/bin \
  WG_EXIT_SSH "$EXIT_SSH" \
  WG_EXIT_SSH_KEY "$SSH_KEY" \
  WG_ENDPOINT "$WG_ENDPOINT" \
  WG_DEFAULT_ENDPOINT "$WG_ENDPOINT" \
  WG_PANEL_HOST 0.0.0.0 \
  WG_PANEL_PORT "$CLIENT_PORT" \
  WG_ADMIN_HOST 127.0.0.1 \
  WG_ADMIN_PORT "$ADMIN_PORT" \
  WG_ADMIN_BASE /admin \
  WG_PANEL_BRAND "$PANEL_BRAND" \
  WG_ADMIN_BRAND "$PANEL_BRAND"

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

export WG_DATA_DIR=/etc/wireguard
export ADMIN_USER ADMIN_PASS INSTALL_DIR
python3 <<'PY'
import os, sys
sys.path.insert(0, os.path.join(os.environ["INSTALL_DIR"], "admin-panel"))
from admin_panel.core.auth import set_admin_password
set_admin_password(os.environ["ADMIN_USER"], os.environ["ADMIN_PASS"])
print("Admin user configured:", os.environ["ADMIN_USER"])
PY

NGINX_CONF="/etc/nginx/sites-available/wg-panels.conf"
NGINX_TEMPLATE="$INSTALL_DIR/client-panel/deploy/nginx-panels.conf.template"
if [[ "$ENABLE_SSL" == "yes" ]]; then
  install_panel_nginx "$NGINX_TEMPLATE" "$NGINX_CONF" \
    "$PANEL_DOMAIN" "$CLIENT_PORT" "$ADMIN_PORT" "$SSL_CERT" "$SSL_KEY"
else
  install_panel_nginx "$NGINX_TEMPLATE" "$NGINX_CONF" \
    "$PANEL_DOMAIN" "$CLIENT_PORT" "$ADMIN_PORT"
fi
ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/wg-panels.conf
rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true
nginx -t
systemctl enable nginx
systemctl reload nginx

cat <<EOF

=== Panel server ready ===
Domain (local nginx) : ${PANEL_DOMAIN}
Client panel         : http://127.0.0.1:${CLIENT_PORT}/login
Admin panel          : http://127.0.0.1:${ADMIN_PORT}/admin/login
Admin user           : ${ADMIN_USER}
WireGuard endpoint   : ${WG_ENDPOINT}
Exit SSH             : ${EXIT_SSH}

If users reach this host via an exit-server reverse proxy, point DNS to the exit server IP.

Tests:
  bash $SCRIPT_DIR/test-connectivity.sh --role panel

EOF

bash "$SCRIPT_DIR/test-connectivity.sh" --role panel || true
