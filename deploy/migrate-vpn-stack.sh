#!/usr/bin/env bash
# Migrate an existing entry/exit install to the simplified two-hop dataplane.
#
# Safe defaults:
#   - Backs up /etc/wireguard configs first
#   - Does not delete private keys or client .conf files
#   - Supports --dry-run
#
# Usage (on the server):
#   sudo bash deploy/migrate-vpn-stack.sh --role entry|exit|auto [--dry-run]
#
# After a successful migration, verify:
#   sudo bash deploy/validate-config.sh --role runtime
#   sudo bash deploy/diagnose-vpn.sh --role entry|exit
#   sudo bash deploy/test-connectivity.sh --role entry|exit
set -eo pipefail

_WG_SCRIPT=""
if [[ "${BASH_SOURCE[0]+set}" == "set" ]]; then
  _WG_SCRIPT="${BASH_SOURCE[0]}"
fi
if [[ -n "$_WG_SCRIPT" && -f "$(dirname "$_WG_SCRIPT")/lib/common.sh" ]]; then
  SCRIPT_DIR="$(cd "$(dirname "$_WG_SCRIPT")" && pwd)"
  # shellcheck source=lib/common.sh
  source "$SCRIPT_DIR/lib/common.sh"
else
  echo '[wg-deploy] ERROR: Run from a checked-out repo (deploy/lib/common.sh required)' >&2
  exit 1
fi
set -u
require_root

ROLE="auto"
DRY_RUN=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --role) ROLE="${2:-}"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help)
      cat <<EOF
Usage: sudo bash deploy/migrate-vpn-stack.sh --role entry|exit|auto [--dry-run]

Migrates routing/firewall/MTU/sysctl to the current two-hop dataplane:
  - Removes broad wg-clients FORWARD ACCEPT (entry)
  - Deduplicates NAT/FORWARD/MSS rules
  - Applies performance sysctl + MSS clamp unit
  - Preserves WireGuard private keys and client configs
EOF
      exit 0
      ;;
    *) die "Unknown argument: $1" ;;
  esac
done

if [[ "$ROLE" == "auto" ]]; then
  ROLE="$(server_role)"
  [[ "$ROLE" != "unknown" ]] || die "Could not detect role — pass --role entry|exit"
fi

log "=== Migrate VPN stack (role=${ROLE} dry_run=${DRY_RUN}) ==="

if [[ "$DRY_RUN" -eq 1 ]]; then
  log "Planned changes:"
  if [[ "$ROLE" == "entry" ]]; then
    log "  - Backup /etc/wireguard/*.conf *.env"
    log "  - Rewrite wg-clients PostUp to route-only if legacy FORWARD present"
    log "  - Apply policy table 100, narrow FORWARD, anti-leak DROP"
    log "  - Apply MSS clamp + performance sysctl + server MTUs"
    log "  - Sync per-client direct-mode exceptions (if any)"
  else
    log "  - Backup /etc/wireguard/*.conf *.env"
    log "  - Deduplicate exit MASQUERADE + FORWARD rules"
    log "  - Ensure client subnet route via wg-tunnel"
    log "  - Apply MSS clamp + performance sysctl + tunnel MTU"
  fi
  log "Dry-run complete — no changes made"
  exit 0
fi

backup_wg_configs "pre-migrate"

if [[ "$ROLE" == "entry" ]]; then
  if [[ -f /etc/wireguard/entry-server.env ]]; then
    # shellcheck disable=SC1091
    source /etc/wireguard/entry-server.env
  fi
  fix_entry_client_postup_in_conf \
    "/etc/wireguard/${WG_IF:-wg-clients}.conf" \
    "${WG_IF:-wg-clients}" \
    "${WG_CLIENT_CIDR:-10.10.10.0/24}"
  fix_entry_tunnel_postup_in_conf "/etc/wireguard/${WG_TUNNEL_IF:-wg-tunnel}.conf"
  strip_wrong_entry_tunnel_peer_block "/etc/wireguard/${WG_TUNNEL_IF:-wg-tunnel}.conf"
  apply_entry_vpn_routing_fix
  # Persist new MTU env knobs if missing.
  if [[ -f /etc/wireguard/entry-server.env ]]; then
    grep -q '^WG_ENTRY_ANTILEAK=' /etc/wireguard/entry-server.env 2>/dev/null \
      || echo "WG_ENTRY_ANTILEAK=1" >> /etc/wireguard/entry-server.env
    grep -q '^WG_CLIENTS_MTU=' /etc/wireguard/entry-server.env 2>/dev/null \
      || echo "WG_CLIENTS_MTU=${WG_SERVER_MTU:-1420}" >> /etc/wireguard/entry-server.env
    grep -q '^WG_TUNNEL_MTU=' /etc/wireguard/entry-server.env 2>/dev/null \
      || echo "WG_TUNNEL_MTU=${WG_SERVER_MTU:-1420}" >> /etc/wireguard/entry-server.env
  fi
else
  if [[ -f /etc/wireguard/exit-server.env ]]; then
    # shellcheck disable=SC1091
    source /etc/wireguard/exit-server.env
  fi
  apply_exit_vpn_routing_fix
  if [[ -f /etc/wireguard/exit-server.env ]]; then
    grep -q '^WG_TUNNEL_MTU=' /etc/wireguard/exit-server.env 2>/dev/null \
      || echo "WG_TUNNEL_MTU=${WG_SERVER_MTU:-1420}" >> /etc/wireguard/exit-server.env
  fi
fi

log "Migration applied. Next:"
log "  sudo bash deploy/validate-config.sh --role runtime"
log "  sudo bash deploy/diagnose-vpn.sh --role ${ROLE}"
log "  sudo bash deploy/test-connectivity.sh --role ${ROLE}"
log "Rollback: restore files from /etc/wireguard/backups/<timestamp>-pre-migrate/"
log "  then: sudo bash deploy/fix-vpn-routing.sh --role ${ROLE}"
