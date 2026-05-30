#!/usr/bin/env bash
# Install WireGuard EXIT server (public VPN endpoint + optional reverse proxy).
#
#   curl -fsSL https://raw.githubusercontent.com/OWNER/REPO/main/deploy/install-exit-server.sh | sudo bash
#   sudo bash deploy/install-exit-server.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "$SCRIPT_DIR/lib/common.sh"

require_root

REPO_DIR="${WG_REPO_DIR:-/opt/wg-src}"
LISTEN_PORT="51820"
VPN_PREFIX="10.10.10"

log "=== WireGuard EXIT server installer ==="
log "All values are asked interactively — nothing is hardcoded to a specific site."
echo ""

PUBLIC_IP="$(detect_public_ip)"
prompt PUBLIC_IP "WireGuard public IP (shown in client configs as Endpoint)" "$PUBLIC_IP"
prompt LISTEN_PORT "WireGuard UDP listen port" "51820"
prompt VPN_PREFIX "VPN subnet prefix (first three octets, e.g. 10.10.10)" "10.10.10"

WG_ENDPOINT="${PUBLIC_IP}:${LISTEN_PORT}"

if [[ -f "$SCRIPT_DIR/../client-panel/bin/wg-client" ]]; then
  REPO_DIR="$SCRIPT_DIR/.."
  log "Using local repo at $REPO_DIR"
else
  prompt GITHUB_REPO "GitHub repo URL (https://github.com/OWNER/REPO.git)" ""
  prompt GITHUB_BRANCH "Git branch" "main"
  install_packages git curl wireguard wireguard-tools qrencode
  clone_or_update_repo "$GITHUB_REPO" "$GITHUB_BRANCH" "$REPO_DIR"
fi

install_packages wireguard wireguard-tools qrencode curl

ensure_wg_dirs
install_bin_tools "$REPO_DIR/client-panel/bin"
write_wg_endpoint "$WG_ENDPOINT"

WG_CONF="/etc/wireguard/wg-ir.conf"
SERVER_PUB="/etc/wireguard/ir_client_public.key"
DEF_IF="$(ip route show default 2>/dev/null | awk '{print $5; exit}')"
DEF_IF="${DEF_IF:-eth0}"

if [[ ! -f "$WG_CONF" ]]; then
  SERVER_PRIV="$(wg genkey)"
  SERVER_PUB_KEY="$(printf '%s' "$SERVER_PRIV" | wg pubkey)"
  umask 077
  cat > "$WG_CONF" <<EOF
[Interface]
Address = ${VPN_PREFIX}.1/24
ListenPort = ${LISTEN_PORT}
PrivateKey = ${SERVER_PRIV}
PostUp = iptables -t nat -A POSTROUTING -s ${VPN_PREFIX}.0/24 -o ${DEF_IF} -j MASQUERADE; iptables -A FORWARD -i wg-ir -j ACCEPT; iptables -A FORWARD -o wg-ir -j ACCEPT
PostDown = iptables -t nat -D POSTROUTING -s ${VPN_PREFIX}.0/24 -o ${DEF_IF} -j MASQUERADE; iptables -D FORWARD -i wg-ir -j ACCEPT; iptables -D FORWARD -o wg-ir -j ACCEPT
EOF
  printf '%s\n' "$SERVER_PUB_KEY" > "$SERVER_PUB"
  chmod 600 "$WG_CONF" "$SERVER_PUB"
  log "Created $WG_CONF"
else
  log "Using existing $WG_CONF"
fi

if command -v ufw >/dev/null 2>&1; then
  ufw allow "${LISTEN_PORT}/udp" || true
fi

sysctl -w net.ipv4.ip_forward=1
grep -q '^net.ipv4.ip_forward=1' /etc/sysctl.conf 2>/dev/null \
  || echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf

systemctl enable wg-quick@wg-ir 2>/dev/null || true
wg-quick down wg-ir 2>/dev/null || true
wg-quick up "$WG_CONF"

write_env_file /etc/wireguard/exit-server.env \
  WG_PUBLIC_ENDPOINT "$WG_ENDPOINT" \
  WG_IF wg-ir \
  WG_CONF "$WG_CONF"

cat <<EOF

=== EXIT server ready ===
Client Endpoint      : ${WG_ENDPOINT}
Server public key    : $(cat "$SERVER_PUB")
Config               : $WG_CONF
Endpoint file        : /etc/wireguard/wg-endpoint

Use on the panel server when prompted:
  WireGuard endpoint : ${WG_ENDPOINT}
  Exit SSH target    : root@$(hostname -I | awk '{print $1}')

Tests:
  wg show wg-ir
  ss -ulnp | grep ${LISTEN_PORT}

EOF

bash "$SCRIPT_DIR/test-connectivity.sh" --role exit || true

prompt_yes_no SETUP_PROXY "Configure nginx reverse proxy to your panel server now?" "N"
if [[ "$SETUP_PROXY" == "yes" ]]; then
  install_packages nginx
  prompt INSIDE_IP "Panel server private IP (reachable from this host)" ""
  prompt PROXY_DOMAIN "Public domain (DNS A record → this server)" ""
  prompt CLIENT_PORT "Client panel port on panel server" "8088"
  prompt ADMIN_PORT "Admin panel port on panel server" "8090"
  PROXY_CONF="/etc/nginx/sites-available/wg-proxy.conf"
  install_exit_proxy_nginx \
    "$SCRIPT_DIR/nginx-exit-proxy.conf.template" \
    "$PROXY_CONF" \
    "$PROXY_DOMAIN" \
    "$INSIDE_IP" \
    "$CLIENT_PORT" \
    "$ADMIN_PORT"
  ln -sf "$PROXY_CONF" /etc/nginx/sites-enabled/wg-proxy.conf
  rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true
  nginx -t
  systemctl enable nginx
  systemctl reload nginx
  log "Nginx proxy: https://${PROXY_DOMAIN}/ → ${INSIDE_IP}:${CLIENT_PORT}"
  log "Run after DNS works: certbot --nginx -d ${PROXY_DOMAIN}"
fi
