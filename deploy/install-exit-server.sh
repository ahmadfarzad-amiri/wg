#!/usr/bin/env bash
# Exit VPS — internet egress via site-to-site tunnel from entry server.
# Clients never connect here directly.
#
# phone/laptop → entry server → encrypted tunnel → THIS server → internet
#
# One-liner:
#   curl -fsSL https://raw.githubusercontent.com/ahmadfarzad-amiri/wg/main/deploy/install-exit-server.sh | sudo bash
set -euo pipefail

_WG_SCRIPT="${BASH_SOURCE[0]:-}"
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
  fetch_deploy_helper_scripts add-entry-peer.sh test-connectivity.sh
fi
require_root
install_wg_tools

REPO_DIR="${WG_REPO_DIR:-/opt/wg-src}"
TUNNEL_PORT="51821"
TUNNEL_IF="wg-tunnel"
CLIENT_CIDR="10.10.10.0/24"
TUNNEL_LOCAL="10.200.0.1/30"
TUNNEL_PEER_IP="10.200.0.2"

log "=== EXIT server — internet egress ==="
log "Source: ${GITHUB_REPO_URL}"
log "Clients connect to the entry server, not this host."
echo ""

PUBLIC_IP="$(detect_public_ip)"
prompt PUBLIC_IP "This server's public IP (exit)" "$PUBLIC_IP"
prompt TUNNEL_PORT "Tunnel UDP port (entry server connects here)" "51821"
prompt CLIENT_CIDR "Client subnet forwarded from entry" "10.10.10.0/24"

DEF_IF="$(default_route_iface)"
DEF_IF="${DEF_IF:-eth0}"

ensure_wg_dirs

TUNNEL_PRIV="$(wg genkey)"
TUNNEL_PUB="$(printf '%s' "$TUNNEL_PRIV" | wg pubkey)"
TUNNEL_CONF="/etc/wireguard/${TUNNEL_IF}.conf"

umask 077
cat > "$TUNNEL_CONF" <<EOF
[Interface]
Address = ${TUNNEL_LOCAL}
ListenPort = ${TUNNEL_PORT}
PrivateKey = ${TUNNEL_PRIV}
PostUp = iptables -t nat -A POSTROUTING -s ${CLIENT_CIDR} -o ${DEF_IF} -j MASQUERADE; iptables -A FORWARD -i ${TUNNEL_IF} -j ACCEPT; iptables -A FORWARD -o ${TUNNEL_IF} -j ACCEPT
PostDown = iptables -t nat -D POSTROUTING -s ${CLIENT_CIDR} -o ${DEF_IF} -j MASQUERADE; iptables -D FORWARD -i ${TUNNEL_IF} -j ACCEPT; iptables -D FORWARD -o ${TUNNEL_IF} -j ACCEPT
EOF
printf '%s\n' "$TUNNEL_PUB" > /etc/wireguard/tunnel-server.pub
chmod 600 "$TUNNEL_CONF" /etc/wireguard/tunnel-server.pub

if command -v ufw >/dev/null 2>&1; then
  ufw allow "${TUNNEL_PORT}/udp" || true
fi

sysctl -w net.ipv4.ip_forward=1
grep -q '^net.ipv4.ip_forward=1' /etc/sysctl.conf 2>/dev/null \
  || echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf

systemctl enable "wg-quick@${TUNNEL_IF}" 2>/dev/null || true
wg-quick down "$TUNNEL_IF" 2>/dev/null || true
wg-quick up "$TUNNEL_CONF"

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
When prompted, enter:
  Exit server IP         : ${PUBLIC_IP}
  Exit tunnel port       : ${TUNNEL_PORT}
  Exit tunnel pubkey     : ${TUNNEL_PUB}

After entry server is installed, run on THIS server:
  bash deploy/add-entry-peer.sh

EOF

prompt_yes_no ADD_PEER "Entry tunnel public key already available?" "N"
if [[ "$ADD_PEER" == "yes" ]]; then
  prompt ENTRY_TUNNEL_PUB "Entry server tunnel public key" ""
  bash "$SCRIPT_DIR/add-entry-peer.sh" "$ENTRY_TUNNEL_PUB"
fi

bash "$SCRIPT_DIR/test-connectivity.sh" --role exit || true
