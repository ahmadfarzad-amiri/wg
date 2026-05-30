#!/usr/bin/env bash
# Test connectivity between exit server, panel server, and WireGuard.
# Usage:
#   bash deploy/test-connectivity.sh --role exit
#   bash deploy/test-connectivity.sh --role panel
#   bash deploy/test-connectivity.sh --role all
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "$SCRIPT_DIR/lib/common.sh"

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
  log "Exit server checks"
  check "wg command" command -v wg
  check "wg-ir interface up" wg show wg-ir
  check "UDP port listening" sh -c 'ss -ulnp | grep -q wg'
  check "IP forwarding" sh -c '[[ "$(sysctl -n net.ipv4.ip_forward)" == "1" ]]'
  check "server public key file" test -f /etc/wireguard/ir_client_public.key
  check "outbound internet" curl -4fsS --max-time 5 https://api.ipify.org
}

test_panel() {
  log "Panel server checks"
  local env_file="/etc/wireguard/panel-server.env"
  if [[ -f "$env_file" ]]; then
    # shellcheck disable=SC1090
    source "$env_file"
  fi

  check "python3" command -v python3
  check "nginx running" systemctl is-active nginx
  check "wg-panel service" systemctl is-active wg-panel
  check "wg-admin-panel service" systemctl is-active wg-admin-panel
  check "client panel HTTP" curl -fsS "http://127.0.0.1:${WG_PANEL_PORT:-8088}/login"
  check "admin panel HTTP" curl -fsS "http://127.0.0.1:${WG_ADMIN_PORT:-8090}/admin/login"
  check "panel.db exists" sh -c 'test -f /etc/wireguard/panel.db || python3 -c "import sys; sys.path.insert(0,\"/opt/wg/client-panel\"); from client_panel.db import db; db().close()"'
  check "admin config exists" test -f /etc/wireguard/admin-panel.json
  check "client-state synced" sh -c 'ls /etc/wireguard/client-state/*.meta >/dev/null 2>&1 || test -d /etc/wireguard/client-state'
  check "wg-client wrapper" test -x /usr/local/bin/wg-client

  if [[ -n "${WG_EXIT_SSH:-}" && -f "${WG_EXIT_SSH_KEY:-/root/.ssh/wg_exit}" ]]; then
    check "SSH to exit server" \
      ssh -o BatchMode=yes -i "${WG_EXIT_SSH_KEY}" "$WG_EXIT_SSH" 'echo ok'
    check "remote wg show" \
      ssh -o BatchMode=yes -i "${WG_EXIT_SSH_KEY}" "$WG_EXIT_SSH" 'wg show wg-ir'
  fi
}

case "$ROLE" in
  exit) test_exit ;;
  panel) test_panel ;;
  all)
    test_exit || true
    test_panel || true
    ;;
  *)
    die "Usage: $0 --role exit|panel|all"
    ;;
esac

echo ""
log "Results: ${pass} passed, ${fail} failed"
[[ "$fail" -eq 0 ]]
