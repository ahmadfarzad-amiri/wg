#!/usr/bin/env bash
# Add entry server as peer on exit server (run on exit after entry install).
# Usage: sudo bash deploy/add-entry-peer.sh [ENTRY_TUNNEL_PUBLIC_KEY]
set -eo pipefail

# curl | bash: re-run from a script fd so prompts are not read from stdin.
if [[ -z "${WG_DEPLOY_REEXEC:-}" && ! -t 0 ]]; then
  export WG_DEPLOY_REEXEC=1
  GITHUB_RAW_BASE="${GITHUB_RAW_BASE:-https://raw.githubusercontent.com/ahmadfarzad-amiri/wg/main}"
  exec bash <(curl -fsSL "$GITHUB_RAW_BASE/deploy/add-entry-peer.sh") "$@"
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
install_wg_tools

TUNNEL_IF="${WG_TUNNEL_IF:-wg-tunnel}"
CLIENT_CIDR="${WG_CLIENT_CIDR:-10.10.10.0/24}"
TUNNEL_PEER_IP="${WG_TUNNEL_PEER_IP:-10.200.0.2/32}"

ENTRY_PUB="${1:-}"
if [[ -z "$ENTRY_PUB" ]]; then
  prompt ENTRY_PUB "Entry server tunnel public key" ""
fi

wg show "$TUNNEL_IF" >/dev/null 2>&1 || die "Interface $TUNNEL_IF is not up. Run install-exit-server.sh first."

wg set "$TUNNEL_IF" peer "$ENTRY_PUB" allowed-ips "${CLIENT_CIDR},${TUNNEL_PEER_IP}"
printf '%s\n' "$ENTRY_PUB" > /etc/wireguard/tunnel-entry.pub
chmod 600 /etc/wireguard/tunnel-entry.pub

log "Added entry server peer to $TUNNEL_IF"
wg show "$TUNNEL_IF"
