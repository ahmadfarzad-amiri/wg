#!/usr/bin/env bash
# Install WireGuard EXIT server (outside Iran).
# Run on the public VPN / reverse-proxy server:
#   curl -fsSL https://raw.githubusercontent.com/USER/REPO/main/deploy/install-exit-server.sh | sudo bash
# Or after cloning:
#   sudo bash deploy/install-exit-server.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "$SCRIPT_DIR/lib/common.sh"

require_root

REPO_DIR="${WG_REPO_DIR:-/opt/wg-src}"
INSTALL_DIR="${WG_INSTALL_DIR:-/opt/wg}"
LISTEN_PORT="${WG_LISTEN_PORT:-51820}"
VPN_PREFIX="${WG_VPN_PREFIX:-10.10.10}"

log "=== WireGuard EXIT server installer ==="

if [[ -f "$SCRIPT_DIR/../client-panel/bin/wg-client" ]]; then
  REPO_DIR="$SCRIPT_DIR/.."
  log "Using local repo at $REPO_DIR"
else
  prompt GITHUB_REPO "GitHub repo URL (https://github.com/USER/wg.git)" "https://github.com/YOUR_USER/wg.git"
  prompt GITHUB_BRANCH "Git branch" "main"
  install_packages git curl wireguard wireguard-tools qrencode
  clone_or_update_repo "$GITHUB_REPO" "$GITHUB_BRANCH" "$REPO_DIR"
fi

install_packages wireguard wireguard-tools qrencode curl

PUBLIC_IP="$(detect_public_ip)"
prompt PUBLIC_IP "Public IP for client Endpoint" "$PUBLIC_IP"
prompt LISTEN_PORT "WireGuard UDP listen port" "$LISTEN_PORT"

ensure_wg_dirs
install_bin_tools "$REPO_DIR/client-panel/bin"

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
  WG_PUBLIC_ENDPOINT "${PUBLIC_IP}:${LISTEN_PORT}" \
  WG_IF wg-ir \
  WG_CONF "$WG_CONF"

cat <<EOF

=== EXIT server ready ===
Endpoint for clients : ${PUBLIC_IP}:${LISTEN_PORT}
Server public key    : $(cat "$SERVER_PUB")
Config               : $WG_CONF

Next: run deploy/install-panel-server.sh on the INSIDE (Iran) server.
Use these values when prompted:
  Exit server IP/SSH : $(hostname -I | awk '{print $1}')
  WG endpoint        : ${PUBLIC_IP}:${LISTEN_PORT}

Connection tests (run here):
  wg show wg-ir
  ss -ulnp | grep ${LISTEN_PORT}
  curl -4fsS https://api.ipify.org

EOF

bash "$SCRIPT_DIR/test-connectivity.sh" --role exit || true

prompt SETUP_PROXY "Configure nginx reverse proxy to inside panel server now? (y/N)" "N"
if [[ "${SETUP_PROXY,,}" == "y" ]]; then
  install_packages nginx
  prompt INSIDE_IP "Inside panel server IP" ""
  prompt PROXY_DOMAIN "Public domain" "access.bsla.dev"
  PROXY_CONF="/etc/nginx/sites-available/wg-proxy.conf"
  sed -e "s/INSIDE_PANEL_IP/${INSIDE_IP}/g" -e "s/access.bsla.dev/${PROXY_DOMAIN}/g" \
    "$SCRIPT_DIR/nginx-exit-proxy.conf.template" > "$PROXY_CONF"
  ln -sf "$PROXY_CONF" /etc/nginx/sites-enabled/wg-proxy.conf
  rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true
  nginx -t
  systemctl enable nginx
  systemctl reload nginx
  log "Nginx proxy configured for ${PROXY_DOMAIN} -> ${INSIDE_IP}"
fi
