#!/usr/bin/env bash
# Open UDP port range for WireGuard on entry/exit (ufw + tunnel ListenPort).
#
# All client configs use ONE server port (default 51820). The range covers:
#   - client WireGuard (51820)
#   - entry tunnel return path (51822 by default)
#   - spare ports if your provider only forwards a block
#
# Usage:
#   sudo wg-ops open-ports --role entry
#   sudo WG_UDP_PORT_RANGE=51820:51830 sudo wg-ops open-ports --role entry
set -eo pipefail

if [[ -z "${WG_DEPLOY_REEXEC:-}" && ! -t 0 ]]; then
  export WG_DEPLOY_REEXEC=1
  GITHUB_RAW_BASE="${GITHUB_RAW_BASE:-https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@v1.0.19}"
  _WG_INSTALLER="$(mktemp /tmp/wg-open-ports-XXXXXX.sh)"
  curl -fsSL "$GITHUB_RAW_BASE/deploy/open-firewall-ports.sh" -o "$_WG_INSTALLER"
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
  GITHUB_RAW_BASE="${GITHUB_RAW_BASE:-https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@v1.0.19}"
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
    die "Could not detect role — use: --role entry|exit"
  fi
fi

if [[ -f /etc/wireguard/entry-server.env ]]; then
  # shellcheck disable=SC1091
  source /etc/wireguard/entry-server.env
fi
if [[ -f /etc/wireguard/exit-server.env ]]; then
  # shellcheck disable=SC1091
  source /etc/wireguard/exit-server.env
fi

export WG_CLIENT_PORT="${WG_CLIENT_PORT:-51820}"
export WG_TUNNEL_LISTEN_PORT="${WG_TUNNEL_LISTEN_PORT:-51822}"
export WG_TUNNEL_PORT="${WG_TUNNEL_PORT:-51821}"

case "$ROLE" in
  entry)
    wg_ufw_allow_udp_ports
    _had_listen="$(grep -c '^ListenPort' /etc/wireguard/wg-tunnel.conf 2>/dev/null || echo 0)"
    ensure_tunnel_listen_port_in_conf "/etc/wireguard/wg-tunnel.conf" "$WG_TUNNEL_LISTEN_PORT"
    if [[ "$_had_listen" -eq 0 ]] && grep -q '^ListenPort' /etc/wireguard/wg-tunnel.conf 2>/dev/null; then
      log "Restart wg-tunnel to apply ListenPort:"
      log "  sudo wg-quick down wg-tunnel && sudo wg-quick up wg-tunnel"
    fi
    read -r _min _max <<< "$(wg_udp_port_range)"
    cat <<EOF

=== Entry server — also open in your CLOUD firewall ===
Inbound UDP: ${_min}-${_max}  (or at minimum ${_min} and ${WG_TUNNEL_LISTEN_PORT})
TCP panels:  ${WG_PANEL_PORT:-8088}, ${WG_ADMIN_PORT:-8090} (if not using nginx)

All client .conf files use the same endpoint port: ${WG_CLIENT_PORT:-51820}
(see /etc/wireguard/wg-endpoint)

EOF
    ;;
  exit)
    if [[ -f /etc/wireguard/exit-server.env ]]; then
      # shellcheck disable=SC1091
      source /etc/wireguard/exit-server.env
    fi
    wg_ensure_exit_tunnel_udp_input "${WG_ENTRY_PUBLIC_IP:-}"
    cat <<EOF

=== Exit server — also open in your CLOUD firewall ===
Inbound UDP: ${WG_TUNNEL_PORT} from your entry server public IP(s)
Host iptables/ufw UDP ${WG_TUNNEL_PORT} has been opened on this machine.

EOF
    ;;
  *)
    die "Usage: $0 --role entry|exit|auto"
    ;;
esac
