#!/usr/bin/env bash
# Add entry server as peer on exit server (run on exit after entry install).
# Usage: sudo wg-ops add-peer [ENTRY_TUNNEL_PUBLIC_KEY] [ENTRY_PUBLIC_IP]
set -eo pipefail

# curl | bash: save to a temp file and re-run so stdin is not the script body.
if [[ -z "${WG_DEPLOY_REEXEC:-}" && ! -t 0 ]]; then
  export WG_DEPLOY_REEXEC=1
  GITHUB_RAW_BASE="${GITHUB_RAW_BASE:-https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@v1.0.18}"
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
  GITHUB_RAW_BASE="${GITHUB_RAW_BASE:-https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@v1.0.18}"
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

ENTRY_PUB="$(wg_strip_wg_key "${1:-${WG_ENTRY_TUNNEL_PUB:-}}")"
ENTRY_IP="${2:-${WG_ENTRY_PUBLIC_IP:-}}"

if [[ -z "$ENTRY_PUB" ]]; then
  if should_prompt; then
    prompt ENTRY_PUB "Entry server tunnel public key" ""
    ENTRY_PUB="$(wg_strip_wg_key "$ENTRY_PUB")"
  else
    die "Set ENTRY_TUNNEL_PUBLIC_KEY argument or WG_ENTRY_TUNNEL_PUB"
  fi
fi

[[ -n "$ENTRY_PUB" ]] || die "Entry tunnel public key is empty"
if [[ "${#ENTRY_PUB}" -lt 40 ]]; then
  die "Entry tunnel public key looks too short (${#ENTRY_PUB} chars) — paste the full key from entry: sudo cat /etc/wireguard/tunnel-entry.pub"
fi

if [[ -z "$ENTRY_IP" ]] && should_prompt; then
  prompt ENTRY_IP "Entry server public IP (for firewall allow)" ""
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

# Replace any stale live peers so only this entry is configured.
while read -r p; do
  [[ -n "$p" ]] || continue
  if [[ "$p" != "$ENTRY_PUB" ]]; then
    log "Removing stale tunnel peer ${p:0:20}..."
    wg set "$TUNNEL_IF" peer "$p" remove 2>/dev/null || true
  fi
done < <(wg show "$TUNNEL_IF" peers 2>/dev/null || true)

wg set "$TUNNEL_IF" peer "$ENTRY_PUB" allowed-ips "${CLIENT_CIDR},${TUNNEL_PEER_IP}"
wg_exit_tunnel_routes_up "$CLIENT_CIDR" "$TUNNEL_PEER_IP" "$TUNNEL_IF"
printf '%s\n' "$ENTRY_PUB" > /etc/wireguard/tunnel-entry.pub
chmod 600 /etc/wireguard/tunnel-entry.pub

# Persist entry IP for later firewall repairs.
if [[ -n "$ENTRY_IP" && -f /etc/wireguard/exit-server.env ]]; then
  if grep -q '^WG_ENTRY_PUBLIC_IP=' /etc/wireguard/exit-server.env; then
    sed -i "s|^WG_ENTRY_PUBLIC_IP=.*|WG_ENTRY_PUBLIC_IP=${ENTRY_IP}|" /etc/wireguard/exit-server.env
  else
    echo "WG_ENTRY_PUBLIC_IP=${ENTRY_IP}" >> /etc/wireguard/exit-server.env
  fi
fi

wg_ensure_exit_tunnel_udp_input "$ENTRY_IP"

log "Added entry server peer to $TUNNEL_IF (persisted in $TUNNEL_CONF)"
if [[ -f /etc/wireguard/exit-server.env ]]; then
  # shellcheck disable=SC1091
  source /etc/wireguard/exit-server.env
fi
apply_exit_vpn_routing_fix
wg show "$TUNNEL_IF"

cat <<EOF

=== Entry peer linked on exit ===
Host firewall: UDP ${WG_TUNNEL_PORT:-51821} accepted on INPUT (+ ufw).

REQUIRED — also open in the EXIT cloud/provider firewall:
  UDP ${WG_TUNNEL_PORT:-51821} from entry IP ${ENTRY_IP:-ENTRY_PUBLIC_IP}

On ENTRY confirm egress IP matches that allow-list:
  curl -4 ifconfig.me

Then on ENTRY:
  sudo wg show wg-tunnel
  ping -c 3 10.200.0.1
  sudo wg-ops check-tunnel --role entry

EOF
