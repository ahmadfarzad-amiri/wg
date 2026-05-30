#!/usr/bin/env bash
# Test connectivity for entry/exit VPN infrastructure.
# Usage: bash deploy/test-connectivity.sh --role exit|entry|all
#
# Standalone — no repo clone required:
#   curl -fsSL https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@main/deploy/test-connectivity.sh -o /tmp/test-connectivity.sh
#   sudo bash /tmp/test-connectivity.sh --role exit
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

test_exit() {
  local tunnel_port="51821"
  if [[ -f /etc/wireguard/exit-server.env ]]; then
    # shellcheck disable=SC1090
    source /etc/wireguard/exit-server.env
    tunnel_port="${WG_TUNNEL_PORT:-51821}"
  fi

  log "Exit server checks"
  check "wg command" command -v wg
  check "wg-tunnel interface up" wg show wg-tunnel
  check "tunnel UDP listening" sh -c "ss -ulnp 2>/dev/null | grep -q ':${tunnel_port} '"
  check "IP forwarding enabled" sh -c '[ "$(sysctl -n net.ipv4.ip_forward 2>/dev/null)" = "1" ]'
  check "tunnel server pubkey saved" test -f /etc/wireguard/tunnel-server.pub
  check "outbound internet" curl -4fsS --max-time 5 https://api.ipify.org
  if [[ -f /etc/wireguard/tunnel-entry.pub ]]; then
    check "entry server peer configured" wg show wg-tunnel peers
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
  check "wg-panel service" systemctl is-active wg-panel
  check "wg-admin-panel service" systemctl is-active wg-admin-panel
  if [[ -f /etc/nginx/sites-enabled/wg-panels.conf ]]; then
    check "nginx running" systemctl is-active nginx
    check "client panel HTTP" curl -fsS "http://127.0.0.1/login" -H "Host: localhost"
    check "admin panel HTTP" curl -fsS "http://127.0.0.1/admin/login" -H "Host: localhost"
  else
    check "client panel HTTP" curl -fsS "http://127.0.0.1:${WG_PANEL_PORT:-8088}/login"
    check "admin panel HTTP" curl -fsS "http://127.0.0.1:${WG_ADMIN_PORT:-8090}/admin/login"
  fi
  check "admin config" test -f /etc/wireguard/admin-panel.json
  check "wg-client installed" command -v wg-client
  check "tunnel handshake to exit" sh -c 'wg show wg-tunnel latest-handshakes | grep -qv "^$"'
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
