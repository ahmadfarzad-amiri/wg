#!/usr/bin/env bash
# Replace stale client Endpoint IPs in all WireGuard client configs on the entry server.
#
# Usage:
#   sudo bash deploy/fix-client-endpoint.sh 198.51.100.10:51820
#   sudo bash deploy/fix-client-endpoint.sh --old 198.51.100.20 --new 198.51.100.10:51820
#   sudo WG_ENTRY_PUBLIC_IP=198.51.100.10 bash deploy/fix-client-endpoint.sh
set -eo pipefail

if [[ -z "${WG_DEPLOY_REEXEC:-}" && ! -t 0 ]]; then
  export WG_DEPLOY_REEXEC=1
  GITHUB_RAW_BASE="${GITHUB_RAW_BASE:-https://raw.githubusercontent.com/ahmadfarzad-amiri/wg/main}"
  _WG_INSTALLER="$(mktemp /tmp/wg-fix-endpoint-XXXXXX.sh)"
  curl -fsSL "$GITHUB_RAW_BASE/deploy/fix-client-endpoint.sh" -o "$_WG_INSTALLER"
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
  GITHUB_RAW_BASE="${GITHUB_RAW_BASE:-https://raw.githubusercontent.com/ahmadfarzad-amiri/wg/main}"
  curl -fsSL "$GITHUB_RAW_BASE/deploy/repo.conf" -o "$_BOOT/deploy/repo.conf"
  curl -fsSL "$GITHUB_RAW_BASE/deploy/lib/common.sh" -o "$_BOOT/deploy/lib/common.sh"
  SCRIPT_DIR="$_BOOT/deploy"
  # shellcheck source=lib/common.sh
  source "$SCRIPT_DIR/lib/common.sh"
fi
set -u
require_root
require_entry_server

OLD_IP="${WG_OLD_ENTRY_IP:-}"
NEW_EP=""
CLIENT_DIR="${WG_CLIENT_DIR:-/etc/wireguard/clients}"
ENV_FILE="/etc/wireguard/entry-server.env"
CLIENT_PORT="${WG_CLIENT_PORT:-51820}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --old)
      OLD_IP="${2:-}"
      shift 2
      ;;
    --new)
      NEW_EP="${2:-}"
      shift 2
      ;;
    -h|--help)
      sed -n '2,8p' "$0"
      exit 0
      ;;
    *)
      NEW_EP="$1"
      shift
      ;;
  esac
done

if [[ -z "$NEW_EP" ]]; then
  if [[ -n "${WG_ENTRY_PUBLIC_IP:-}" ]]; then
    NEW_EP="${WG_ENTRY_PUBLIC_IP}:${CLIENT_PORT}"
  else
    _pub="$(detect_public_ip || true)"
    [[ -n "$_pub" && "$_pub" != "127.0.0.1" ]] || die "Pass NEW_ENDPOINT (e.g. 198.51.100.10:51820) or set WG_ENTRY_PUBLIC_IP"
    NEW_EP="${_pub}:${CLIENT_PORT}"
  fi
fi

NEW_IP="${NEW_EP%%:*}"
NEW_PORT="${NEW_EP#*:}"
[[ "$NEW_PORT" == "$NEW_EP" ]] && NEW_PORT="$CLIENT_PORT"

if [[ -z "$OLD_IP" ]]; then
  if [[ -f /etc/wireguard/wg-endpoint ]]; then
    OLD_IP="$(cut -d: -f1 </etc/wireguard/wg-endpoint)"
  elif [[ -f "$ENV_FILE" ]] && grep -q '^WG_ENDPOINT=' "$ENV_FILE"; then
    OLD_IP="$(grep -m1 '^WG_ENDPOINT=' "$ENV_FILE" | cut -d= -f2- | cut -d: -f1 | tr -d \"\' )"
  fi
fi
[[ -n "$OLD_IP" ]] || die "Set --old OLD_IP or WG_OLD_ENTRY_IP (current entry IP to replace)"

log "Old entry IP to replace: ${OLD_IP}"
log "New client endpoint:   ${NEW_EP}"

backup_wg_configs "fix-endpoint"

write_wg_endpoint "$NEW_EP"

if [[ -f "$ENV_FILE" ]]; then
  if grep -q '^WG_ENDPOINT=' "$ENV_FILE"; then
    sed -i "s|^WG_ENDPOINT=.*|WG_ENDPOINT=${NEW_EP}|" "$ENV_FILE"
  else
    echo "WG_ENDPOINT=${NEW_EP}" >> "$ENV_FILE"
  fi
  if grep -q '^WG_DEFAULT_ENDPOINT=' "$ENV_FILE"; then
    sed -i "s|^WG_DEFAULT_ENDPOINT=.*|WG_DEFAULT_ENDPOINT=${NEW_EP}|" "$ENV_FILE"
  else
    echo "WG_DEFAULT_ENDPOINT=${NEW_EP}" >> "$ENV_FILE"
  fi
  log "Updated ${ENV_FILE}"
fi

fixed=0
if [[ -d "$CLIENT_DIR" ]]; then
  shopt -s nullglob
  for f in "$CLIENT_DIR"/*.conf; do
    if grep -qE "^Endpoint = ${OLD_IP}(:[0-9]+)?" "$f"; then
      sed -i -E "s|^Endpoint = ${OLD_IP}(:[0-9]+)?|Endpoint = ${NEW_EP}|" "$f"
      log "Updated $(basename "$f")"
      fixed=$((fixed + 1))
    fi
  done
  shopt -u nullglob
fi

for extra in /etc/wireguard/*.conf; do
  [[ -f "$extra" ]] || continue
  [[ "$extra" == *wg-clients.conf ]] && continue
  [[ "$extra" == *wg-tunnel.conf ]] && continue
  if grep -qE "^Endpoint = ${OLD_IP}" "$extra" 2>/dev/null; then
    sed -i -E "s|^Endpoint = ${OLD_IP}(:[0-9]+)?|Endpoint = ${NEW_EP}|" "$extra"
    log "Updated ${extra}"
    fixed=$((fixed + 1))
  fi
done

grep -rFl "$OLD_IP" /etc/wireguard 2>/dev/null | while read -r path; do
  case "$path" in
    *.conf|*entry-server.env|*wg-endpoint)
      ;;
    *)
      continue
      ;;
  esac
  if grep -q "$OLD_IP" "$path" 2>/dev/null; then
    sed -i "s|${OLD_IP}|${NEW_IP}|g" "$path"
    log "Patched reference in ${path}"
  fi
done

cat <<EOF

=== Endpoint fix complete ===
wg-endpoint     : ${NEW_EP}
Client configs updated: ${fixed}

Users with old configs must re-import the .conf from the panel or copy from:
  ${CLIENT_DIR}/

EOF

if grep -rq "$OLD_IP" "$CLIENT_DIR" 2>/dev/null; then
  warn "Some files under ${CLIENT_DIR} may still reference ${OLD_IP}:"
  grep -r "$OLD_IP" "$CLIENT_DIR" 2>/dev/null || true
fi
