#!/usr/bin/env bash
# Point entry server wg-tunnel at a new exit VPS.
#
# Usage:
#   sudo WG_EXIT_PUBLIC_IP=EXIT_IP \
#        WG_EXIT_TUNNEL_PUB='EXIT_TUNNEL_PUBKEY' \
#        WG_EXIT_TUNNEL_PORT=51821 \
#        wg-ops change-exit
#
# Or:
#   sudo wg-ops change-exit --exit-ip EXIT_IP --tunnel-pub 'EXIT_TUNNEL_PUBKEY' [--port 51821]
#   sudo bash /opt/wg-ops/change-exit-server.sh --exit-ip EXIT_IP --tunnel-pub 'EXIT_TUNNEL_PUBKEY'
set -eo pipefail

if [[ -z "${WG_DEPLOY_REEXEC:-}" && ! -t 0 ]]; then
  export WG_DEPLOY_REEXEC=1
  GITHUB_RAW_BASE="${GITHUB_RAW_BASE:-https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@v1.0.10}"
  _WG_INSTALLER="$(mktemp /tmp/wg-change-exit-XXXXXX.sh)"
  curl -fsSL "$GITHUB_RAW_BASE/deploy/change-exit-server.sh" -o "$_WG_INSTALLER"
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
  GITHUB_RAW_BASE="${GITHUB_RAW_BASE:-https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@v1.0.10}"
  curl -fsSL "$GITHUB_RAW_BASE/deploy/repo.conf" -o "$_BOOT/deploy/repo.conf"
  curl -fsSL "$GITHUB_RAW_BASE/deploy/lib/common.sh" -o "$_BOOT/deploy/lib/common.sh"
  SCRIPT_DIR="$_BOOT/deploy"
  # shellcheck source=lib/common.sh
  source "$SCRIPT_DIR/lib/common.sh"
fi
set -u
require_root
require_entry_server

TUNNEL_CONF="/etc/wireguard/wg-tunnel.conf"
TUNNEL_IF="${WG_TUNNEL_IF:-wg-tunnel}"
ENV_FILE="/etc/wireguard/entry-server.env"
EXIT_IP="${WG_EXIT_PUBLIC_IP:-}"
EXIT_PORT="${WG_EXIT_TUNNEL_PORT:-51821}"
EXIT_PUB="${WG_EXIT_TUNNEL_PUB:-}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --exit-ip)
      EXIT_IP="${2:-}"
      shift 2
      ;;
    --tunnel-pub|--exit-pub)
      EXIT_PUB="${2:-}"
      shift 2
      ;;
    --port|--tunnel-port)
      EXIT_PORT="${2:-}"
      shift 2
      ;;
    -h|--help)
      sed -n '2,12p' "$0"
      exit 0
      ;;
    *)
      die "Unknown option: $1 (use --exit-ip, --tunnel-pub, --port)"
      ;;
  esac
done

[[ -n "$EXIT_IP" ]] || die "Set WG_EXIT_PUBLIC_IP or --exit-ip"
[[ -n "$EXIT_PUB" ]] || die "Set WG_EXIT_TUNNEL_PUB or --tunnel-pub (from install-exit-server.sh on new exit)"

if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  EXIT_PORT="${WG_EXIT_TUNNEL_PORT:-$EXIT_PORT}"
fi

[[ -f "$TUNNEL_CONF" ]] || die "Missing $TUNNEL_CONF — run install-entry-server.sh first"

log "=== Change exit server ==="
log "New exit endpoint: ${EXIT_IP}:${EXIT_PORT}"
log "New tunnel pubkey: ${EXIT_PUB:0:20}..."

backup_wg_configs "change-exit"

# Update peer block in wg-tunnel.conf
if grep -q '^PublicKey = ' "$TUNNEL_CONF"; then
  sed -i -E "s|^PublicKey = .*|PublicKey = ${EXIT_PUB}|" "$TUNNEL_CONF"
fi
if grep -q '^Endpoint = ' "$TUNNEL_CONF"; then
  sed -i -E "s|^Endpoint = .*|Endpoint = ${EXIT_IP}:${EXIT_PORT}|" "$TUNNEL_CONF"
else
  die "No Endpoint line in $TUNNEL_CONF"
fi

if [[ -f "$ENV_FILE" ]]; then
  if grep -q '^WG_EXIT_IP=' "$ENV_FILE"; then
    sed -i "s|^WG_EXIT_IP=.*|WG_EXIT_IP=${EXIT_IP}|" "$ENV_FILE"
  else
    echo "WG_EXIT_IP=${EXIT_IP}" >> "$ENV_FILE"
  fi
  if grep -q '^WG_EXIT_TUNNEL_PORT=' "$ENV_FILE"; then
    sed -i "s|^WG_EXIT_TUNNEL_PORT=.*|WG_EXIT_TUNNEL_PORT=${EXIT_PORT}|" "$ENV_FILE"
  else
    echo "WG_EXIT_TUNNEL_PORT=${EXIT_PORT}" >> "$ENV_FILE"
  fi
  log "Updated ${ENV_FILE}"
fi

export WG_TUNNEL_IF="$TUNNEL_IF"
if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$ENV_FILE"
fi
wg syncconf "$TUNNEL_IF" <(wg-quick strip "$TUNNEL_CONF") 2>/dev/null \
  || wg-quick down "$TUNNEL_IF" 2>/dev/null && wg-quick up "$TUNNEL_CONF"

apply_entry_vpn_routing_fix

ENTRY_PUB=""
if [[ -f /etc/wireguard/tunnel-entry.pub ]]; then
  ENTRY_PUB="$(< /etc/wireguard/tunnel-entry.pub)"
fi
ENTRY_IP="${WG_ENTRY_PUBLIC_IP:-}"
if [[ -z "$ENTRY_IP" && -f /etc/wireguard/wg-endpoint ]]; then
  ENTRY_IP="$(tr -d '[:space:]' < /etc/wireguard/wg-endpoint | cut -d: -f1)"
fi

if command -v wg-client >/dev/null 2>&1; then
  wg-client sync-vpn-modes 2>/dev/null || true
fi

cat <<EOF

=== Exit server change applied on entry ===
Tunnel peer now: ${EXIT_IP}:${EXIT_PORT}

NEXT — on the NEW exit server:
  sudo wg-ops add-peer '${ENTRY_PUB}' '${ENTRY_IP:-ENTRY_PUBLIC_IP}'

On the OLD exit server (if replacing):
  sudo wg set ${TUNNEL_IF} peer OLD_TUNNEL_PUBKEY remove

Cloud firewall: allow UDP ${EXIT_PORT} from entry server egress IP.

Verify on entry:
  wg show ${TUNNEL_IF}
  sudo wg-ops test --role entry

EOF
