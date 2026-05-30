#!/usr/bin/env bash
# Entry VPS — where phones/laptops connect + web panels.
#
# phone/laptop → THIS server (wg-clients) → tunnel (wg-tunnel) → exit server → internet
#
# One-liner:
#   curl -fsSL https://raw.githubusercontent.com/ahmadfarzad-amiri/wg/main/deploy/install-entry-server.sh | sudo bash
set -eo pipefail

_WG_SCRIPT=""
if [[ "${BASH_SOURCE[0]+set}" == "set" ]]; then
  _WG_SCRIPT="${BASH_SOURCE[0]}"
fi
if [[ -n "$_WG_SCRIPT" && -f "$(dirname "$_WG_SCRIPT")/lib/common.sh" ]]; then
  SCRIPT_DIR="$(cd "$(dirname "$_WG_SCRIPT")" && pwd)"
  # shellcheck source=lib/common.sh
  source "$SCRIPT_DIR/lib/common.sh"
else
  _BOOT="$(mktemp -d)"
  mkdir -p "$_BOOT/deploy/lib"
  GITHUB_RAW_BASE="${GITHUB_RAW_BASE:-https://raw.githubusercontent.com/ahmadfarzad-amiri/wg/main}"
  curl -fsSL "$GITHUB_RAW_BASE/deploy/repo.conf" -o "$_BOOT/deploy/repo.conf"
  curl -fsSL "$GITHUB_RAW_BASE/deploy/lib/common.sh" -o "$_BOOT/deploy/lib/common.sh"
  SCRIPT_DIR="$_BOOT/deploy"
  # shellcheck source=lib/common.sh
  source "$SCRIPT_DIR/lib/common.sh"
  fetch_deploy_helper_scripts test-connectivity.sh
fi
set -u
require_root
install_wg_tools

REPO_DIR="${WG_REPO_DIR:-/opt/wg-src}"
INSTALL_DIR="${WG_INSTALL_DIR:-/opt/wg}"
ENV_FILE="/etc/wireguard/entry-server.env"

CLIENT_IF="wg-clients"
TUNNEL_IF="wg-tunnel"
CLIENT_PORT_WG="51820"
VPN_PREFIX="10.10.10"
TUNNEL_LOCAL="10.200.0.2/30"
CLIENT_CIDR="10.10.10.0/24"

log "=== ENTRY server — client entry + panels ==="
log "Source: ${GITHUB_REPO_URL}"
echo ""

ENTRY_IP="$(detect_public_ip)"
prompt ENTRY_IP "Entry server public IP (client Endpoint — phones connect here)" "$ENTRY_IP"
prompt CLIENT_PORT_WG "Client WireGuard UDP port" "51820"
prompt EXIT_IP "Exit server public IP" ""
prompt EXIT_TUNNEL_PORT "Exit tunnel UDP port" "51821"
prompt EXIT_TUNNEL_PUB "Exit tunnel public key (from install-exit-server.sh)" ""

prompt PANEL_DOMAIN "Public domain for web panels (e.g. vpn.example.com)" ""
prompt PANEL_BRAND "Brand name shown in panels" "VPN Access"
prompt CLIENT_PORT "Client panel HTTP port" "8088"
prompt ADMIN_PORT "Admin panel HTTP port" "8090"
prompt ADMIN_USER "Admin panel username" "admin"
prompt_secret ADMIN_PASS "Admin panel password (min 8 chars)"

prompt_yes_no ENABLE_SSL "Add HTTPS nginx block (requires existing cert paths)?" "N"
SSL_CERT=""
SSL_KEY=""
if [[ "$ENABLE_SSL" == "yes" ]]; then
  prompt SSL_CERT "Full path to TLS certificate (fullchain.pem)" ""
  prompt SSL_KEY "Full path to TLS private key (privkey.pem)" ""
fi

WG_ENDPOINT="${ENTRY_IP}:${CLIENT_PORT_WG}"

if [[ -f "$SCRIPT_DIR/../client-panel/app.py" ]]; then
  REPO_DIR="$SCRIPT_DIR/.."
else
  install_packages git curl
  clone_repo_if_needed "$REPO_DIR"
fi

install_packages python3 nginx qrencode git

ensure_wg_dirs
install_bin_tools "$REPO_DIR/client-panel/bin"
write_wg_endpoint "$WG_ENDPOINT"

mkdir -p "$INSTALL_DIR"
rsync -a --delete \
  --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
  "$REPO_DIR/client-panel/" "$INSTALL_DIR/client-panel/"
rsync -a --delete \
  --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
  "$REPO_DIR/admin-panel/" "$INSTALL_DIR/admin-panel/"

DEF_IF="$(default_route_iface)"
DEF_IF="${DEF_IF:-eth0}"

# --- Client interface (users connect here) ---
CLIENT_PRIV="$(wg genkey)"
CLIENT_PUB="$(printf '%s' "$CLIENT_PRIV" | wg pubkey)"
CLIENT_CONF="/etc/wireguard/${CLIENT_IF}.conf"

umask 077
cat > "$CLIENT_CONF" <<EOF
[Interface]
Address = ${VPN_PREFIX}.1/24
ListenPort = ${CLIENT_PORT_WG}
PrivateKey = ${CLIENT_PRIV}
PostUp = iptables -A FORWARD -i ${CLIENT_IF} -j ACCEPT; iptables -A FORWARD -o ${CLIENT_IF} -j ACCEPT
PostDown = iptables -D FORWARD -i ${CLIENT_IF} -j ACCEPT; iptables -D FORWARD -o ${CLIENT_IF} -j ACCEPT
EOF
printf '%s\n' "$CLIENT_PUB" > /etc/wireguard/clients-server.pub
chmod 600 "$CLIENT_CONF" /etc/wireguard/clients-server.pub

# --- Tunnel to exit server ---
TUNNEL_PRIV="$(wg genkey)"
TUNNEL_PUB="$(printf '%s' "$TUNNEL_PRIV" | wg pubkey)"
TUNNEL_CONF="/etc/wireguard/${TUNNEL_IF}.conf"

cat > "$TUNNEL_CONF" <<EOF
[Interface]
Address = ${TUNNEL_LOCAL}
PrivateKey = ${TUNNEL_PRIV}
Table = off
PostUp = iptables -A FORWARD -i ${CLIENT_IF} -o ${TUNNEL_IF} -j ACCEPT; iptables -A FORWARD -i ${TUNNEL_IF} -o ${CLIENT_IF} -m state --state RELATED,ESTABLISHED -j ACCEPT; ip rule add from ${CLIENT_CIDR} lookup 100 priority 100; ip route add default dev ${TUNNEL_IF} table 100
PostDown = iptables -D FORWARD -i ${CLIENT_IF} -o ${TUNNEL_IF} -j ACCEPT; iptables -D FORWARD -i ${TUNNEL_IF} -o ${CLIENT_IF} -m state --state RELATED,ESTABLISHED -j ACCEPT; ip rule del from ${CLIENT_CIDR} lookup 100 priority 100 2>/dev/null || true; ip route del default dev ${TUNNEL_IF} table 100 2>/dev/null || true

[Peer]
PublicKey = ${EXIT_TUNNEL_PUB}
Endpoint = ${EXIT_IP}:${EXIT_TUNNEL_PORT}
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
EOF
printf '%s\n' "$TUNNEL_PUB" > /etc/wireguard/tunnel-entry.pub
chmod 600 "$TUNNEL_CONF" /etc/wireguard/tunnel-entry.pub

if command -v ufw >/dev/null 2>&1; then
  ufw allow "${CLIENT_PORT_WG}/udp" || true
fi

sysctl -w net.ipv4.ip_forward=1
grep -q '^net.ipv4.ip_forward=1' /etc/sysctl.conf 2>/dev/null \
  || echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf

systemctl enable "wg-quick@${CLIENT_IF}" "wg-quick@${TUNNEL_IF}" 2>/dev/null || true
wg-quick down "$CLIENT_IF" 2>/dev/null || true
wg-quick down "$TUNNEL_IF" 2>/dev/null || true
wg-quick up "$CLIENT_CONF"
wg-quick up "$TUNNEL_CONF"

write_env_file "$ENV_FILE" \
  WG_ROLE entry \
  WG_DATA_DIR /etc/wireguard \
  WG_BIN_DIR /usr/local/bin \
  WG_IF "$CLIENT_IF" \
  WG_ENDPOINT "$WG_ENDPOINT" \
  WG_DEFAULT_ENDPOINT "$WG_ENDPOINT" \
  WG_PANEL_HOST 0.0.0.0 \
  WG_PANEL_PORT "$CLIENT_PORT" \
  WG_ADMIN_HOST 127.0.0.1 \
  WG_ADMIN_PORT "$ADMIN_PORT" \
  WG_ADMIN_BASE /admin \
  WG_PANEL_BRAND "$PANEL_BRAND" \
  WG_ADMIN_BRAND "$PANEL_BRAND" \
  WG_EXIT_IP "$EXIT_IP" \
  WG_EXIT_TUNNEL_PORT "$EXIT_TUNNEL_PORT"

cat > /etc/systemd/system/wg-panel.service <<EOF
[Unit]
Description=WireGuard Client Login Panel
After=network.target wg-quick@${CLIENT_IF}.service

[Service]
Type=simple
EnvironmentFile=$ENV_FILE
ExecStart=/usr/bin/python3 $INSTALL_DIR/client-panel/app.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/wg-admin-panel.service <<EOF
[Unit]
Description=WireGuard Admin Web Panel
After=network.target wg-quick@${CLIENT_IF}.service

[Service]
Type=simple
EnvironmentFile=$ENV_FILE
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

=== ENTRY server ready ===
Client Endpoint (phones)  : ${WG_ENDPOINT}
Client server public key  : ${CLIENT_PUB}
Tunnel public key (entry) : ${TUNNEL_PUB}

Web panels:
  http://${PANEL_DOMAIN}/login
  http://${PANEL_DOMAIN}/admin/login
Admin user                : ${ADMIN_USER}

IMPORTANT — on the exit server, run:
  bash deploy/add-entry-peer.sh ${TUNNEL_PUB}

Traffic path:
  phone/laptop → ${ENTRY_IP}:${CLIENT_PORT_WG} → tunnel → ${EXIT_IP} → internet

EOF

bash "$SCRIPT_DIR/test-connectivity.sh" --role entry || true
