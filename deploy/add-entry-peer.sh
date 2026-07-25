#!/usr/bin/env bash
# Add entry server as peer on exit server (run on exit after entry install).
# Usage: sudo wg-ops add-peer [ENTRY_TUNNEL_PUBLIC_KEY] [ENTRY_PUBLIC_IP]
set -eo pipefail

# curl | bash: save to a temp file and re-run so stdin is not the script body.
if [[ -z "${WG_DEPLOY_REEXEC:-}" && ! -t 0 ]]; then
  export WG_DEPLOY_REEXEC=1
  GITHUB_RAW_BASE="${GITHUB_RAW_BASE:-https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@v1.0.9}"
  _WG_INSTALLER="$(mktemp /tmp/wg-install-XXXXXX.sh)"
  curl -fsSL "$GITHUB_RAW_BASE/deploy/add-entry-peer.sh" -o "$_WG_INSTALLER"
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
  GITHUB_RAW_BASE="${GITHUB_RAW_BASE:-https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@v1.0.9}"
  curl -fsSL "$GITHUB_RAW_BASE/deploy/repo.conf" -o "$_BOOT/deploy/repo.conf"
  curl -fsSL "$GITHUB_RAW_BASE/deploy/lib/common.sh" -o "$_BOOT/deploy/lib/common.sh"
  SCRIPT_DIR="$_BOOT/deploy"
  # shellcheck source=lib/common.sh
  source "$SCRIPT_DIR/lib/common.sh"
fi
set -u
require_root
require_exit_server
install_wg_tools

TUNNEL_IF="${WG_TUNNEL_IF:-wg-tunnel}"
CLIENT_CIDR="${WG_CLIENT_CIDR:-10.10.10.0/24}"
TUNNEL_PEER_IP="${WG_TUNNEL_PEER_IP:-10.200.0.2/32}"
TUNNEL_CONF="/etc/wireguard/${TUNNEL_IF}.conf"

ENTRY_PUB="${1:-${WG_ENTRY_TUNNEL_PUB:-}}"
ENTRY_IP="${2:-${WG_ENTRY_PUBLIC_IP:-}}"

if [[ -z "$ENTRY_PUB" ]]; then
  if should_prompt; then
    prompt ENTRY_PUB "Entry server tunnel public key" ""
  else
    die "Set ENTRY_TUNNEL_PUBLIC_KEY argument or WG_ENTRY_TUNNEL_PUB"
  fi
fi

wg show "$TUNNEL_IF" >/dev/null 2>&1 || die "Interface $TUNNEL_IF is not up. Run install-exit-server.sh first."

backup_wg_configs "add-entry-peer"

persist_entry_tunnel_peer() {
  local pub="$1"
  local allowed="${CLIENT_CIDR},${TUNNEL_PEER_IP}"
  local tmp marker="# BEGIN ENTRY TUNNEL PEER"

  if [[ ! -f "$TUNNEL_CONF" ]]; then
    die "Missing $TUNNEL_CONF"
  fi

  awk -v marker="$marker" '
    $0 ~ marker { skip=1; next }
    skip && /^# END ENTRY TUNNEL PEER/ { skip=0; next }
    !skip { print }
  ' "$TUNNEL_CONF" > "${TUNNEL_CONF}.tmp"

  cat >> "${TUNNEL_CONF}.tmp" <<EOF

${marker}
[Peer]
PublicKey = ${pub}
AllowedIPs = ${allowed}
# END ENTRY TUNNEL PEER
EOF

  chmod 600 "${TUNNEL_CONF}.tmp"
  mv "${TUNNEL_CONF}.tmp" "$TUNNEL_CONF"
}

persist_entry_tunnel_peer "$ENTRY_PUB"
wg set "$TUNNEL_IF" peer "$ENTRY_PUB" allowed-ips "${CLIENT_CIDR},${TUNNEL_PEER_IP}"
wg_exit_tunnel_routes_up "$CLIENT_CIDR" "$TUNNEL_PEER_IP" "$TUNNEL_IF"
printf '%s\n' "$ENTRY_PUB" > /etc/wireguard/tunnel-entry.pub
chmod 600 /etc/wireguard/tunnel-entry.pub

if command -v ufw >/dev/null 2>&1 && [[ -n "$ENTRY_IP" ]]; then
  ufw allow from "$ENTRY_IP" to any port "${WG_TUNNEL_PORT:-51821}" proto udp comment 'wg-tunnel entry' || true
fi

log "Added entry server peer to $TUNNEL_IF (persisted in $TUNNEL_CONF)"
if [[ -f /etc/wireguard/exit-server.env ]]; then
  # shellcheck disable=SC1091
  source /etc/wireguard/exit-server.env
fi
apply_exit_vpn_routing_fix
wg show "$TUNNEL_IF"
