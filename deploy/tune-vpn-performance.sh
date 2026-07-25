#!/usr/bin/env bash
# Apply VPN routing repair + performance tuning (MSS clamp, BBR, UDP buffers), then diagnose.
#
# Run on entry and exit servers before speed tests or after config changes:
#   sudo wg-ops tune
#   sudo wg-ops tune --role entry
#
# Disable BBR/MSS via env: WG_ENABLE_BBR=0 WG_ENABLE_MSS_CLAMP=0 sudo bash ...
set -eo pipefail

if [[ -z "${WG_DEPLOY_REEXEC:-}" && ! -t 0 ]]; then
  export WG_DEPLOY_REEXEC=1
  GITHUB_RAW_BASE="${GITHUB_RAW_BASE:-https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@v1.0.11}"
  _WG_INSTALLER="$(mktemp /tmp/wg-tune-perf-XXXXXX.sh)"
  curl -fsSL "$GITHUB_RAW_BASE/deploy/tune-vpn-performance.sh" -o "$_WG_INSTALLER"
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
  GITHUB_RAW_BASE="${GITHUB_RAW_BASE:-https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@v1.0.11}"
  curl -fsSL "$GITHUB_RAW_BASE/deploy/repo.conf" -o "$_BOOT/deploy/repo.conf"
  curl -fsSL "$GITHUB_RAW_BASE/deploy/lib/common.sh" -o "$_BOOT/deploy/lib/common.sh"
  SCRIPT_DIR="$_BOOT/deploy"
  # shellcheck source=lib/common.sh
  source "$SCRIPT_DIR/lib/common.sh"
  fetch_deploy_helper_scripts fix-vpn-routing.sh diagnose-vpn.sh test-connectivity.sh
fi
set -u
require_root

ROLE="${1:-auto}"
if [[ "$ROLE" == "--role" ]]; then
  ROLE="${2:-auto}"
fi
if [[ "$ROLE" == "auto" ]]; then
  ROLE="$(server_role)"
  [[ "$ROLE" != "unknown" ]] || die "Could not detect role — use: sudo wg-ops tune --role entry|exit"
fi

if [[ -f /etc/wireguard/entry-server.env ]]; then
  # shellcheck disable=SC1091
  source /etc/wireguard/entry-server.env
elif [[ -f /etc/wireguard/exit-server.env ]]; then
  # shellcheck disable=SC1091
  source /etc/wireguard/exit-server.env
fi

log "=== Tune VPN performance (${ROLE}) ==="
log "WG_ENABLE_BBR=${WG_ENABLE_BBR:-1} WG_ENABLE_MSS_CLAMP=${WG_ENABLE_MSS_CLAMP:-1}"

bash "$SCRIPT_DIR/fix-vpn-routing.sh" --role "$ROLE"

if [[ "$ROLE" == "entry" ]] && command -v wg-client >/dev/null 2>&1; then
  wg-client sync-vpn-modes 2>/dev/null || warn "wg-client sync-vpn-modes failed"
fi

echo ""
bash "$SCRIPT_DIR/diagnose-vpn.sh" --role "$ROLE"

log "Done. Confirm exit IP from a twohop client: curl -4 https://api.ipify.org"
log "Hop bandwidth plan: sudo wg-ops measure --role guide"
