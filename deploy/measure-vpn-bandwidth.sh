#!/usr/bin/env bash
# Hop-by-hop bandwidth measurement guide for the two-hop WireGuard stack.
#
# Does NOT change routing or firewall. Prints (and optionally runs) safe checks.
#
# Usage:
#   sudo wg-ops measure --role entry|exit|guide
#
# Required architecture remains: device → entry → exit → internet.
# A temporary direct-mode A/B is documented for diagnosis only — not production.
set -eo pipefail

if [[ -z "${WG_DEPLOY_REEXEC:-}" && ! -t 0 ]]; then
  export WG_DEPLOY_REEXEC=1
  GITHUB_RAW_BASE="${GITHUB_RAW_BASE:-https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@v1.0.12}"
  _WG_INSTALLER="$(mktemp /tmp/wg-measure-bw-XXXXXX.sh)"
  curl -fsSL "$GITHUB_RAW_BASE/deploy/measure-vpn-bandwidth.sh" -o "$_WG_INSTALLER"
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
  GITHUB_RAW_BASE="${GITHUB_RAW_BASE:-https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@v1.0.12}"
  curl -fsSL "$GITHUB_RAW_BASE/deploy/repo.conf" -o "$_BOOT/deploy/repo.conf"
  curl -fsSL "$GITHUB_RAW_BASE/deploy/lib/common.sh" -o "$_BOOT/deploy/lib/common.sh"
  SCRIPT_DIR="$_BOOT/deploy"
  # shellcheck source=lib/common.sh
  source "$SCRIPT_DIR/lib/common.sh"
fi
set -u

ROLE="${1:-guide}"
if [[ "$ROLE" == "--role" ]]; then
  ROLE="${2:-guide}"
fi

print_guide() {
  cat <<'EOF'
=== Two-hop bandwidth measurement plan ===

Goal: find which hop limits ~throughput before changing architecture.
Production path must remain: client → entry → exit → internet.

Install iperf3 on both servers:  apt-get install -y iperf3

--- 1) Exit → public internet (on EXIT) ---
  curl -4 -o /dev/null -w 'download_bps=%{speed_download}\n' \
    https://proof.ovh.net/files/100Mb.dat
  # Or: iperf3 -c <public-iperf-host> -P 4
  # Watch CPU: mpstat -P ALL 1 30

--- 2) Entry → exit underlay (NOT through WireGuard) ---
  # On EXIT:   iperf3 -s
  # On ENTRY:  iperf3 -c EXIT_PUBLIC_IP -P 1
  #            iperf3 -c EXIT_PUBLIC_IP -P 4
  #            iperf3 -c EXIT_PUBLIC_IP -u -b 0 -P 4
  # Note retransmits / jitter in iperf3 output

--- 3) Entry → exit through wg-tunnel ---
  # On EXIT:   iperf3 -s -B 10.200.0.1
  # On ENTRY:  iperf3 -c 10.200.0.1 -P 1
  #            iperf3 -c 10.200.0.1 -P 4
  #            iperf3 -c 10.200.0.1 -u -b 0
  # Compare to step 2 — large gap ⇒ MTU/CPU/WG path

--- 4) Full two-hop (from CLIENT device on VPN) ---
  curl -4 https://api.ipify.org    # must show EXIT public IP
  iperf3 -c <public-iperf-host> -P 1
  iperf3 -c <public-iperf-host> -P 4
  iperf3 -c <public-iperf-host> -u -b 0
  # Acceptance is always measured in twohop mode

--- 5) Path quality ---
  # Client → entry:  mtr -rwzc 100 ENTRY_IP
  # Entry → exit:    mtr -rwzc 100 EXIT_IP
  # Via tunnel:      ping -c 50 10.200.0.1   (from entry)
  # MTU probe:       ping -M do -s 1350 -c 3 10.200.0.1

--- 6) Host counters during a speed test ---
  mpstat -P ALL 1 30
  wg show wg-tunnel transfer
  wg show wg-clients transfer
  nstat -az | egrep 'Udp|TcpRetrans|TcpExtListen'
  sysctl net.core.rmem_max net.core.wmem_max net.ipv4.tcp_congestion_control
  # Softnet drops: cat /proc/net/softnet_stat
  # Interface errors: ip -s link show wg-tunnel

--- 7) Optional diagnostic A/B (NOT production) ---
  # On entry, for one test client only:
  #   sudo wg-client set-mode TESTCLIENT direct
  # Measure client throughput, then:
  #   sudo wg-client set-mode TESTCLIENT twohop
  # If direct ≈ twohop ≈ slow → client↔entry path (ISP/DPI).
  # If direct ≫ twohop and step 2/3 are slow → entry↔exit or exit.

Results depend on client ISP, entry/exit VPS, CPU, PPS limits, peering,
distance, loss, and shaping — no fixed Mbps guarantee.

Interpretation:
  Step1 slow          → improve exit plan / provider
  Step2 slow, Step1 ok → entry↔exit peering/location; co-locate or change providers
  Step3 ≪ Step2       → tunnel/MTU/CPU issue on WG path
  Step4 ≪ Step3       → client↔entry path or client MTU/loss
EOF
}

local_checks_entry() {
  require_root
  if [[ -f /etc/wireguard/entry-server.env ]]; then
    # shellcheck disable=SC1091
    source /etc/wireguard/entry-server.env
  fi
  log "=== ENTRY local performance snapshot ==="
  log "TCP congestion: $(sysctl -n net.ipv4.tcp_congestion_control 2>/dev/null || echo unknown)"
  log "rmem_max: $(sysctl -n net.core.rmem_max 2>/dev/null || echo unknown)"
  log "wmem_max: $(sysctl -n net.core.wmem_max 2>/dev/null || echo unknown)"
  log "wg-clients MTU: $(ip -o link show wg-clients 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="mtu") print $(i+1)}' || echo n/a)"
  log "wg-tunnel MTU: $(ip -o link show wg-tunnel 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="mtu") print $(i+1)}' || echo n/a)"
  if systemctl is-enabled wg-mss-clamp.service >/dev/null 2>&1; then
    log "MSS clamp unit: enabled"
  else
    warn "MSS clamp unit not enabled — run: sudo wg-ops tune --role entry"
  fi
  if iptables -t mangle -C FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --clamp-mss-to-pmtu 2>/dev/null; then
    log "MSS clamp rule: present"
  else
    warn "MSS clamp rule missing"
  fi
  echo
  log "Tunnel peer + transfer:"
  wg show wg-tunnel 2>/dev/null || warn "wg-tunnel down"
  echo
  if [[ -n "${WG_EXIT_IP:-}" ]]; then
    log "Ping exit ${WG_EXIT_IP}:"
    ping -c 5 -W 2 "${WG_EXIT_IP}" 2>/dev/null || warn "exit ping failed"
    log "Ping exit tunnel IP 10.200.0.1:"
    ping -c 5 -W 2 10.200.0.1 2>/dev/null || warn "tunnel ping failed"
  fi
  echo
  print_guide
}

local_checks_exit() {
  require_root
  if [[ -f /etc/wireguard/exit-server.env ]]; then
    # shellcheck disable=SC1091
    source /etc/wireguard/exit-server.env
  fi
  log "=== EXIT local performance snapshot ==="
  log "TCP congestion: $(sysctl -n net.ipv4.tcp_congestion_control 2>/dev/null || echo unknown)"
  log "rmem_max: $(sysctl -n net.core.rmem_max 2>/dev/null || echo unknown)"
  log "wmem_max: $(sysctl -n net.core.wmem_max 2>/dev/null || echo unknown)"
  log "wg-tunnel MTU: $(ip -o link show wg-tunnel 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="mtu") print $(i+1)}' || echo n/a)"
  if systemctl is-enabled wg-mss-clamp.service >/dev/null 2>&1; then
    log "MSS clamp unit: enabled"
  else
    warn "MSS clamp unit not enabled — run: sudo wg-ops tune --role exit"
  fi
  printf 'Public IP: '
  curl -4fsS --max-time 5 https://api.ipify.org 2>/dev/null || echo FAIL
  echo
  wg show wg-tunnel 2>/dev/null || warn "wg-tunnel down"
  echo
  print_guide
}

case "$ROLE" in
  guide) print_guide ;;
  entry) local_checks_entry ;;
  exit) local_checks_exit ;;
  *)
    die "Usage: sudo wg-ops measure --role entry|exit|guide"
    ;;
esac
