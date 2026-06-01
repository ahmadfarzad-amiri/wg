#!/usr/bin/env bash
# Deep VPN routing diagnostics for entry/exit stack.
# Usage: sudo bash deploy/diagnose-vpn.sh [--role entry|exit|auto]
set -eo pipefail

if [[ -z "${WG_DEPLOY_REEXEC:-}" && ! -t 0 ]]; then
  export WG_DEPLOY_REEXEC=1
  GITHUB_RAW_BASE="${GITHUB_RAW_BASE:-https://raw.githubusercontent.com/ahmadfarzad-amiri/wg/main}"
  _WG_INSTALLER="$(mktemp /tmp/wg-diagnose-XXXXXX.sh)"
  curl -fsSL "$GITHUB_RAW_BASE/deploy/diagnose-vpn.sh" -o "$_WG_INSTALLER"
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

ROLE="${1:-auto}"
if [[ "$ROLE" == "--role" ]]; then
  ROLE="${2:-auto}"
fi
if [[ "$ROLE" == "auto" ]]; then
  ROLE="$(server_role)"
  [[ "$ROLE" != "unknown" ]] || die "Could not detect role — use: sudo bash deploy/diagnose-vpn.sh --role entry|exit"
fi

diag_performance() {
  log "=== Performance tuning ==="
  if [[ -f /etc/wireguard/entry-server.env ]]; then
    # shellcheck disable=SC1091
    source /etc/wireguard/entry-server.env
  elif [[ -f /etc/wireguard/exit-server.env ]]; then
    # shellcheck disable=SC1091
    source /etc/wireguard/exit-server.env
  fi
  log "WG_ENABLE_BBR=${WG_ENABLE_BBR:-1} WG_ENABLE_MSS_CLAMP=${WG_ENABLE_MSS_CLAMP:-1}"
  if [[ -f /etc/sysctl.d/99-wg-performance.conf ]]; then
    log "Performance sysctl file: present"
    grep -E 'bbr|qdisc|rmem|wmem' /etc/sysctl.d/99-wg-performance.conf 2>/dev/null || true
  else
    warn "No /etc/sysctl.d/99-wg-performance.conf — run: sudo bash deploy/tune-vpn-performance.sh"
  fi
  log "TCP congestion: $(sysctl -n net.ipv4.tcp_congestion_control 2>/dev/null || echo unknown)"
  log "Default qdisc: $(sysctl -n net.core.default_qdisc 2>/dev/null || echo unknown)"
  log "UDP rmem_max: $(sysctl -n net.core.rmem_max 2>/dev/null || echo unknown)"
  if iptables -t mangle -C FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --clamp-mss-to-pmtu 2>/dev/null; then
    log "TCP MSS clamp: enabled"
  else
    warn "TCP MSS clamp missing — run: sudo bash deploy/tune-vpn-performance.sh"
  fi
  if [[ -d /etc/wireguard/clients ]]; then
    local sample
    sample="$(find /etc/wireguard/clients -name '*.conf' 2>/dev/null | head -1)"
    if [[ -n "$sample" ]]; then
      log "Sample client MTU: $(grep -E '^MTU' "$sample" 2>/dev/null || echo 'not set')"
    fi
  fi
  if [[ -f /etc/wireguard/entry-server.env ]]; then
    log "Configured MTU defaults: WG_CLIENT_MTU=${WG_CLIENT_MTU:-1280} direct=${WG_CLIENT_MTU_DIRECT:-1420} twohop=${WG_CLIENT_MTU_TWOHOP:-1280}"
  fi
  echo
  log "Tunnel transfer counters (reset on reboot):"
  wg show wg-tunnel transfer 2>/dev/null || true
  if wg show wg-clients >/dev/null 2>&1; then
    wg show wg-clients transfer 2>/dev/null | head -5 || true
  fi
}

diag_exit() {
  local client_cidr="${WG_CLIENT_CIDR:-10.10.10.0/24}"
  if [[ -f /etc/wireguard/exit-server.env ]]; then
    # shellcheck disable=SC1091
    source /etc/wireguard/exit-server.env
    client_cidr="${WG_CLIENT_CIDR:-10.10.10.0/24}"
  fi

  log "=== EXIT diagnostics ==="
  printf 'Public IP: '; curl -4fsS --max-time 5 https://api.ipify.org 2>/dev/null || echo FAIL
  echo
  wg show wg-tunnel 2>/dev/null || warn "wg-tunnel down"
  echo
  log "Routes (must use dev wg-tunnel for client subnet):"
  ip route get 10.10.10.2 2>/dev/null || true
  ip route get 10.200.0.2 2>/dev/null || true
  echo
  log "Reachability:"
  ping -c 2 -W 2 10.200.0.2 2>/dev/null || warn "cannot ping entry tunnel IP 10.200.0.2"
  ping -c 2 -W 2 10.10.10.1 2>/dev/null || warn "cannot ping entry wg-clients gateway 10.10.10.1"
  echo
  log "NAT / FORWARD:"
  iptables -t nat -L POSTROUTING -n -v | grep -E 'MASQUERADE|10.10.10' || true
  iptables -L FORWARD -n -v | head -10
  echo
  if wg_exit_route_to_client_ok "10.10.10.2"; then
    log "Route check: 10.10.10.2 → wg-tunnel OK"
  else
    warn "Route check FAIL — run: sudo bash deploy/fix-vpn-routing.sh --role exit"
  fi
  diag_performance
}

diag_entry() {
  local client_cidr="${WG_CLIENT_CIDR:-10.10.10.0/24}"
  if [[ -f /etc/wireguard/entry-server.env ]]; then
    # shellcheck disable=SC1091
    source /etc/wireguard/entry-server.env
    client_cidr="${WG_CLIENT_CIDR:-10.10.10.0/24}"
  fi

  log "=== ENTRY diagnostics ==="
  printf 'Public IP: '; curl -4fsS --max-time 5 https://api.ipify.org 2>/dev/null || echo FAIL
  echo
  printf 'Client endpoint file: '; cat /etc/wireguard/wg-endpoint 2>/dev/null || echo MISSING
  echo
  wg show wg-clients 2>/dev/null || warn "wg-clients down"
  echo
  wg show wg-tunnel 2>/dev/null || warn "wg-tunnel down"
  echo
  log "Routes (10.10.10.2 must use dev wg-clients; client egress uses table 100):"
  ip route get 10.10.10.2 2>/dev/null || true
  ip route get 10.10.10.2 from 1.1.1.1 iif wg-tunnel 2>/dev/null || true
  ip rule show | grep -E '100|10.10.10' || true
  ip route show table 100 2>/dev/null || true
  echo
  log "rp_filter (both wg interfaces must be 0):"
  sysctl net.ipv4.conf.wg-tunnel.rp_filter net.ipv4.conf.wg-clients.rp_filter 2>/dev/null || true
  echo
  log "Reachability:"
  ping -c 2 -W 2 10.200.0.1 2>/dev/null || warn "cannot ping exit tunnel IP 10.200.0.1"
  echo
  log "FORWARD / Docker:"
  iptables -L FORWARD -n -v --line-numbers | head -15
  iptables -L DOCKER-USER -n -v 2>/dev/null | head -8 || echo "no DOCKER-USER"
  echo
  if wg_entry_client_subnet_route_ok "10.10.10.2"; then
    log "Route check: 10.10.10.2 → wg-clients OK"
  else
    warn "Route check FAIL — provider may route ${client_cidr} via LAN; run: sudo bash deploy/fix-vpn-routing.sh --role entry"
  fi
  if iptables -L DOCKER-USER -n >/dev/null 2>&1; then
    if iptables -C DOCKER-USER -i wg-tunnel -o wg-clients -j ACCEPT 2>/dev/null; then
      log "Docker bypass: wg-tunnel → wg-clients OK"
    else
      warn "Docker bypass missing — run: sudo bash deploy/fix-vpn-routing.sh --role entry"
    fi
  fi
  echo
  log "Client peers (handshake + transfer while a device is connected):"
  wg show wg-clients latest-handshakes 2>/dev/null || true
  wg show wg-clients transfer 2>/dev/null || true
  echo
  local direct=0 twohop=0
  if [[ -d /etc/wireguard/client-state ]]; then
    for f in /etc/wireguard/client-state/*.meta; do
      [[ -f "$f" ]] || continue
      if grep -q '^VPN_MODE=direct' "$f" 2>/dev/null || grep -q "^VPN_MODE='direct'" "$f" 2>/dev/null; then
        direct=$((direct + 1))
      else
        twohop=$((twohop + 1))
      fi
    done
  fi
  log "VPN modes: direct=${direct} twohop=${twohop} (direct clients egress via entry NAT; twohop via exit)"
  echo
  log "End-to-end test: on a connected client device run: curl -4 https://api.ipify.org"
  log "Expected: exit server public IP for twohop clients; entry server public IP for direct clients"
  diag_performance
}

case "$ROLE" in
  exit) diag_exit ;;
  entry) diag_entry ;;
  *)
    die "Usage: sudo bash deploy/diagnose-vpn.sh [--role entry|exit|auto]"
    ;;
esac

if [[ -f "$SCRIPT_DIR/test-connectivity.sh" ]]; then
  echo ""
  bash "$SCRIPT_DIR/test-connectivity.sh" --role "$ROLE" || true
fi
