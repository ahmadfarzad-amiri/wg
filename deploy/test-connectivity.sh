#!/usr/bin/env bash
# Test connectivity for entry/exit VPN infrastructure.
# Usage: bash deploy/test-connectivity.sh --role exit|entry|all
set -eo pipefail

log() { printf '[wg-deploy] %s\n' "$*"; }
warn() { printf '[wg-deploy] WARN: %s\n' "$*" >&2; }
die() { printf '[wg-deploy] ERROR: %s\n' "$*" >&2; exit 1; }

ROLE="${1:-}"
if [[ "$ROLE" == "--role" ]]; then
  ROLE="${2:-all}"
fi
ROLE="${ROLE:-all}"

pass=0
fail=0

check() {
  local name="$1"
  shift
  printf '  %-42s ' "$name"
  if "$@" >/dev/null 2>&1; then
    echo "OK"
    pass=$((pass + 1))
  else
    echo "FAIL"
    fail=$((fail + 1))
  fi
}

tunnel_handshake_recent() {
  local max_age="${1:-180}"
  local tunnel_if="${2:-wg-tunnel}"
  local now hs age
  now="$(date +%s)"
  hs="$(wg show "$tunnel_if" latest-handshakes 2>/dev/null \
    | awk 'NF >= 2 { t = $NF + 0; if (t > max) max = t } END { print max + 0 }')"
  hs="${hs:-0}"
  age=$((now - hs))
  [[ "$hs" -gt 0 && "$age" -le "$max_age" ]]
}

test_exit() {
  local tunnel_port="51821"
  local client_cidr="10.10.10.0/24"
  if [[ -f /etc/wireguard/exit-server.env ]]; then
    # shellcheck disable=SC1090
    source /etc/wireguard/exit-server.env
    tunnel_port="${WG_TUNNEL_PORT:-51821}"
    client_cidr="${WG_CLIENT_CIDR:-10.10.10.0/24}"
  fi

  log "Exit server checks"
  check "wg command" command -v wg
  check "wg-tunnel interface up" wg show wg-tunnel
  check "tunnel UDP listening" sh -c "ss -ulnp 2>/dev/null | grep -q ':${tunnel_port} '"
  check "IP forwarding enabled" sh -c '[ "$(sysctl -n net.ipv4.ip_forward 2>/dev/null)" = "1" ]'
  check "NAT masquerade for clients" sh -c "iptables -t nat -C POSTROUTING -s ${client_cidr} -j MASQUERADE 2>/dev/null || iptables -t nat -L POSTROUTING -n -v | grep -q MASQUERADE"
  check "tunnel server pubkey saved" test -f /etc/wireguard/tunnel-server.pub
  check "outbound internet" curl -4fsS --max-time 5 https://api.ipify.org
  if [[ -f /etc/wireguard/tunnel-entry.pub ]]; then
    check "entry peer in config" grep -q 'BEGIN ENTRY TUNNEL PEER' /etc/wireguard/wg-tunnel.conf
    check "entry server peer configured" wg show wg-tunnel peers
    check "client subnet routed via wg-tunnel" sh -c 'ip route get 10.10.10.2 2>/dev/null | grep -q "dev wg-tunnel"'
  else
    warn "Entry server peer not added yet — run add-entry-peer.sh on this host"
  fi
}

test_entry() {
  log "Entry server checks"
  local env_file="/etc/wireguard/entry-server.env"
  if [[ -f "$env_file" ]]; then
    # shellcheck disable=SC1090
    source "$env_file"
  fi

  check "wg-clients up" wg show wg-clients
  check "wg-tunnel up (to exit)" wg show wg-tunnel
  check "client endpoint file" test -f /etc/wireguard/wg-endpoint
  check "policy route table 100" sh -c "ip rule show | grep -q 'lookup 100'"
  check "tunnel→client forward rule" sh -c "iptables -C FORWARD -i wg-tunnel -o wg-clients -j ACCEPT"
  check "client→tunnel forward rule" sh -c "iptables -C FORWARD -i wg-clients -o wg-tunnel -j ACCEPT"
  check "wg tunnel rp_filter off" sh -c '[ "$(sysctl -n net.ipv4.conf.wg-tunnel.rp_filter 2>/dev/null)" = "0" ]'
  check "wg-panel service" systemctl is-active wg-panel
  check "wg-admin-panel service" systemctl is-active wg-admin-panel
  if [[ -f /etc/nginx/sites-enabled/wg-panels.conf ]]; then
    check "nginx running" systemctl is-active nginx
    check "client panel HTTP" curl -fsS "http://127.0.0.1/login" -H "Host: localhost"
    check "admin panel HTTP" curl -fsS "http://127.0.0.1/admin/login" -H "Host: localhost"
    if [[ "${WG_HTTPS:-0}" == "1" ]]; then
      check "client panel HTTPS" curl -fsSk "https://127.0.0.1/login" -H "Host: localhost"
    fi
  else
    check "client panel HTTP" curl -fsS "http://127.0.0.1:${WG_PANEL_PORT:-8088}/login"
    check "admin panel HTTP" curl -fsS "http://127.0.0.1:${WG_ADMIN_PORT:-8090}/admin/login"
  fi
  check "admin config" test -f /etc/wireguard/admin-panel.json
  check "wg-client installed" command -v wg-client
  printf '  %-42s ' "tunnel handshake to exit (<=180s)"
  if tunnel_handshake_recent 180; then
    echo "OK"
    pass=$((pass + 1))
  else
    echo "FAIL"
    fail=$((fail + 1))
  fi
  check "client panel health" curl -fsS "http://127.0.0.1:${WG_PANEL_PORT:-8088}/health"
  check "admin panel health" curl -fsS "http://127.0.0.1:${WG_ADMIN_PORT:-8090}/admin/health"
}

case "$ROLE" in
  exit) test_exit ;;
  entry) test_entry ;;
  panel) test_entry ;;
  all)
    test_exit || true
    test_entry || true
    ;;
  *)
    die "Usage: $0 --role exit|entry|all"
    ;;
esac

echo ""
log "Results: ${pass} passed, ${fail} failed"
[[ "$fail" -eq 0 ]]
