#!/usr/bin/env bash
# Local (non-root) tests for deploy helpers — no live VPN required.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# Offline-friendly: pin version before sourcing deploy helpers (avoids GitHub network).
export WG_VERSION="${WG_VERSION:-0.0.0-test}"
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

echo
echo "=== public endpoint host ==="
assert_ok "public ipv4 endpoint host" wg_is_public_endpoint_host 203.0.113.10
assert_ok "hostname endpoint host" wg_is_public_endpoint_host vpn.example.com
assert_fail "rfc1918 endpoint host" wg_is_public_endpoint_host 10.0.0.1
assert_fail "loopback endpoint host" wg_is_public_endpoint_host 127.0.0.1
assert_fail "cgnat endpoint host" wg_is_public_endpoint_host 100.64.0.1
assert_fail "localhost endpoint host" wg_is_public_endpoint_host localhost

assert_eq "server mtu default" "$(WG_SERVER_MTU= wg_server_mtu)" "1420"
assert_eq "tunnel mtu override" "$(WG_TUNNEL_MTU=1400 wg_tunnel_mtu)" "1400"
assert_eq "clients mtu falls back" "$(WG_CLIENTS_MTU= WG_SERVER_MTU=1410 wg_clients_mtu)" "1410"

# Runtime entry-server.env uses WG_ENDPOINT / WG_EXIT_IP, not install-only names.
_tmpdir="$(mktemp -d)"
cat > "$_tmpdir/wg-endpoint" <<'EOF'
203.0.113.10:51820
EOF
cat > "$_tmpdir/wg-tunnel.conf" <<EOF
[Interface]
PrivateKey = dummy
[Peer]
PublicKey = ${ZERO_PUB}
Endpoint = 203.0.113.20:51821
AllowedIPs = 0.0.0.0/0
EOF
# Resolve the same way validate does (without requiring live wg tools for IP parse).
_entry="$(WG_ENDPOINT=203.0.113.10:51820 bash -c 'ep="${WG_ENDPOINT}"; echo "${ep%%:*}"')"
_exit="$(WG_EXIT_IP=203.0.113.20 bash -c 'echo "${WG_EXIT_PUBLIC_IP:-${EXIT_IP:-${WG_EXIT_IP:-}}}"')"
_pub="$(awk '/^\[Peer\]/{p=1;next} p && /^PublicKey[[:space:]]*=/{sub(/^[^=]*=[[:space:]]*/,""); print; exit}' "$_tmpdir/wg-tunnel.conf")"
assert_eq "runtime entry IP from WG_ENDPOINT" "$_entry" "203.0.113.10"
assert_eq "runtime exit IP from WG_EXIT_IP" "$_exit" "203.0.113.20"
assert_eq "runtime exit pub from tunnel conf" "$_pub" "$ZERO_PUB"
assert_ok "validate helper reads runtime names" \
  grep -q 'WG_ENDPOINT:-' "$ROOT/deploy/lib/common.sh"
assert_ok "validate helper reads WG_EXIT_IP" \
  grep -q 'WG_EXIT_IP' "$ROOT/deploy/lib/common.sh"
assert_ok "standalone helper defined" type wg_entry_is_standalone
assert_ok "has_exit helper defined" type wg_entry_has_exit
assert_eq "default mode twohop with exit" \
  "$(WG_ENTRY_MODE=twohop WG_EXIT_PUBLIC_IP=203.0.113.10 WG_EXIT_TUNNEL_PUB="$ZERO_PUB" wg_entry_default_vpn_mode)" "twohop"
assert_eq "default mode direct standalone" \
  "$(WG_ENTRY_MODE=standalone wg_entry_default_vpn_mode)" "direct"
assert_eq "default mode direct when twohop label but no exit" \
  "$(WG_ENTRY_MODE=twohop wg_entry_default_vpn_mode)" "direct"
assert_ok "standalone when mode set" \
  bash -c 'source "'"$ROOT"'/deploy/lib/common.sh"; WG_ENTRY_MODE=standalone; wg_entry_is_standalone'
assert_ok "standalone when twohop label but no exit" \
  bash -c 'source "'"$ROOT"'/deploy/lib/common.sh"; WG_ENTRY_MODE=twohop; wg_entry_is_standalone'
assert_fail "not standalone when twohop with exit" \
  bash -c 'source "'"$ROOT"'/deploy/lib/common.sh"; WG_ENTRY_MODE=twohop; WG_EXIT_PUBLIC_IP=203.0.113.10; WG_EXIT_TUNNEL_PUB=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=; wg_entry_is_standalone'
assert_ok "test-connectivity sources common.sh" \
  grep -q 'source .*lib/common.sh' "$ROOT/deploy/test-connectivity.sh"
assert_ok "entry install mentions standalone" \
  grep -q 'standalone' "$ROOT/deploy/install-entry-server.sh"
assert_ok "change-exit can attach from scratch" \
  grep -q 'ATTACHING_FROM_STANDALONE' "$ROOT/deploy/change-exit-server.sh"
rm -rf "$_tmpdir"

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
echo "=== rp_filter systemd hooks ==="
_tmpdir="$(mktemp -d)"
# Render drop-in content the same way as wg_install_rp_filter_systemd_hooks (no root needed).
cat > "$_tmpdir/rpfilter.conf" <<'EOF'
[Service]
ExecStartPost=-/bin/sh -c 'echo 0 > /proc/sys/net/ipv4/conf/wg-clients/rp_filter 2>/dev/null || true'
ExecStartPost=-/bin/sh -c 'echo 0 > /proc/sys/net/ipv4/conf/wg-tunnel/rp_filter 2>/dev/null || true'
EOF
assert_ok "rpfilter drop-in ignores failures (- prefix)" \
  grep -q 'ExecStartPost=-/bin/sh' "$_tmpdir/rpfilter.conf"
assert_fail "rpfilter drop-in no brittle && -e" \
  grep -qE '\[ -e .*rp_filter \].*&&' "$_tmpdir/rpfilter.conf"
assert_ok "common.sh installs tolerant ExecStartPost" \
  grep -q "ExecStartPost=-/bin/sh -c 'echo 0 > /proc/sys/net/ipv4/conf/wg-clients/rp_filter" \
    "$ROOT/deploy/lib/common.sh"
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
assert_ok "wg-ops list-menu shows version" \
  bash -c "WG_VERSION=0.0.0-test bash '$ROOT/deploy/wg-ops' list-menu none | grep -q 'Version: 0.0.0-test'"
assert_ok "server env WG_VERSION does not pin menu release channel" \
  bash -c '
    tmp="$(mktemp -d)"
    trap "rm -rf \"$tmp\"" EXIT
    printf "WG_VERSION=1.0.23\nWG_ENTRY_MODE=standalone\n" > "$tmp/entry-server.env"
    out="$(
      WG_VERSION=1.0.25 \
      WG_ENTRY_ENV_FILE="$tmp/entry-server.env" \
      WG_OPS_ROLE_OVERRIDE=entry \
      bash "'"$ROOT"'/deploy/wg-ops" list-menu entry
    )"
    echo "$out" | grep -q "Version: 1.0.25"
  '
assert_ok "refresh_release_channel keeps RAW_BASE after sourcing common.sh" \
  bash -c '
    set -euo pipefail
    # shellcheck source=/dev/null
    source <(
      sed -n "/^wg_strip_v()/,/^require_root()/p" "'"$ROOT"'/deploy/wg-ops" | sed "\$d"
    )
    resolve_ops_version
    # shellcheck source=/dev/null
    source "'"$ROOT"'/deploy/lib/common.sh"
    refresh_release_channel
    sync_ops_raw_base
    test -n "${RAW_BASE:-}"
    cdn_resolved_version >/dev/null || true
    printf "%s" "${RAW_BASE}" | grep -q .
  '
assert_ok "WG_VERSION env drives CDN ref without hardcode" \
  bash -c '
    unset GITHUB_CDN_REF GITHUB_RAW_BASE
    WG_VERSION=9.9.9
    # shellcheck source=/dev/null
    source "'"$ROOT"'/deploy/lib/common.sh"
    test "$WG_VERSION" = "9.9.9"
    test "$GITHUB_CDN_REF" = "v9.9.9"
    [[ "$GITHUB_RAW_BASE" == *"/wg@v9.9.9" ]]
    grep -q "resolve_version" "'"$ROOT"'/client-panel/client_panel/config/settings.py"
    grep -q "resolve_version" "'"$ROOT"'/admin-panel/admin_panel/config/settings.py"
    ! grep -qE "VERSION = .*[0-9]+\.[0-9]+\.[0-9]+" "'"$ROOT"'/client-panel/client_panel/config/settings.py"
    ! grep -qE "VERSION = .*[0-9]+\.[0-9]+\.[0-9]+" "'"$ROOT"'/admin-panel/admin_panel/config/settings.py"
  '
assert_ok "no hardcoded semver pin in repo.conf" \
  bash -c "! grep -qE '[0-9]+\.[0-9]+\.[0-9]+' '$ROOT/deploy/repo.conf'"
assert_ok "wg-ops list-menu none shows install exit" \
  bash -c "bash '$ROOT/deploy/wg-ops' list-menu none | grep -q 'Install exit server'"
assert_ok "wg-ops list-menu none shows install entry" \
  bash -c "bash '$ROOT/deploy/wg-ops' list-menu none | grep -q 'Install entry server'"
assert_ok "wg-ops list-menu none hides add peer" \
  bash -c "! bash '$ROOT/deploy/wg-ops' list-menu none | grep -q 'Add entry peer'"
assert_ok "wg-ops list-menu entry shows panels" \
  bash -c "bash '$ROOT/deploy/wg-ops' list-menu entry | grep -q 'Update panels only'"
assert_ok "wg-ops list-menu entry shows check-client" \
  bash -c "bash '$ROOT/deploy/wg-ops' list-menu entry | grep -q 'Check client handshake'"
assert_ok "wg-ops maps check-client" \
  bash -c "bash '$ROOT/deploy/wg-ops' help | grep -q check-client"
assert_ok "check-client-handshake script present" \
  test -f "$ROOT/deploy/check-client-handshake.sh"
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
assert_ok "wg-client-rotate-keys syntax" python3 -m py_compile "$ROOT/client-panel/bin/wg-client-rotate-keys"

echo
echo "=== client config / rotate-keys guards ==="
assert_ok "wg-client rejects private endpoint helper" \
  grep -q 'is_public_endpoint_host' "$ROOT/client-panel/bin/wg-client"
assert_ok "wg-client asserts server pubkey sync" \
  grep -q 'assert_server_pubkey_sync' "$ROOT/client-panel/bin/wg-client"
assert_ok "rotate-keys preserves VPN_MODE" \
  grep -q '"VPN_MODE"' "$ROOT/client-panel/bin/wg-client-rotate-keys"
assert_ok "rotate-keys prefers wg-endpoint" \
  grep -q 'ENDPOINT_FILE' "$ROOT/client-panel/bin/wg-client-rotate-keys"
assert_ok "rotate-keys validates public endpoint" \
  env ROTATE_KEYS="$ROOT/client-panel/bin/wg-client-rotate-keys" python3 -c '
import os, sys
from importlib.machinery import SourceFileLoader
mod = SourceFileLoader("rotate_keys", os.environ["ROTATE_KEYS"]).load_module()
assert mod.is_public_endpoint_host("203.0.113.10")
assert not mod.is_public_endpoint_host("10.1.2.3")
assert not mod.is_public_endpoint_host("127.0.0.1")
for bad in ("127.0.0.1:51820", "10.0.0.5:51820"):
    try:
        mod.validate_client_endpoint(bad)
    except SystemExit:
        pass
    else:
        sys.exit(f"expected die for {bad}")
mod.validate_client_endpoint("203.0.113.10:51820")
'
assert_ok "diagnose classifies one-way client handshake" \
  grep -q 'ONE-WAY answered' "$ROOT/deploy/diagnose-vpn.sh"

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
assert_ok "exit PostUp route replace is tolerant" \
  grep -q 'ip route replace ${CLIENT_CIDR} dev ${TUNNEL_IF} 2>/dev/null || true' "$ROOT/deploy/install-exit-server.sh"

_tmpdir="$(mktemp -d)"
cat > "$_tmpdir/wg-tunnel.conf" <<'EOF'
[Interface]
Address = 10.200.0.1/30
PostUp = iptables -A FORWARD -i wg-tunnel -j ACCEPT; ip route replace 10.10.10.0/24 dev wg-tunnel; ip route replace 10.200.0.2/32 dev wg-tunnel
EOF
ensure_exit_tunnel_postup_tolerant "$_tmpdir/wg-tunnel.conf"
assert_ok "ensure_exit_tunnel_postup_tolerant softens routes" \
  grep -q 'ip route replace 10.10.10.0/24 dev wg-tunnel 2>/dev/null || true' "$_tmpdir/wg-tunnel.conf"
rm -rf "$_tmpdir"
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
