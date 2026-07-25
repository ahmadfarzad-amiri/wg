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
#
# Handshake requires a matching step on the NEW exit:
#   sudo wg-ops add-peer 'ENTRY_TUNNEL_PUBKEY' 'ENTRY_PUBLIC_IP'
set -eo pipefail

if [[ -z "${WG_DEPLOY_REEXEC:-}" && ! -t 0 ]]; then
  export WG_DEPLOY_REEXEC=1
  GITHUB_RAW_BASE="${GITHUB_RAW_BASE:-https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@v1.0.18}"
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
  GITHUB_RAW_BASE="${GITHUB_RAW_BASE:-https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@v1.0.18}"
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
# Capture port from the invoking environment before sourcing on-disk env (which may be stale).
EXIT_PORT_FROM_ENV=0
if [[ -n "${WG_EXIT_TUNNEL_PORT:-}" ]]; then
  EXIT_PORT="$WG_EXIT_TUNNEL_PORT"
  EXIT_PORT_FROM_ENV=1
else
  EXIT_PORT="51821"
fi
EXIT_PUB="${WG_EXIT_TUNNEL_PUB:-}"
PORT_FROM_CLI=0

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
      PORT_FROM_CLI=1
      shift 2
      ;;
    -h|--help)
      sed -n '2,16p' "$0"
      exit 0
      ;;
    *)
      die "Unknown option: $1 (use --exit-ip, --tunnel-pub, --port)"
      ;;
  esac
done

CURRENT_EXIT_IP=""
CURRENT_EXIT_PORT="51821"
if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  CURRENT_EXIT_IP="${WG_EXIT_IP:-${WG_EXIT_PUBLIC_IP:-}}"
  CURRENT_EXIT_PORT="${WG_EXIT_TUNNEL_PORT:-51821}"
  [[ -n "$EXIT_IP" ]] || EXIT_IP="$CURRENT_EXIT_IP"
  # Do not let on-disk env override an explicit CLI/env port the caller already set.
  if [[ "$PORT_FROM_CLI" -eq 0 && "$EXIT_PORT_FROM_ENV" -eq 0 ]]; then
    EXIT_PORT="$CURRENT_EXIT_PORT"
  fi
fi

# Menu / TTY: prompt when required values were not passed via env or flags.
if [[ -z "$EXIT_IP" || -z "$EXIT_PUB" ]] && _have_tty; then
  log "=== Change exit server ==="
  log "Point this entry at a new exit VPS (install-exit on the new host first)."
  [[ -n "$CURRENT_EXIT_IP" ]] && log "Current exit IP: ${CURRENT_EXIT_IP}"
  prompt EXIT_IP "New exit server public IP" "${EXIT_IP:-$CURRENT_EXIT_IP}"
  prompt EXIT_PORT "Exit tunnel UDP port" "${EXIT_PORT:-51821}"
  prompt EXIT_PUB "New exit tunnel public key (from install-exit on new exit)" "$EXIT_PUB"
fi

[[ -n "$EXIT_IP" ]] || die "Set WG_EXIT_PUBLIC_IP or --exit-ip"
[[ -n "$EXIT_PUB" ]] || die "Set WG_EXIT_TUNNEL_PUB or --tunnel-pub (from install-exit-server.sh on new exit)"
wg_is_port "$EXIT_PORT" || die "Invalid exit tunnel port: ${EXIT_PORT}"

[[ -f "$TUNNEL_CONF" ]] || die "Missing $TUNNEL_CONF — run install-entry-server.sh first"

log "=== Change exit server ==="
log "New exit endpoint: ${EXIT_IP}:${EXIT_PORT}"
log "New tunnel pubkey: ${EXIT_PUB:0:20}..."

backup_wg_configs "change-exit"

OLD_PEER_PUB=""
OLD_PEER_PUB="$(awk '
  /^\[Peer\]/ { p=1; next }
  p && /^PublicKey[[:space:]]*=/ {
    sub(/^[^=]*=[[:space:]]*/, "")
    gsub(/[[:space:]]/, "")
    print
    exit
  }
' "$TUNNEL_CONF")"

# Update only the first [Peer] PublicKey + Endpoint (exit peer on entry).
awk -v pub="$EXIT_PUB" -v ep="${EXIT_IP}:${EXIT_PORT}" '
  BEGIN { in_peer=0; peer_done=0; saw_endpoint=0 }
  /^\[Peer\]/ {
    if (!peer_done) { in_peer=1 } else { in_peer=0 }
    print
    next
  }
  /^\[/ {
    if (in_peer && !peer_done) {
      if (!saw_endpoint) print "Endpoint = " ep
      peer_done=1
      in_peer=0
    }
    print
    next
  }
  in_peer && !peer_done && /^PublicKey[[:space:]]*=/ {
    print "PublicKey = " pub
    next
  }
  in_peer && !peer_done && /^Endpoint[[:space:]]*=/ {
    print "Endpoint = " ep
    saw_endpoint=1
    next
  }
  { print }
  END {
    if (in_peer && !peer_done && !saw_endpoint) print "Endpoint = " ep
  }
' "$TUNNEL_CONF" > "${TUNNEL_CONF}.tmp"
chmod 600 "${TUNNEL_CONF}.tmp"
mv "${TUNNEL_CONF}.tmp" "$TUNNEL_CONF"

if ! grep -qF "PublicKey = ${EXIT_PUB}" "$TUNNEL_CONF"; then
  die "Failed to write new exit PublicKey into $TUNNEL_CONF"
fi
if ! grep -qF "Endpoint = ${EXIT_IP}:${EXIT_PORT}" "$TUNNEL_CONF"; then
  die "Failed to write new exit Endpoint into $TUNNEL_CONF"
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
  if grep -q '^WG_EXIT_TUNNEL_PUB=' "$ENV_FILE"; then
    sed -i "s|^WG_EXIT_TUNNEL_PUB=.*|WG_EXIT_TUNNEL_PUB=${EXIT_PUB}|" "$ENV_FILE"
  else
    echo "WG_EXIT_TUNNEL_PUB=${EXIT_PUB}" >> "$ENV_FILE"
  fi
  log "Updated ${ENV_FILE}"
fi

export WG_TUNNEL_IF="$TUNNEL_IF"
if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$ENV_FILE"
fi

# Apply peer change reliably: remove stale live peers, syncconf, or bounce.
# (Avoid `syncconf || down && up` — with set -e that aborts after a successful syncconf.)
wg_apply_entry_exit_peer_live() {
  local conf="$1" ifname="$2" new_pub="$3" endpoint="$4"
  if ! ip link show "$ifname" >/dev/null 2>&1; then
    log "Starting ${ifname}..."
    wg-quick up "$conf"
    return 0
  fi

  local p
  while read -r p; do
    [[ -n "$p" ]] || continue
    if [[ "$p" != "$new_pub" ]]; then
      wg set "$ifname" peer "$p" remove 2>/dev/null || true
    fi
  done < <(wg show "$ifname" peers 2>/dev/null || true)

  if wg syncconf "$ifname" <(wg-quick strip "$conf") 2>/dev/null; then
    wg set "$ifname" peer "$new_pub" endpoint "$endpoint" \
      allowed-ips 0.0.0.0/0 persistent-keepalive 25 2>/dev/null \
      || true
    log "Applied new exit peer via wg syncconf"
    return 0
  fi

  log "syncconf failed — bouncing ${ifname}"
  wg-quick down "$ifname" 2>/dev/null || true
  ip link del "$ifname" 2>/dev/null || true
  wg-quick up "$conf"
}

wg_apply_entry_exit_peer_live "$TUNNEL_CONF" "$TUNNEL_IF" "$EXIT_PUB" "${EXIT_IP}:${EXIT_PORT}"

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

# Nudge a handshake (PersistentKeepalive alone may wait up to 25s).
ping -c 1 -W 2 10.200.0.1 >/dev/null 2>&1 || true
sleep 2

HANDSHAKE_OK=0
if tunnel_handshake_recent 30 "$TUNNEL_IF" 2>/dev/null; then
  HANDSHAKE_OK=1
  log "Tunnel handshake with new exit: OK"
else
  warn "No recent handshake yet — the NEW exit must add this entry as peer (and allow UDP ${EXIT_PORT})."
fi

cat <<EOF

=== Exit server change applied on entry ===
Tunnel peer now: ${EXIT_IP}:${EXIT_PORT}
Handshake      : $([[ "$HANDSHAKE_OK" -eq 1 ]] && echo OK || echo PENDING)

REQUIRED — on the NEW exit server (no handshake without this):
  sudo wg-ops add-peer '${ENTRY_PUB:-ENTRY_TUNNEL_PUBKEY}' '${ENTRY_IP:-ENTRY_PUBLIC_IP}'

Get ENTRY_TUNNEL_PUBKEY anytime with:
  sudo cat /etc/wireguard/tunnel-entry.pub

Then on entry verify:
  sudo wg show ${TUNNEL_IF}
  ping -c 3 10.200.0.1

Cloud firewall on NEW exit: allow UDP ${EXIT_PORT} from entry egress IP.
Entry cloud firewall: allow UDP ${WG_TUNNEL_LISTEN_PORT:-51822} (tunnel return path).

EOF

if [[ -n "$OLD_PEER_PUB" && "$OLD_PEER_PUB" != "$EXIT_PUB" ]]; then
  log "Old exit peer pubkey was ${OLD_PEER_PUB:0:20}... (removed from live ${TUNNEL_IF})"
fi

if [[ "$HANDSHAKE_OK" -ne 1 ]]; then
  warn "Re-check after add-peer: sudo wg-ops test --role entry"
fi
