#!/usr/bin/env bash
# Diagnose missing entry↔exit WireGuard handshake (one-way tunnel).
#
# Usage:
#   sudo wg-ops check-tunnel --role entry
#   sudo wg-ops check-tunnel --role exit
set -eo pipefail

if [[ -z "${WG_DEPLOY_REEXEC:-}" && ! -t 0 ]]; then
  export WG_DEPLOY_REEXEC=1
  GITHUB_RAW_BASE="${GITHUB_RAW_BASE:-https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@v1.0.19}"
  _WG_INSTALLER="$(mktemp /tmp/wg-check-tunnel-XXXXXX.sh)"
  curl -fsSL "$GITHUB_RAW_BASE/deploy/check-tunnel-handshake.sh" -o "$_WG_INSTALLER"
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
  ROLE="$(server_role)"
  [[ "$ROLE" != "unknown" ]] || die "Could not detect role — use: --role entry|exit"
fi

check_exit() {
  if [[ -f /etc/wireguard/exit-server.env ]]; then
    # shellcheck disable=SC1091
    source /etc/wireguard/exit-server.env
  fi
  local port="${WG_TUNNEL_PORT:-51821}"
  local entry_ip="${WG_ENTRY_PUBLIC_IP:-}"
  if [[ -z "$entry_ip" && -f /etc/wireguard/tunnel-entry.pub ]]; then
    :
  fi

  log "=== EXIT tunnel handshake check ==="
  wg_ensure_exit_tunnel_udp_input "$entry_ip"

  local iface_pub peer_pub
  iface_pub="$(wg show wg-tunnel public-key 2>/dev/null || true)"
  peer_pub="$(wg show wg-tunnel peers 2>/dev/null | head -1 || true)"
  log "Exit iface pubkey : ${iface_pub:-(none)}"
  log "Configured peer   : ${peer_pub:-(none)}"
  if [[ -f /etc/wireguard/tunnel-server.pub ]]; then
    log "tunnel-server.pub : $(tr -d '[:space:]' < /etc/wireguard/tunnel-server.pub)"
  fi
  if [[ -f /etc/wireguard/tunnel-entry.pub ]]; then
    log "Expected entry pub: $(tr -d '[:space:]' < /etc/wireguard/tunnel-entry.pub)"
  fi

  local rx tx hs
  read -r rx tx < <(wg show wg-tunnel transfer 2>/dev/null | awk 'NF>=3 {print $2, $3; exit}')
  rx="${rx:-0}"; tx="${tx:-0}"
  hs="$(wg show wg-tunnel latest-handshakes 2>/dev/null | awk 'NF>=2 {print $2; exit}')"
  hs="${hs:-0}"
  log "Peer transfer     : rx=${rx} tx=${tx}"
  log "Latest handshake  : ${hs} (0 = never)"

  echo
  log "Listening sockets:"
  ss -ulnp 2>/dev/null | grep -E ":${port}\\b" || warn "Nothing listening on UDP ${port}"
  echo
  if command -v ufw >/dev/null 2>&1; then
    log "ufw status (udp ${port}):"
    ufw status 2>/dev/null | grep -E "${port}|Status" || true
  fi
  log "iptables INPUT udp/${port}:"
  iptables -L INPUT -n -v 2>/dev/null | head -5
  iptables -L INPUT -n -v 2>/dev/null | grep -E "udp.*dpt:${port}|dpt:${port}" || warn "No INPUT rule matched for udp/${port} (now inserted if missing)"

  echo
  if [[ "$hs" == "0" || "$rx" == "0" ]]; then
    warn "No handshake / zero RX on exit — UDP ${port} is not being accepted from entry."
    cat <<EOF

Do this NOW (two terminals on EXIT):

  Terminal A:
    sudo tcpdump -ni any udp port ${port} -c 30

  Terminal B (or from ENTRY):
    # on ENTRY: ping -c 5 10.200.0.1

If Terminal A stays empty:
  → CLOUD firewall (or wrong entry egress IP) is dropping UDP ${port}.
  → Open UDP ${port} from entry public IP in the provider panel.
  → Confirm entry egress IP: on ENTRY run  curl -4 ifconfig.me

If Terminal A shows packets from entry but handshake stays 0:
  → Re-link peer with clean keys:
    sudo wg-ops add-peer "\$(cat /etc/wireguard/tunnel-entry.pub)" ENTRY_IP

EOF
  else
    log "Handshake looks present (rx>0). Tunnel path OK on exit side."
  fi
  wg show wg-tunnel
}

check_entry() {
  if [[ -f /etc/wireguard/entry-server.env ]]; then
    # shellcheck disable=SC1091
    source /etc/wireguard/entry-server.env
  fi
  local exit_ip="${WG_EXIT_IP:-}"
  local exit_port="${WG_EXIT_TUNNEL_PORT:-51821}"
  local listen="${WG_TUNNEL_LISTEN_PORT:-51822}"
  local egress
  egress="$(curl -4fsS --max-time 5 https://api.ipify.org 2>/dev/null || curl -4fsS --max-time 5 https://ifconfig.me 2>/dev/null || true)"

  log "=== ENTRY tunnel handshake check ==="
  log "This host egress IP : ${egress:-(unknown)}  ← exit firewall must allow THIS IP"
  log "Exit endpoint       : ${exit_ip:-?}:${exit_port}"
  log "Local tunnel listen : UDP ${listen} (cloud firewall must allow inbound)"

  local iface_pub peer_pub endpoint
  iface_pub="$(wg show wg-tunnel public-key 2>/dev/null || true)"
  peer_pub="$(wg show wg-tunnel peers 2>/dev/null | head -1 || true)"
  endpoint="$(wg show wg-tunnel endpoints 2>/dev/null | awk 'NF>=2{print $2; exit}')"
  log "Entry iface pubkey  : ${iface_pub:-(none)}"
  log "Exit peer pubkey    : ${peer_pub:-(none)}"
  log "Live endpoint       : ${endpoint:-(none)}"
  if [[ -f /etc/wireguard/tunnel-entry.pub ]]; then
    log "tunnel-entry.pub    : $(tr -d '[:space:]' < /etc/wireguard/tunnel-entry.pub)"
  fi

  if [[ -n "$peer_pub" && -n "$exit_ip" ]]; then
    log "Refreshing peer endpoint ${exit_ip}:${exit_port} ..."
    wg set wg-tunnel peer "$peer_pub" endpoint "${exit_ip}:${exit_port}" \
      persistent-keepalive 25 2>/dev/null || true
  fi

  ping -c 2 -W 2 10.200.0.1 >/dev/null 2>&1 || true
  sleep 2

  local rx tx hs
  read -r rx tx < <(wg show wg-tunnel transfer 2>/dev/null | awk 'NF>=3 {print $2, $3; exit}')
  rx="${rx:-0}"; tx="${tx:-0}"
  hs="$(wg show wg-tunnel latest-handshakes 2>/dev/null | awk 'NF>=2 {print $2; exit}')"
  hs="${hs:-0}"
  log "Peer transfer       : rx=${rx} tx=${tx}"
  log "Latest handshake    : ${hs} (0 = never)"

  echo
  if [[ "$tx" -gt 0 && "$rx" -eq 0 ]]; then
    warn "ONE-WAY: entry sends (${tx} B) but receives 0 B."
    cat <<EOF

Keys on entry look configured. Exit is not answering UDP ${exit_port}.

1) On EXIT (must see packets):
     sudo tcpdump -ni any udp port ${exit_port} -c 30
2) On ENTRY (while tcpdump runs):
     ping -c 5 10.200.0.1
3) On EXIT open host + cloud firewall:
     sudo iptables -I INPUT -p udp --dport ${exit_port} -j ACCEPT
     sudo ufw allow ${exit_port}/udp
     sudo ufw allow from ${egress:-ENTRY_EGRESS_IP} to any port ${exit_port} proto udp
     # Provider panel: UDP ${exit_port} from ${egress:-ENTRY_EGRESS_IP}
4) On ENTRY cloud firewall: allow UDP ${listen} inbound.
5) Then on EXIT:
     sudo wg-ops add-peer '$(tr -d '[:space:]' < /etc/wireguard/tunnel-entry.pub 2>/dev/null || echo ENTRY_TUNNEL_PUB)' '${egress:-ENTRY_IP}'

EOF
  elif tunnel_handshake_recent 180 2>/dev/null; then
    log "Handshake OK."
    ping -c 3 -W 2 10.200.0.1 || warn "handshake ok but ping 10.200.0.1 failed (routing?)"
  else
    warn "No recent handshake — see steps above."
  fi
  wg show wg-tunnel
}

case "$ROLE" in
  exit) check_exit ;;
  entry) check_entry ;;
  *)
    die "Usage: sudo bash deploy/check-tunnel-handshake.sh --role entry|exit"
    ;;
esac
