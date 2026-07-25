#!/usr/bin/env bash
# Entry VPS — where client devices connect + web panels.
#
# Preferred:
#   sudo WG_ENTRY_PUBLIC_IP=ENTRY_IP \
#     WG_EXIT_PUBLIC_IP=EXIT_IP \
#     WG_EXIT_TUNNEL_PUB='EXIT_TUNNEL_PUBKEY' \
#     WG_ADMIN_PASS='ADMIN_PASSWORD' \
#     wg-ops install-entry
#
# Direct path after wg-ops pull:
#   WG_INSTALL_INTERACTIVE=1 sudo bash /opt/wg-ops/install-entry-server.sh
# Fresh install only — existing installs must be uninstalled first.
set -eo pipefail

if [[ -z "${WG_DEPLOY_REEXEC:-}" && ! -t 0 ]]; then
  export WG_DEPLOY_REEXEC=1
  GITHUB_RAW_BASE="${GITHUB_RAW_BASE:-https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@latest}"
  _WG_INSTALLER="$(mktemp /tmp/wg-install-XXXXXX.sh)"
  curl -fsSL "$GITHUB_RAW_BASE/deploy/install-entry-server.sh" -o "$_WG_INSTALLER"
  chmod 700 "$_WG_INSTALLER"
  exec bash "$_WG_INSTALLER" "$@"
fi

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
  GITHUB_RAW_BASE="${GITHUB_RAW_BASE:-https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@latest}"
  curl -fsSL "$GITHUB_RAW_BASE/deploy/repo.conf" -o "$_BOOT/deploy/repo.conf"
  curl -fsSL "$GITHUB_RAW_BASE/deploy/lib/common.sh" -o "$_BOOT/deploy/lib/common.sh"
  SCRIPT_DIR="$_BOOT/deploy"
  # shellcheck source=lib/common.sh
  source "$SCRIPT_DIR/lib/common.sh"
  fetch_deploy_helper_scripts test-connectivity.sh diagnose-vpn.sh fix-vpn-routing.sh change-entry-server.sh change-exit-server.sh
fi
set -u
require_root
install_wg_tools

log "Starting entry server installation..."

REPO_DIR="${WG_REPO_DIR:-/opt/wg-src}"
INSTALL_DIR="${WG_INSTALL_DIR:-/opt/wg}"
ENV_FILE="/etc/wireguard/entry-server.env"

CLIENT_IF="wg-clients"
TUNNEL_IF="wg-tunnel"
CLIENT_PORT_WG="${WG_CLIENT_PORT:-51820}"
TUNNEL_LISTEN_PORT="${WG_TUNNEL_LISTEN_PORT:-51822}"
VPN_PREFIX="10.10.10"
TUNNEL_LOCAL="10.200.0.2/30"
CLIENT_CIDR="${WG_CLIENT_CIDR:-10.10.10.0/24}"
CLIENT_CONF="/etc/wireguard/${CLIENT_IF}.conf"
TUNNEL_CONF="/etc/wireguard/${TUNNEL_IF}.conf"

log "=== ENTRY server — client entry + panels ==="
log "Source: ${GITHUB_REPO_URL}"

if [[ -n "${WG_ENTRY_PUBLIC_IP:-}" ]]; then
  ENTRY_IP="$WG_ENTRY_PUBLIC_IP"
else
  ENTRY_IP="$(detect_public_ip)"
fi

EXIT_IP="${WG_EXIT_PUBLIC_IP:-}"
EXIT_TUNNEL_PORT="${WG_EXIT_TUNNEL_PORT:-51821}"
EXIT_TUNNEL_PUB="${WG_EXIT_TUNNEL_PUB:-}"
PANEL_DOMAIN="${WG_PANEL_DOMAIN:-}"
PANEL_BRAND="${WG_PANEL_BRAND:-VPN Access}"
CLIENT_PORT="${WG_PANEL_PORT:-8088}"
ADMIN_PORT="${WG_ADMIN_PORT:-8090}"
ADMIN_USER="${WG_ADMIN_USER:-admin}"
ENABLE_SSL="${WG_ENABLE_SSL:-no}"
CERTBOT_EMAIL="${WG_CERTBOT_EMAIL:-}"
XRAY_REALITY_SNI="${WG_XRAY_REALITY_SNI:-}"
XRAY_WS_DOMAIN="${WG_XRAY_WS_DOMAIN:-}"
XRAY_SKIP="${WG_SKIP_XRAY:-0}"

if should_prompt; then
  log "Interactive mode — press Enter to accept [defaults]."
  prompt ENTRY_IP "Entry server public IP (client Endpoint)" "$ENTRY_IP"
  prompt CLIENT_PORT_WG "Client WireGuard UDP port" "$CLIENT_PORT_WG"
  prompt EXIT_IP "Exit server public IP" "$EXIT_IP"
  prompt EXIT_TUNNEL_PORT "Exit tunnel UDP port" "$EXIT_TUNNEL_PORT"
  prompt EXIT_TUNNEL_PUB "Exit tunnel public key (from install-exit-server.sh)" "$EXIT_TUNNEL_PUB"
  prompt_optional PANEL_DOMAIN "Panel domain for web access" "$PANEL_DOMAIN"
  prompt PANEL_BRAND "Brand name shown in panels" "$PANEL_BRAND"
  prompt CLIENT_PORT "Client panel HTTP port" "$CLIENT_PORT"
  prompt ADMIN_PORT "Admin panel HTTP port" "$ADMIN_PORT"
  prompt ADMIN_USER "Admin panel username" "$ADMIN_USER"
  read_admin_password
  prompt_yes_no ENABLE_SSL "Enable HTTPS with Let's Encrypt (certbot)?" "N"
  if [[ "$ENABLE_SSL" == "yes" ]]; then
    prompt CERTBOT_EMAIL "Email for Let's Encrypt certificate notifications" "$CERTBOT_EMAIL"
  fi
  prompt_optional XRAY_REALITY_SNI "Xray Reality SNI domain (blank to skip — e.g. www.microsoft.com)" "${XRAY_REALITY_SNI:-}"
  if [[ -n "$XRAY_REALITY_SNI" ]]; then
    prompt_optional XRAY_WS_DOMAIN "Xray WebSocket CDN domain (blank to skip)" "${XRAY_WS_DOMAIN:-}"
  fi
else
  log "Entry public IP   : ${ENTRY_IP}"
  log "Exit public IP    : ${EXIT_IP}"
  log "Exit tunnel port  : ${EXIT_TUNNEL_PORT}"
  [[ -n "$EXIT_TUNNEL_PUB" ]] || die "Set WG_EXIT_TUNNEL_PUB (exit tunnel public key)"
  [[ -n "$EXIT_IP" ]] || die "Set WG_EXIT_PUBLIC_IP"
  if [[ -z "${WG_ADMIN_PASS:-}" && -z "${WG_ADMIN_PASS_FILE:-}" ]]; then
    die "Set WG_ADMIN_PASS or WG_ADMIN_PASS_FILE for non-interactive install"
  fi
  read_admin_password
fi

PANEL_ADMIN_HOST="0.0.0.0"
USE_NGINX="no"
if [[ -n "$PANEL_DOMAIN" ]]; then
  USE_NGINX="yes"
  PANEL_ADMIN_HOST="127.0.0.1"
fi

WG_ENDPOINT="${ENTRY_IP}:${CLIENT_PORT_WG}"
# Export for validators (names match env vars used by helpers).
export WG_ENTRY_PUBLIC_IP="$ENTRY_IP"
export WG_EXIT_PUBLIC_IP="$EXIT_IP"
export WG_EXIT_TUNNEL_PUB="$EXIT_TUNNEL_PUB"
export WG_EXIT_TUNNEL_PORT="$EXIT_TUNNEL_PORT"
export WG_CLIENT_PORT="$CLIENT_PORT_WG"
export WG_CLIENT_CIDR="$CLIENT_CIDR"
wg_validate_entry_install_env
require_fresh_install "$CLIENT_CONF"
require_fresh_install "$TUNNEL_CONF"

if [[ -f "$SCRIPT_DIR/../client-panel/app.py" ]]; then
  REPO_DIR="$SCRIPT_DIR/.."
else
  install_packages git curl
  clone_repo_if_needed "$REPO_DIR"
fi

# Bootstrap from /tmp may load a stale common.sh; prefer the cloned repo.
if [[ -f "$REPO_DIR/deploy/lib/common.sh" ]]; then
  # shellcheck source=lib/common.sh
  source "$REPO_DIR/deploy/lib/common.sh"
fi

install_packages python3 qrencode git
if [[ "$USE_NGINX" == "yes" ]]; then
  install_packages nginx
fi

ensure_wg_dirs
install_bin_tools "$REPO_DIR/client-panel/bin"
install_wg_ops "$REPO_DIR/deploy"
write_wg_endpoint "$WG_ENDPOINT"

mkdir -p "$INSTALL_DIR"
rsync -a --delete \
  --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
  "$REPO_DIR/client-panel/" "$INSTALL_DIR/client-panel/"
rsync -a --delete \
  --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
  "$REPO_DIR/admin-panel/" "$INSTALL_DIR/admin-panel/"
rsync -a --delete \
  --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
  "$REPO_DIR/wg_common/" "$INSTALL_DIR/wg_common/"

DEF_IF="$(default_route_iface)"
DEF_IF="${DEF_IF:-eth0}"

wg_stop_if "$CLIENT_IF"
wg_stop_if "$TUNNEL_IF"

CLIENT_PRIV="$(wg genkey)"
CLIENT_PUB="$(printf '%s' "$CLIENT_PRIV" | wg pubkey)"
umask 077
cat > "$CLIENT_CONF" <<EOF
[Interface]
Address = ${VPN_PREFIX}.1/24
ListenPort = ${CLIENT_PORT_WG}
PrivateKey = ${CLIENT_PRIV}
MTU = ${WG_CLIENTS_MTU:-${WG_SERVER_MTU:-1420}}
EOF
printf '%s\n' "$CLIENT_PUB" > /etc/wireguard/clients-server.pub
chmod 600 "$CLIENT_CONF" /etc/wireguard/clients-server.pub

TUNNEL_PRIV="$(wg genkey)"
TUNNEL_PUB="$(printf '%s' "$TUNNEL_PRIV" | wg pubkey)"

cat > "$TUNNEL_CONF" <<EOF
[Interface]
Address = ${TUNNEL_LOCAL}
ListenPort = ${TUNNEL_LISTEN_PORT}
PrivateKey = ${TUNNEL_PRIV}
MTU = ${WG_TUNNEL_MTU:-${WG_SERVER_MTU:-1420}}
Table = off
PostUp = iptables -C FORWARD -i ${CLIENT_IF} -o ${TUNNEL_IF} -j ACCEPT 2>/dev/null || iptables -A FORWARD -i ${CLIENT_IF} -o ${TUNNEL_IF} -j ACCEPT; iptables -C FORWARD -i ${TUNNEL_IF} -o ${CLIENT_IF} -j ACCEPT 2>/dev/null || iptables -A FORWARD -i ${TUNNEL_IF} -o ${CLIENT_IF} -j ACCEPT; ip rule del from ${CLIENT_CIDR} lookup 100 priority 100 2>/dev/null || true; ip rule add from ${CLIENT_CIDR} lookup 100 priority 100; ip route del default dev ${TUNNEL_IF} table 100 2>/dev/null || true; ip route add default dev ${TUNNEL_IF} table 100
PostDown = iptables -D FORWARD -i ${CLIENT_IF} -o ${TUNNEL_IF} -j ACCEPT 2>/dev/null || true; iptables -D FORWARD -i ${TUNNEL_IF} -o ${CLIENT_IF} -j ACCEPT 2>/dev/null || true; ip rule del from ${CLIENT_CIDR} lookup 100 priority 100 2>/dev/null || true; ip route del default dev ${TUNNEL_IF} table 100 2>/dev/null || true

[Peer]
PublicKey = ${EXIT_TUNNEL_PUB}
Endpoint = ${EXIT_IP}:${EXIT_TUNNEL_PORT}
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
EOF
printf '%s\n' "$TUNNEL_PUB" > /etc/wireguard/tunnel-entry.pub
chmod 600 "$TUNNEL_CONF" /etc/wireguard/tunnel-entry.pub

if command -v ufw >/dev/null 2>&1; then
  wg_ufw_allow_udp_ports
  if [[ "$USE_NGINX" == "yes" ]]; then
    ufw allow 80/tcp || true
    ufw allow 443/tcp || true
  else
    ufw allow "${CLIENT_PORT}/tcp" || true
    ufw allow "${ADMIN_PORT}/tcp" || true
  fi
fi
maybe_enable_ufw

wg_quick_up "$CLIENT_CONF" "$CLIENT_IF"
wg_quick_up "$TUNNEL_CONF" "$TUNNEL_IF"
systemctl enable "wg-quick@${CLIENT_IF}" "wg-quick@${TUNNEL_IF}" 2>/dev/null || true

UDP_PORT_MIN="${WG_UDP_PORT_MIN:-$CLIENT_PORT_WG}"
UDP_PORT_MAX="${WG_UDP_PORT_MAX:-}"
if [[ -z "$UDP_PORT_MAX" && -n "${WG_UDP_PORT_RANGE:-}" ]]; then
  UDP_PORT_MAX="${WG_UDP_PORT_RANGE#*:}"
fi
UDP_PORT_MAX="${UDP_PORT_MAX:-$UDP_PORT_MIN}"

write_env_file "$ENV_FILE" \
  WG_ROLE entry \
  WG_DATA_DIR /etc/wireguard \
  WG_BIN_DIR /usr/local/bin \
  WG_IF "$CLIENT_IF" \
  WG_TUNNEL_IF "$TUNNEL_IF" \
  WG_CLIENT_CIDR "$CLIENT_CIDR" \
  WG_ENTRY_PUBLIC_IP "$ENTRY_IP" \
  WG_ENDPOINT "$WG_ENDPOINT" \
  WG_DEFAULT_ENDPOINT "$WG_ENDPOINT" \
  WG_PANEL_HOST 0.0.0.0 \
  WG_PANEL_PORT "$CLIENT_PORT" \
  WG_ADMIN_HOST "$PANEL_ADMIN_HOST" \
  WG_ADMIN_PORT "$ADMIN_PORT" \
  WG_ADMIN_BASE /admin \
  WG_PANEL_BRAND "$PANEL_BRAND" \
  WG_ADMIN_BRAND "$PANEL_BRAND" \
  WG_EXIT_IP "$EXIT_IP" \
  WG_EXIT_PUBLIC_IP "$EXIT_IP" \
  WG_EXIT_TUNNEL_PUB "$EXIT_TUNNEL_PUB" \
  WG_EXIT_TUNNEL_PORT "$EXIT_TUNNEL_PORT" \
  WG_TUNNEL_LISTEN_PORT "$TUNNEL_LISTEN_PORT" \
  WG_UDP_PORT_MIN "$UDP_PORT_MIN" \
  WG_UDP_PORT_MAX "$UDP_PORT_MAX" \
  WG_HTTPS "$([[ "$ENABLE_SSL" == "yes" ]] && echo 1 || echo 0)" \
  WG_CLIENT_MTU "${WG_CLIENT_MTU:-1380}" \
  WG_CLIENT_MTU_DIRECT "${WG_CLIENT_MTU_DIRECT:-1420}" \
  WG_CLIENT_MTU_TWOHOP "${WG_CLIENT_MTU_TWOHOP:-1380}" \
  WG_SERVER_MTU "${WG_SERVER_MTU:-1420}" \
  WG_CLIENTS_MTU "${WG_CLIENTS_MTU:-${WG_SERVER_MTU:-1420}}" \
  WG_TUNNEL_MTU "${WG_TUNNEL_MTU:-${WG_SERVER_MTU:-1420}}" \
  WG_ENABLE_BBR "${WG_ENABLE_BBR:-1}" \
  WG_ENABLE_MSS_CLAMP "${WG_ENABLE_MSS_CLAMP:-1}" \
  WG_ENTRY_ANTILEAK "${WG_ENTRY_ANTILEAK:-1}" \
  WG_DNS "${WG_DNS:-8.8.8.8, 8.8.4.4}"

export WG_CLIENT_CIDR="$CLIENT_CIDR"
export WG_TUNNEL_IF="$TUNNEL_IF"
export WG_IF="$CLIENT_IF"
apply_entry_vpn_routing_fix

cat > /etc/systemd/system/wg-panel.service <<EOF
[Unit]
Description=WireGuard Client Login Panel
After=network.target wg-quick@${CLIENT_IF}.service

[Service]
Type=simple
EnvironmentFile=$ENV_FILE
Environment=PYTHONPATH=$INSTALL_DIR:$INSTALL_DIR/client-panel:$INSTALL_DIR/admin-panel
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
Environment=PYTHONPATH=$INSTALL_DIR:$INSTALL_DIR/admin-panel:$INSTALL_DIR/client-panel
ExecStart=/usr/bin/python3 $INSTALL_DIR/admin-panel/app.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable wg-panel wg-admin-panel

if [[ -n "${ADMIN_PASS:-}" ]]; then
  export WG_DATA_DIR=/etc/wireguard
  export ADMIN_USER ADMIN_PASS INSTALL_DIR
  python3 <<'PY'
import os, sys
sys.path.insert(0, os.environ["INSTALL_DIR"])
sys.path.insert(0, os.path.join(os.environ["INSTALL_DIR"], "admin-panel"))
from admin_panel.core.auth import set_admin_password
set_admin_password(os.environ["ADMIN_USER"], os.environ["ADMIN_PASS"])
print("Admin user configured:", os.environ["ADMIN_USER"])
PY
fi

systemctl restart wg-panel wg-admin-panel

if command -v wg-client >/dev/null 2>&1; then
  wg-client install-timer 2>/dev/null || warn "wg-client install-timer failed (optional)"
fi

NGINX_CONF="/etc/nginx/sites-available/wg-panels.conf"
NGINX_TEMPLATE="$INSTALL_DIR/client-panel/deploy/nginx-panels.conf.template"
PANEL_URL_CLIENT=""
PANEL_URL_ADMIN=""

if [[ "$USE_NGINX" == "yes" ]]; then
  SSL_CERT="/etc/letsencrypt/live/${PANEL_DOMAIN}/fullchain.pem"
  SSL_KEY="/etc/letsencrypt/live/${PANEL_DOMAIN}/privkey.pem"
  install_panel_nginx "$NGINX_TEMPLATE" "$NGINX_CONF" \
    "$PANEL_DOMAIN" "$CLIENT_PORT" "$ADMIN_PORT" "$SSL_CERT" "$SSL_KEY"
  ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/wg-panels.conf
  rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true
  if ! nginx -t 2>/tmp/wg-nginx-test.err; then
    warn "nginx config test failed — removing stale site configs and retrying HTTP-only"
    cat /tmp/wg-nginx-test.err >&2 || true
    clean_stale_panel_nginx "$PANEL_DOMAIN"
    install_panel_nginx "$NGINX_TEMPLATE" "$NGINX_CONF" \
      "$PANEL_DOMAIN" "$CLIENT_PORT" "$ADMIN_PORT"
    ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/wg-panels.conf
    nginx -t || die "nginx config invalid after cleanup — check /etc/nginx/sites-enabled/"
  fi
  systemctl enable nginx
  nginx_reload_or_start
  if [[ "$ENABLE_SSL" == "yes" && -n "$CERTBOT_EMAIL" ]]; then
    if ! install_certbot_https "$PANEL_DOMAIN" "$CERTBOT_EMAIL"; then
      warn "HTTPS not enabled — point DNS A record for ${PANEL_DOMAIN} to ${ENTRY_IP}, then run:"
      warn "  certbot --nginx -d ${PANEL_DOMAIN}"
    fi
    nginx_reload_or_start
  fi
  if [[ "$ENABLE_SSL" == "yes" ]] && [[ -f "/etc/letsencrypt/live/${PANEL_DOMAIN}/fullchain.pem" ]]; then
    PANEL_URL_CLIENT="https://${PANEL_DOMAIN}/login"
    PANEL_URL_ADMIN="https://${PANEL_DOMAIN}/admin/login"
  else
    PANEL_URL_CLIENT="http://${PANEL_DOMAIN}/login"
    PANEL_URL_ADMIN="http://${PANEL_DOMAIN}/admin/login"
  fi
else
  log "Skipping nginx — panels listen directly on ports ${CLIENT_PORT} and ${ADMIN_PORT}"
  PANEL_URL_CLIENT="http://${ENTRY_IP}:${CLIENT_PORT}/login"
  PANEL_URL_ADMIN="http://${ENTRY_IP}:${ADMIN_PORT}/admin/login"
fi

# --- Xray (VLESS+Reality + Shadowsocks 2022) ---
XRAY_INSTALLED="no"
if [[ "$XRAY_SKIP" == "1" ]]; then
  log "Xray skipped (WG_SKIP_XRAY=1)"
elif [[ -n "$XRAY_REALITY_SNI" ]]; then
  log "Installing Xray (Reality SNI: ${XRAY_REALITY_SNI})..."
  if WG_XRAY_SERVER_IP="$ENTRY_IP" \
     WG_XRAY_REALITY_SNI="$XRAY_REALITY_SNI" \
     WG_XRAY_WS_DOMAIN="$XRAY_WS_DOMAIN" \
     bash "$SCRIPT_DIR/install-xray.sh"; then
    XRAY_INSTALLED="yes"
  else
    warn "Xray install failed — run manually later:"
    warn "  sudo WG_XRAY_REALITY_SNI=${XRAY_REALITY_SNI} wg-ops install-xray"
  fi
else
  log "Xray skipped — set WG_XRAY_REALITY_SNI to install, or run: sudo wg-ops install-xray"
fi

bash "$SCRIPT_DIR/test-connectivity.sh" --role entry || true

# Print summary last so keys are not scrolled away by connectivity checks
# (and stay visible above wg-ops "Press Enter" when installed from the menu).
cat <<EOF

=== ENTRY server ready ===
Client Endpoint (devices): ${WG_ENDPOINT}
Client server public key  : ${CLIENT_PUB}
  (saved: /etc/wireguard/clients-server.pub)
Tunnel public key (entry) : ${TUNNEL_PUB}
  (saved: /etc/wireguard/tunnel-entry.pub)

Operator CLI:
  sudo wg-ops pull
  sudo wg-ops test --role entry
  sudo wg-ops diagnose --role entry
  sudo wg-ops tune --role entry

Web panels:
  ${PANEL_URL_CLIENT}
  ${PANEL_URL_ADMIN}
Admin user                : ${ADMIN_USER}
Xray protocols            : ${XRAY_INSTALLED}

IMPORTANT — on the exit server, run:
  sudo wg-ops add-peer ${TUNNEL_PUB} ${ENTRY_IP}

Cloud firewall: allow UDP ${CLIENT_PORT_WG} from clients; TCP 80/443 or panel ports.

Copy the tunnel public key above before continuing (needed for add-peer on the exit).

EOF

# Pause when run as a standalone CLI install (menu path pauses itself).
if should_prompt && [[ "${WG_OPS_MENU:-0}" != "1" ]]; then
  read -r -p "Press Enter after you have copied the tunnel public key..." _
fi
