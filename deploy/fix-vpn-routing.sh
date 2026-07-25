#!/usr/bin/env bash
# Fix one-way client traffic (TX up, RX stuck) on entry/exit VPN stack.
#
# Applies:
#   Exit — client subnet routes via wg-tunnel, NAT, forward rules
#   Entry — policy routing, client subnet → wg-clients, rp_filter, Docker bypass
#
# Usage: sudo wg-ops fix-routing [--role entry|exit|auto]
set -eo pipefail

if [[ -z "${WG_DEPLOY_REEXEC:-}" && ! -t 0 ]]; then
  export WG_DEPLOY_REEXEC=1
  GITHUB_RAW_BASE="${GITHUB_RAW_BASE:-https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@v1.0.18}"
  _WG_INSTALLER="$(mktemp /tmp/wg-fix-routing-XXXXXX.sh)"
  curl -fsSL "$GITHUB_RAW_BASE/deploy/fix-vpn-routing.sh" -o "$_WG_INSTALLER"
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

ROLE="${1:-auto}"
if [[ "$ROLE" == "--role" ]]; then
  ROLE="${2:-auto}"
fi

if [[ "$ROLE" == "auto" ]]; then
  if [[ -f /etc/wireguard/entry-server.env ]]; then
    ROLE="entry"
  elif [[ -f /etc/wireguard/exit-server.env ]]; then
    ROLE="exit"
  else
    die "Could not detect role — use: sudo wg-ops fix-routing --role entry|exit"
  fi
fi

fix_exit() {
  if [[ -f /etc/wireguard/exit-server.env ]]; then
    # shellcheck disable=SC1091
    source /etc/wireguard/exit-server.env
  fi
  apply_exit_vpn_routing_fix
  if [[ ! -f /etc/wireguard/tunnel-entry.pub ]]; then
    warn "Exit: entry tunnel peer not configured — run add-entry-peer.sh on this host"
  fi
  wg show "${WG_TUNNEL_IF:-wg-tunnel}" 2>/dev/null || warn "wg-tunnel is not up"
}

fix_entry() {
  if [[ -f /etc/wireguard/entry-server.env ]]; then
    # shellcheck disable=SC1091
    source /etc/wireguard/entry-server.env
  fi
  apply_entry_vpn_routing_fix
  if ! tunnel_handshake_recent 180 2>/dev/null; then
    warn "Entry: wg-tunnel handshake to exit is stale or missing — check exit peer + UDP ${WG_EXIT_TUNNEL_PORT:-51821}"
  fi
  log "Re-test from a connected client after this fix (ping 1.1.1.1, open a website)"
}

case "$ROLE" in
  entry) fix_entry ;;
  exit) fix_exit ;;
  *)
    die "Usage: sudo wg-ops fix-routing [--role entry|exit|auto]"
    ;;
esac

if [[ -f "$SCRIPT_DIR/test-connectivity.sh" ]]; then
  bash "$SCRIPT_DIR/test-connectivity.sh" --role "$ROLE" || true
fi
