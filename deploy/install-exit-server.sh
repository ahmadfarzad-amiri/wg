#!/usr/bin/env bash
# Exit VPS — internet egress via site-to-site tunnel from entry server.
#
# Non-interactive (recommended):
#   WG_EXIT_PUBLIC_IP=203.0.113.50 WG_TUNNEL_PORT=51821 sudo bash install-exit-server.sh
#
# Upgrade (preserve tunnel keys):
#   WG_INSTALL_MODE=upgrade sudo bash install-exit-server.sh
set -eo pipefail

if [[ -z "${WG_DEPLOY_REEXEC:-}" && ! -t 0 ]]; then
  export WG_DEPLOY_REEXEC=1
  GITHUB_RAW_BASE="${GITHUB_RAW_BASE:-https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@main}"
  _WG_INSTALLER="$(mktemp /tmp/wg-install-XXXXXX.sh)"
  curl -fsSL "$GITHUB_RAW_BASE/deploy/install-exit-server.sh" -o "$_WG_INSTALLER"
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
  GITHUB_RAW_BASE="${GITHUB_RAW_BASE:-https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@main}"
  curl -fsSL "$GITHUB_RAW_BASE/deploy/repo.conf" -o "$_BOOT/deploy/repo.conf"
  curl -fsSL "$GITHUB_RAW_BASE/deploy/lib/common.sh" -o "$_BOOT/deploy/lib/common.sh"
  SCRIPT_DIR="$_BOOT/deploy"
  # shellcheck source=lib/common.sh
  source "$SCRIPT_DIR/lib/common.sh"
  fetch_deploy_helper_scripts add-entry-peer.sh test-connectivity.sh
fi
set -u
require_root
install_wg_tools

TUNNEL_IF="wg-tunnel"
CLIENT_CIDR="10.10.10.0/24"
TUNNEL_LOCAL="10.200.0.1/30"
TUNNEL_CONF="/etc/wireguard/${TUNNEL_IF}.conf"

log "=== EXIT server — internet egress ==="
log "Source: ${GITHUB_REPO_URL}"

if [[ -n "${WG_EXIT_PUBLIC_IP:-}" ]]; then
  PUBLIC_IP="$WG_EXIT_PUBLIC_IP"
else
  PUBLIC_IP="$(detect_public_ip)"
fi
TUNNEL_PORT="${WG_TUNNEL_PORT:-51821}"
CLIENT_CIDR="${WG_CLIENT_CIDR:-10.10.10.0/24}"

if should_prompt; then
  prompt PUBLIC_IP "This server's public IP (exit)" "$PUBLIC_IP"
  prompt TUNNEL_PORT "Tunnel UDP port (entry server connects here)" "$TUNNEL_PORT"
  prompt CLIENT_CIDR "Client subnet forwarded from entry" "$CLIENT_CIDR"
else
  log "Exit public IP  : ${PUBLIC_IP}"
  log "Tunnel UDP port : ${TUNNEL_PORT}"
  log "Client subnet   : ${CLIENT_CIDR}"
  if [[ "$PUBLIC_IP" == "127.0.0.1" ]]; then
    warn "Could not detect public IP — set WG_EXIT_PUBLIC_IP and re-run, or use WG_INSTALL_INTERACTIVE=1"
  fi
fi

require_fresh_or_upgrade "$TUNNEL_CONF"

DEF_IF="$(default_route_iface)"
DEF_IF="${DEF_IF:-eth0}"
ensure_wg_dirs

if ! preserve_tunnel_keys "$TUNNEL_CONF" /etc/wireguard/tunnel-server.pub; then
  TUNNEL_PRIV="$(wg genkey)"
  TUNNEL_PUB="$(printf '%s' "$TUNNEL_PRIV" | wg pubkey)"
fi

umask 077
cat > "$TUNNEL_CONF" <<EOF
[Interface]
Address = ${TUNNEL_LOCAL}
ListenPort = ${TUNNEL_PORT}
PrivateKey = ${TUNNEL_PRIV}
PostUp = iptables -t nat -A POSTROUTING -s ${CLIENT_CIDR} -o ${DEF_IF} -j MASQUERADE; iptables -A FORWARD -i ${TUNNEL_IF} -j ACCEPT; iptables -A FORWARD -o ${TUNNEL_IF} -j ACCEPT
PostDown = iptables -t nat -D POSTROUTING -s ${CLIENT_CIDR} -o ${DEF_IF} -j MASQUERADE; iptables -D FORWARD -i ${TUNNEL_IF} -j ACCEPT; iptables -D FORWARD -o ${TUNNEL_IF} -j ACCEPT
EOF

if [[ -f /etc/wireguard/tunnel-entry.pub ]]; then
  ENTRY_PEER_PUB="$(< /etc/wireguard/tunnel-entry.pub)"
  if [[ -n "$ENTRY_PEER_PUB" ]]; then
    cat >> "$TUNNEL_CONF" <<EOF

# BEGIN ENTRY TUNNEL PEER
[Peer]
PublicKey = ${ENTRY_PEER_PUB}
AllowedIPs = ${CLIENT_CIDR},10.200.0.2/32
# END ENTRY TUNNEL PEER
EOF
  fi
fi

printf '%s\n' "$TUNNEL_PUB" > /etc/wireguard/tunnel-server.pub
chmod 600 "$TUNNEL_CONF" /etc/wireguard/tunnel-server.pub

if command -v ufw >/dev/null 2>&1; then
  if [[ -n "${WG_ENTRY_PUBLIC_IP:-}" ]]; then
    ufw allow from "${WG_ENTRY_PUBLIC_IP}" to any port "${TUNNEL_PORT}" proto udp || true
  else
    ufw allow "${TUNNEL_PORT}/udp" || true
  fi
fi
maybe_enable_ufw

sysctl -w net.ipv4.ip_forward=1
grep -q '^net.ipv4.ip_forward=1' /etc/sysctl.conf 2>/dev/null \
  || echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf

systemctl enable "wg-quick@${TUNNEL_IF}" 2>/dev/null || true
wg_quick_up "$TUNNEL_CONF" "$TUNNEL_IF"

write_env_file /etc/wireguard/exit-server.env \
  WG_ROLE exit \
  WG_TUNNEL_IF "$TUNNEL_IF" \
  WG_TUNNEL_PORT "$TUNNEL_PORT" \
  WG_TUNNEL_PUBLIC_IP "$PUBLIC_IP" \
  WG_CLIENT_CIDR "$CLIENT_CIDR"

cat <<EOF

=== EXIT server ready ===
Tunnel endpoint     : ${PUBLIC_IP}:${TUNNEL_PORT}
Tunnel public key   : ${TUNNEL_PUB}
Client subnet       : ${CLIENT_CIDR} (from entry server)

NEXT: run install-entry-server.sh on your ENTRY VPS.
After entry install, on THIS server:
  bash deploy/add-entry-peer.sh ENTRY_TUNNEL_PUB [ENTRY_PUBLIC_IP]

Cloud firewall: allow UDP ${TUNNEL_PORT} (ideally only from entry server IP).

EOF

ADD_PEER="no"
ENTRY_TUNNEL_PUB="${WG_ENTRY_TUNNEL_PUB:-}"
if [[ -n "$ENTRY_TUNNEL_PUB" ]]; then
  bash "$SCRIPT_DIR/add-entry-peer.sh" "$ENTRY_TUNNEL_PUB" "${WG_ENTRY_PUBLIC_IP:-}"
elif should_prompt; then
  prompt_yes_no ADD_PEER "Entry tunnel public key already available?" "N"
  if [[ "$ADD_PEER" == "yes" ]]; then
    prompt ENTRY_TUNNEL_PUB "Entry server tunnel public key" ""
    bash "$SCRIPT_DIR/add-entry-peer.sh" "$ENTRY_TUNNEL_PUB"
  fi
fi

bash "$SCRIPT_DIR/test-connectivity.sh" --role exit || true
