#!/usr/bin/env bash
# Restore WireGuard configs from a backup directory.
# Usage: sudo bash deploy/restore.sh /etc/wireguard/backups/20250101-120000-pre-install
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "$SCRIPT_DIR/lib/common.sh"
set -u
require_root

SRC="${1:-}"
[[ -n "$SRC" && -d "$SRC" ]] || die "Usage: $0 /etc/wireguard/backups/TIMESTAMP-label"

backup_wg_configs "pre-restore"

for f in "$SRC"/*; do
  [[ -f "$f" ]] || continue
  base="$(basename "$f")"
  cp -a "$f" "/etc/wireguard/$base"
  log "Restored /etc/wireguard/$base"
done

wg-quick down wg-clients 2>/dev/null || true
wg-quick down wg-tunnel 2>/dev/null || true
wg-quick up /etc/wireguard/wg-clients.conf 2>/dev/null || true
wg-quick up /etc/wireguard/wg-tunnel.conf 2>/dev/null || true
systemctl restart wg-panel wg-admin-panel 2>/dev/null || true

log "Restore complete. Verify with: bash deploy/test-connectivity.sh --role entry"
