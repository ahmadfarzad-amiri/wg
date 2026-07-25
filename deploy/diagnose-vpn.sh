#!/usr/bin/env bash
# Deep VPN diagnostics for the two-hop stack.
# Read-only: does not modify routing, firewall, or sysctl.
#
# Usage: sudo wg-ops diagnose [--role entry|exit|auto]
#
# Status legend:
#   [HEALTHY]  expected state
#   [WARNING]  degraded or suboptimal
#   [FAILED]   broken / must fix
#   [N/A]      not applicable on this role/host
set -eo pipefail

if [[ -z "${WG_DEPLOY_REEXEC:-}" && ! -t 0 ]]; then
  export WG_DEPLOY_REEXEC=1
  GITHUB_RAW_BASE="${GITHUB_RAW_BASE:-https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@v1.0.14}"
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
  GITHUB_RAW_BASE="${GITHUB_RAW_BASE:-https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@v1.0.14}"
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
  [[ "$ROLE" != "unknown" ]] || die "Could not detect role — use: sudo wg-ops diagnose --role entry|exit"
fi

HEALTHY=0
WARNING=0
FAILED=0

status() {
  local level="$1"
  local msg="$2"
  case "$level" in
    HEALTHY) printf '[HEALTHY] %s\n' "$msg"; HEALTHY=$((HEALTHY + 1)) ;;
    WARNING) printf '[WARNING] %s\n' "$msg"; WARNING=$((WARNING + 1)) ;;
    FAILED)  printf '[FAILED]  %s\n' "$msg"; FAILED=$((FAILED + 1)) ;;
    N/A)     printf '[N/A]     %s\n' "$msg" ;;
    *)       printf '[INFO]    %s\n' "$msg" ;;
  esac
}

check_bool() {
  local name="$1"
  shift
  if "$@" >/dev/null 2>&1; then
    status HEALTHY "$name"
  else
    status FAILED "$name"
  fi
}

iface_mtu() {
  ip -o link show "$1" 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="mtu") print $(i+1)}'
}

iface_stats() {
  local iface="$1"
  if [[ -r "/sys/class/net/${iface}/statistics/rx_errors" ]]; then
    printf 'rx_err=%s tx_err=%s rx_drop=%s tx_drop=%s' \
      "$(cat "/sys/class/net/${iface}/statistics/rx_errors")" \
      "$(cat "/sys/class/net/${iface}/statistics/tx_errors")" \
      "$(cat "/sys/class/net/${iface}/statistics/rx_dropped")" \
      "$(cat "/sys/class/net/${iface}/statistics/tx_dropped")"
  else
    printf 'n/a'
  fi
}

diag_host_perf() {
  status INFO "=== Host / kernel ==="
  local cc qdisc rmem steal softirq
  cc="$(sysctl -n net.ipv4.tcp_congestion_control 2>/dev/null || echo unknown)"
  qdisc="$(sysctl -n net.core.default_qdisc 2>/dev/null || echo unknown)"
  rmem="$(sysctl -n net.core.rmem_max 2>/dev/null || echo 0)"
  if [[ "$cc" == "bbr" ]]; then
    status HEALTHY "TCP congestion=${cc} qdisc=${qdisc}"
  else
    status WARNING "TCP congestion=${cc} (expected bbr when WG_ENABLE_BBR=1)"
  fi
  if [[ "${rmem:-0}" -ge 16777216 ]]; then
    status HEALTHY "UDP/TCP rmem_max=${rmem}"
  else
    status WARNING "rmem_max=${rmem} is low — run tune-vpn-performance.sh"
  fi
  if [[ -f /etc/sysctl.d/99-wg-performance.conf ]]; then
    status HEALTHY "Performance sysctl file present"
  else
    status WARNING "Missing /etc/sysctl.d/99-wg-performance.conf"
  fi
  if systemctl is-enabled wg-mss-clamp.service >/dev/null 2>&1; then
    status HEALTHY "wg-mss-clamp.service enabled"
  else
    status WARNING "wg-mss-clamp.service not enabled"
  fi
  if iptables -t mangle -C FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --clamp-mss-to-pmtu 2>/dev/null; then
    local mss_count
    mss_count="$(iptables-save -t mangle 2>/dev/null | grep -c 'TCPMSS.*clamp' || true)"
    if [[ "${mss_count:-0}" -gt 1 ]]; then
      status WARNING "Duplicate MSS clamp rules (${mss_count}) — run: sudo wg-ops fix-routing --role ${ROLE}"
    else
      status HEALTHY "TCP MSS clamp rule present"
    fi
  else
    status FAILED "TCP MSS clamp rule missing"
  fi
  if [[ -e /proc/sys/net/netfilter/nf_conntrack_count ]]; then
    local used max
    used="$(cat /proc/sys/net/netfilter/nf_conntrack_count)"
    max="$(cat /proc/sys/net/netfilter/nf_conntrack_max)"
    status INFO "Conntrack ${used}/${max}"
    if [[ "$max" -gt 0 && $((used * 100 / max)) -gt 80 ]]; then
      status WARNING "Conntrack usage >80%"
    else
      status HEALTHY "Conntrack usage OK"
    fi
  else
    status N/A "Conntrack not loaded"
  fi
  steal="$(awk '/cpu /{s=$9; t=$2+$3+$4+$5+$6+$7+$8+$9+$10+$11; if(t>0) printf "%.1f", 100*s/t; else print 0}' /proc/stat 2>/dev/null || echo n/a)"
  status INFO "CPU steal≈${steal}% (cumulative since boot — interpret carefully)"
  if command -v mpstat >/dev/null 2>&1; then
    softirq="$(mpstat 1 1 2>/dev/null | awk '/Average:.*all/{print $(NF-1)}' || true)"
    status INFO "SoftIRQ sample (mpstat %irq/%soft): ${softirq:-n/a}"
  else
    status N/A "mpstat not installed (apt install sysstat)"
  fi
  echo
}

diag_wg_ifaces() {
  status INFO "=== WireGuard interfaces ==="
  local iface
  for iface in "$@"; do
    if ! ip link show "$iface" >/dev/null 2>&1; then
      status FAILED "${iface} missing"
      continue
    fi
    local mtu
    mtu="$(iface_mtu "$iface")"
    status HEALTHY "${iface} up MTU=${mtu} $(iface_stats "$iface")"
    wg show "$iface" 2>/dev/null | head -20 || status FAILED "wg show ${iface} failed"
    echo
    status INFO "${iface} transfer:"
    wg show "$iface" transfer 2>/dev/null || true
    status INFO "${iface} latest-handshakes:"
    wg show "$iface" latest-handshakes 2>/dev/null || true
    echo
  done
}

diag_exit() {
  local client_cidr="${WG_CLIENT_CIDR:-10.10.10.0/24}"
  if [[ -f /etc/wireguard/exit-server.env ]]; then
    # shellcheck disable=SC1091
    source /etc/wireguard/exit-server.env
    client_cidr="${WG_CLIENT_CIDR:-10.10.10.0/24}"
  fi

  status INFO "=== EXIT diagnostics ==="
  local pub
  pub="$(curl -4fsS --max-time 5 https://api.ipify.org 2>/dev/null || true)"
  if [[ -n "$pub" ]]; then
    status HEALTHY "Public egress IP=${pub}"
  else
    status FAILED "Cannot reach api.ipify.org from exit"
  fi

  diag_wg_ifaces wg-tunnel

  if wg_exit_route_to_client_ok "10.10.10.2"; then
    status HEALTHY "Route 10.10.10.2 → wg-tunnel"
  else
    status FAILED "Route 10.10.10.2 not via wg-tunnel — fix-vpn-routing.sh --role exit"
  fi
  ip route get 10.10.10.2 2>/dev/null || true
  ip route get 10.200.0.2 2>/dev/null || true

  if ping -c 2 -W 2 10.200.0.2 >/dev/null 2>&1; then
    status HEALTHY "Ping entry tunnel IP 10.200.0.2"
  else
    status WARNING "Cannot ping 10.200.0.2 (peer may be down)"
  fi

  if iptables -t nat -S POSTROUTING 2>/dev/null | grep -qE -- "-s ${client_cidr}.*MASQUERADE"; then
    local nat_count
    nat_count="$(iptables-save -t nat 2>/dev/null | grep -cE -- "-A POSTROUTING -s ${client_cidr}.*MASQUERADE" || true)"
    if [[ "${nat_count:-0}" -gt 1 ]]; then
      status WARNING "Duplicate MASQUERADE rules (${nat_count}) — run: sudo wg-ops fix-routing --role exit"
    else
      status HEALTHY "NAT MASQUERADE for ${client_cidr}"
    fi
  else
    status FAILED "Missing MASQUERADE for ${client_cidr}"
  fi

  check_bool "IP forwarding on" sh -c '[ "$(sysctl -n net.ipv4.ip_forward)" = "1" ]'
  if systemctl is-active --quiet "wg-quick@wg-tunnel" 2>/dev/null; then
    status HEALTHY "wg-quick@wg-tunnel active"
  else
    status WARNING "wg-quick@wg-tunnel not active via systemd"
  fi
  diag_host_perf
}

diag_entry() {
  local client_cidr="${WG_CLIENT_CIDR:-10.10.10.0/24}"
  if [[ -f /etc/wireguard/entry-server.env ]]; then
    # shellcheck disable=SC1091
    source /etc/wireguard/entry-server.env
    client_cidr="${WG_CLIENT_CIDR:-10.10.10.0/24}"
  fi

  status INFO "=== ENTRY diagnostics ==="
  if [[ -f /etc/wireguard/wg-endpoint ]]; then
    status HEALTHY "Client endpoint=$(cat /etc/wireguard/wg-endpoint)"
  else
    status FAILED "Missing /etc/wireguard/wg-endpoint"
  fi

  diag_wg_ifaces wg-clients wg-tunnel

  if wg_entry_client_subnet_route_ok "10.10.10.2"; then
    status HEALTHY "Route 10.10.10.2 → wg-clients"
  else
    status FAILED "Route 10.10.10.2 not via wg-clients"
  fi
  if ip rule show | grep -q 'lookup 100'; then
    status HEALTHY "Policy rule lookup 100 present"
  else
    status FAILED "Missing policy rule lookup 100"
  fi
  if ip route show table 100 2>/dev/null | grep -q 'default'; then
    status HEALTHY "Table 100 default via wg-tunnel"
  else
    status FAILED "Table 100 missing default route"
  fi
  ip rule show | grep -E '100|10.10.10' || true
  ip route show table 100 2>/dev/null || true

  local rp_c rp_t
  rp_c="$(sysctl -n net.ipv4.conf.wg-clients.rp_filter 2>/dev/null || echo missing)"
  rp_t="$(sysctl -n net.ipv4.conf.wg-tunnel.rp_filter 2>/dev/null || echo missing)"
  if [[ "$rp_c" == "0" && "$rp_t" == "0" ]]; then
    status HEALTHY "rp_filter=0 on wg-clients and wg-tunnel"
  else
    status FAILED "rp_filter wg-clients=${rp_c} wg-tunnel=${rp_t} (need 0)"
  fi

  if tunnel_handshake_recent 180; then
    status HEALTHY "Tunnel handshake to exit ≤180s"
  else
    status FAILED "Tunnel handshake stale/missing — check exit peer + UDP ${WG_EXIT_TUNNEL_PORT:-51821}"
  fi
  if ping -c 2 -W 2 10.200.0.1 >/dev/null 2>&1; then
    status HEALTHY "Ping exit tunnel IP 10.200.0.1"
    local rtt
    rtt="$(ping -c 5 -W 2 10.200.0.1 2>/dev/null | awk -F'/' '/rtt|round-trip/{print $5}')"
    status INFO "Entry→exit tunnel RTT avg=${rtt:-n/a} ms"
  else
    status WARNING "Cannot ping 10.200.0.1"
  fi

  if iptables -C FORWARD -i wg-clients -o wg-tunnel -j ACCEPT 2>/dev/null; then
    status HEALTHY "FORWARD client→tunnel"
  else
    status FAILED "Missing FORWARD client→tunnel"
  fi
  if iptables -C FORWARD -i wg-tunnel -o wg-clients -j ACCEPT 2>/dev/null; then
    status HEALTHY "FORWARD tunnel→client"
  else
    status FAILED "Missing FORWARD tunnel→client"
  fi
  if iptables -C FORWARD -i wg-clients -j ACCEPT 2>/dev/null; then
    status WARNING "Broad FORWARD -i wg-clients ACCEPT still present — run fix-vpn-routing.sh"
  else
    status HEALTHY "No broad wg-clients FORWARD ACCEPT"
  fi
  local def_if
  def_if="$(default_route_iface)"
  if [[ -n "$def_if" ]] && iptables -C FORWARD -i wg-clients -o "$def_if" -j DROP 2>/dev/null; then
    status HEALTHY "Anti-leak DROP client→${def_if}"
  else
    status WARNING "Anti-leak DROP missing (set WG_ENTRY_ANTILEAK=1 and run fix-vpn-routing.sh)"
  fi
  if iptables -t nat -S POSTROUTING 2>/dev/null | grep -qE -- "-s ${client_cidr}.*MASQUERADE"; then
    status WARNING "Subnet MASQUERADE on entry for ${client_cidr} — double-NAT risk"
  else
    status HEALTHY "No subnet MASQUERADE on entry (NAT belongs on exit)"
  fi

  if iptables -L DOCKER-USER -n >/dev/null 2>&1; then
    status WARNING "Docker present — prefer bare metal for VPN dataplane"
    if iptables -C DOCKER-USER -i wg-clients -o wg-tunnel -j ACCEPT 2>/dev/null; then
      status HEALTHY "DOCKER-USER bypass present"
    else
      status FAILED "DOCKER-USER bypass missing"
    fi
  else
    status HEALTHY "No Docker DOCKER-USER chain"
  fi

  if [[ -f /etc/wireguard/wg-clients.conf ]] \
    && grep -qE 'iptables -A FORWARD -i wg-clients -j ACCEPT' /etc/wireguard/wg-clients.conf; then
    status WARNING "wg-clients.conf has unsupported broad PostUp FORWARD — reinstall or fix PostUp"
  fi

  local direct=0 twohop=0
  if [[ -d /etc/wireguard/client-state ]]; then
    local f
    for f in /etc/wireguard/client-state/*.meta; do
      [[ -f "$f" ]] || continue
      if grep -qE "^VPN_MODE=('direct'|direct)" "$f" 2>/dev/null; then
        direct=$((direct + 1))
      else
        twohop=$((twohop + 1))
      fi
    done
  fi
  status INFO "VPN modes: twohop=${twohop} direct=${direct} (direct is diagnostic-only)"
  if [[ "$direct" -gt 0 ]]; then
    status WARNING "${direct} client(s) in direct mode — production should use twohop"
  fi

  check_bool "IP forwarding on" sh -c '[ "$(sysctl -n net.ipv4.ip_forward)" = "1" ]'
  if systemctl is-active --quiet wg-panel 2>/dev/null; then
    status HEALTHY "wg-panel active"
  else
    status WARNING "wg-panel not active"
  fi
  if systemctl is-active --quiet wg-admin-panel 2>/dev/null; then
    status HEALTHY "wg-admin-panel active"
  else
    status WARNING "wg-admin-panel not active"
  fi

  local sample
  sample="$(find /etc/wireguard/clients -name '*.conf' 2>/dev/null | head -1 || true)"
  if [[ -n "$sample" ]]; then
    status INFO "Sample client MTU: $(grep -E '^MTU' "$sample" 2>/dev/null || echo 'not set')"
  fi
  status INFO "Configured MTU: server=${WG_SERVER_MTU:-1420} clients_if=${WG_CLIENTS_MTU:-} tunnel=${WG_TUNNEL_MTU:-} twohop_client=${WG_CLIENT_MTU_TWOHOP:-1380}"

  status INFO "From a twohop client: curl -4 https://api.ipify.org  # must equal EXIT public IP"
  diag_host_perf
}

case "$ROLE" in
  exit) diag_exit ;;
  entry) diag_entry ;;
  *) die "Usage: sudo wg-ops diagnose [--role entry|exit|auto]" ;;
esac

echo
status INFO "Summary: healthy=${HEALTHY} warning=${WARNING} failed=${FAILED}"
if [[ "$FAILED" -gt 0 ]]; then
  status INFO "Fix: sudo wg-ops fix-routing --role ${ROLE}"
  status INFO "Then: sudo wg-ops diagnose --role ${ROLE}"
  exit 1
fi
exit 0
