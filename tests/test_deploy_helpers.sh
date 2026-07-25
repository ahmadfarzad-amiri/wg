#!/usr/bin/env bash
# Local (non-root) tests for deploy helpers — no live VPN required.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=../deploy/lib/common.sh
source "$ROOT/deploy/lib/common.sh"

pass=0
fail=0

assert_eq() {
  local name="$1" got="$2" want="$3"
  if [[ "$got" == "$want" ]]; then
    echo "  OK  $name"
    pass=$((pass + 1))
  else
    echo "  FAIL $name (got='$got' want='$want')"
    fail=$((fail + 1))
  fi
}

assert_ok() {
  local name="$1"
  shift
  if ( "$@" ) >/dev/null 2>&1; then
    echo "  OK  $name"
    pass=$((pass + 1))
  else
    echo "  FAIL $name"
    fail=$((fail + 1))
  fi
}

assert_fail() {
  local name="$1"
  shift
  if ( "$@" ) >/dev/null 2>&1; then
    echo "  FAIL $name (expected failure)"
    fail=$((fail + 1))
  else
    echo "  OK  $name"
    pass=$((pass + 1))
  fi
}

echo "=== deploy lib validation ==="
assert_ok "ipv4 valid" wg_is_ipv4 198.51.100.10
assert_fail "ipv4 invalid" wg_is_ipv4 300.1.1.1
assert_ok "cidr valid" wg_is_cidr_v4 10.10.10.0/24
assert_fail "cidr invalid" wg_is_cidr_v4 10.10.10.0/99
assert_ok "port valid" wg_is_port 51820
assert_fail "port invalid" wg_is_port 70000
assert_ok "iface name" wg_is_iface_name wg-tunnel
assert_fail "iface name bad" wg_is_iface_name 'bad iface'

# 32-byte all-zero key in base64 is a valid length/shape for tests.
ZERO_PUB='AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA='
assert_ok "wg pubkey shape" wg_is_wg_pubkey "$ZERO_PUB"
assert_fail "wg pubkey short" wg_is_wg_pubkey shortkey

assert_ok "mtu 1420" wg_validate_mtu 1420 test
assert_fail "mtu too low" wg_validate_mtu 1000 test
assert_fail "mtu too high" wg_validate_mtu 9000 test

assert_eq "server mtu default" "$(WG_SERVER_MTU= wg_server_mtu)" "1420"
assert_eq "tunnel mtu override" "$(WG_TUNNEL_MTU=1400 wg_tunnel_mtu)" "1400"
assert_eq "clients mtu falls back" "$(WG_CLIENTS_MTU= WG_SERVER_MTU=1410 wg_clients_mtu)" "1410"

postup="$(wg_render_entry_tunnel_postup wg-clients wg-tunnel 10.10.10.0/24)"
assert_ok "postup idempotent -C" sh -c "printf '%s' \"$postup\" | grep -q 'iptables -C FORWARD'"
assert_ok "postup has table 100" sh -c "printf '%s' \"$postup\" | grep -q 'lookup 100'"
assert_fail "postup no bare -A only" sh -c "printf '%s' \"$postup\" | grep -Eq 'PostUp = iptables -A FORWARD -i wg-clients -j ACCEPT$'"

echo
echo "=== client PostUp normalize ==="
_tmpdir="$(mktemp -d)"
cat > "$_tmpdir/wg-clients.conf" <<'EOF'
[Interface]
Address = 10.10.10.1/24
ListenPort = 51820
PrivateKey = dummy
PostUp = iptables -A FORWARD -i wg-clients -j ACCEPT; iptables -A FORWARD -o wg-clients -j ACCEPT; ip route replace 10.10.10.0/24 dev wg-clients scope link
PostDown = iptables -D FORWARD -i wg-clients -j ACCEPT; iptables -D FORWARD -o wg-clients -j ACCEPT; ip route del 10.10.10.0/24 dev wg-clients scope link 2>/dev/null || true
EOF
ensure_entry_client_postup_in_conf "$_tmpdir/wg-clients.conf" wg-clients 10.10.10.0/24
assert_fail "strips PostUp entirely" \
  grep -qE '^PostUp[[:space:]]*=' "$_tmpdir/wg-clients.conf"
assert_fail "strips PostDown entirely" \
  grep -qE '^PostDown[[:space:]]*=' "$_tmpdir/wg-clients.conf"
assert_fail "no FORWARD left in clients conf" \
  grep -qE 'iptables .*FORWARD' "$_tmpdir/wg-clients.conf"
assert_ok "keeps Address" \
  grep -q 'Address = 10.10.10.1/24' "$_tmpdir/wg-clients.conf"
rm -rf "$_tmpdir"

echo
echo "=== fresh-install guards ==="
assert_ok "require_fresh_install defined" type require_fresh_install
assert_fail "no upgrade mode in entry installer" \
  grep -q 'WG_INSTALL_MODE' "$ROOT/deploy/install-entry-server.sh"
assert_fail "no upgrade mode in exit installer" \
  grep -q 'WG_INSTALL_MODE' "$ROOT/deploy/install-exit-server.sh"
assert_fail "migrate script removed" \
  test -f "$ROOT/deploy/migrate-vpn-stack.sh"
assert_fail "restore script removed" \
  test -f "$ROOT/deploy/restore.sh"
assert_fail "deprecated panel installer removed" \
  test -f "$ROOT/deploy/install-panel-server.sh"
assert_ok "backup script kept (ops)" \
  test -f "$ROOT/deploy/backup.sh"
assert_ok "uninstall script kept" \
  test -f "$ROOT/deploy/uninstall-server.sh"

assert_ok "wg-ops bash -n" bash -n "$ROOT/deploy/wg-ops"
assert_ok "wg-ops CLI present" test -f "$ROOT/deploy/wg-ops"
assert_ok "wg-ops help" bash "$ROOT/deploy/wg-ops" help
assert_ok "wg-ops maps test" bash -c "bash '$ROOT/deploy/wg-ops' list | grep -q 'test-connectivity.sh\|test,'"
assert_ok "wg-ops help mentions update" bash -c "bash '$ROOT/deploy/wg-ops' help | grep -q update"
assert_ok "wg-ops help mentions uninstall" bash -c "bash '$ROOT/deploy/wg-ops' help | grep -q uninstall"
assert_ok "wg-ops help mentions role detection" bash -c "bash '$ROOT/deploy/wg-ops' help | grep -q 'none'"
assert_fail "wg-ops unknown command" bash "$ROOT/deploy/wg-ops" not-a-real-command
assert_ok "wg-ops list-menu none shows install exit" \
  bash -c "bash '$ROOT/deploy/wg-ops' list-menu none | grep -q 'Install exit server'"
assert_ok "wg-ops list-menu none shows install entry" \
  bash -c "bash '$ROOT/deploy/wg-ops' list-menu none | grep -q 'Install entry server'"
assert_ok "wg-ops list-menu none hides add peer" \
  bash -c "! bash '$ROOT/deploy/wg-ops' list-menu none | grep -q 'Add entry peer'"
assert_ok "wg-ops list-menu entry shows panels" \
  bash -c "bash '$ROOT/deploy/wg-ops' list-menu entry | grep -q 'Update panels only'"
assert_ok "wg-ops list-menu entry hides add peer" \
  bash -c "! bash '$ROOT/deploy/wg-ops' list-menu entry | grep -q 'Add entry peer'"
assert_ok "wg-ops list-menu entry hides install exit" \
  bash -c "! bash '$ROOT/deploy/wg-ops' list-menu entry | grep -q 'Install exit server'"
assert_ok "wg-ops list-menu exit shows add peer" \
  bash -c "bash '$ROOT/deploy/wg-ops' list-menu exit | grep -q 'Add entry peer'"
assert_ok "wg-ops list-menu exit hides panels" \
  bash -c "! bash '$ROOT/deploy/wg-ops' list-menu exit | grep -q 'Update panels only'"
assert_ok "wg-ops list-menu both shows add peer and panels" \
  bash -c "out=\$(bash '$ROOT/deploy/wg-ops' list-menu both); echo \"\$out\" | grep -q 'Add entry peer' && echo \"\$out\" | grep -q 'Update panels only'"
assert_ok "set-admin-password syntax" python3 -m py_compile "$ROOT/deploy/set-admin-password.py"

echo
echo "=== shell syntax ==="
syntax_fail=0
while IFS= read -r f; do
  if bash -n "$f" 2>/tmp/wg-bash-n.err; then
    echo "  OK  bash -n $(basename "$f")"
    pass=$((pass + 1))
  else
    echo "  FAIL bash -n $f"
    cat /tmp/wg-bash-n.err
    fail=$((fail + 1))
    syntax_fail=1
  fi
done < <(find "$ROOT/deploy" -type f -name '*.sh' | sort)

if command -v shellcheck >/dev/null 2>&1; then
  echo
  echo "=== shellcheck (selected) ==="
  for f in \
    "$ROOT/deploy/lib/common.sh" \
    "$ROOT/deploy/validate-config.sh" \
    "$ROOT/deploy/diagnose-vpn.sh" \
    "$ROOT/deploy/tune-vpn-performance.sh"
  do
    if shellcheck -x -e SC1091,SC2034,SC2155,SC2086,SC2016 "$f" 2>/tmp/wg-sc.err; then
      echo "  OK  shellcheck $(basename "$f")"
      pass=$((pass + 1))
    else
      echo "  WARN shellcheck $(basename "$f") (non-fatal)"
      head -20 /tmp/wg-sc.err || true
    fi
  done
else
  echo "  N/A shellcheck not installed"
fi

echo
echo "=== install template checks ==="
assert_ok "entry install has idempotent forward" \
  grep -q 'iptables -C FORWARD -i ${CLIENT_IF} -o ${TUNNEL_IF}' "$ROOT/deploy/install-entry-server.sh"
assert_fail "entry clients no redundant route PostUp" \
  grep -q 'PostUp = ip route replace ${CLIENT_CIDR} dev ${CLIENT_IF}' "$ROOT/deploy/install-entry-server.sh"
assert_fail "entry clients no broad FORWARD" \
  grep -q 'FORWARD -i ${CLIENT_IF} -j ACCEPT' "$ROOT/deploy/install-entry-server.sh"
assert_ok "exit install idempotent NAT" \
  grep -q 'iptables -t nat -C POSTROUTING' "$ROOT/deploy/install-exit-server.sh"
assert_ok "entry uses require_fresh_install" \
  grep -q 'require_fresh_install' "$ROOT/deploy/install-entry-server.sh"
assert_ok "exit uses require_fresh_install" \
  grep -q 'require_fresh_install' "$ROOT/deploy/install-exit-server.sh"

echo
echo "=== hardcoded IP check ==="
if bash "$ROOT/tests/check_no_hardcoded_ips.sh"; then
  echo "  OK  no suspicious hardcoded IPs"
  pass=$((pass + 1))
else
  echo "  FAIL hardcoded IP check"
  fail=$((fail + 1))
fi

echo
echo "=== legacy keyword scan (deploy + docs) ==="
legacy_hits="$(
  grep -RInE \
    --exclude-dir=.git \
    'migrate-vpn-stack|WG_INSTALL_MODE|install-panel-server|migrate-to-opt-wg|restore\.sh|pre-migrate|preserve_tunnel_keys|require_fresh_or_upgrade' \
    "$ROOT/deploy" "$ROOT/docs" "$ROOT/README.md" 2>/dev/null || true
)"
if [[ -n "$legacy_hits" ]]; then
  echo "$legacy_hits"
  echo "  FAIL legacy references still present"
  fail=$((fail + 1))
else
  echo "  OK  no legacy migrate/upgrade/restore references"
  pass=$((pass + 1))
fi

echo
echo "Results: ${pass} passed, ${fail} failed"
[[ "$fail" -eq 0 && "$syntax_fail" -eq 0 ]]
