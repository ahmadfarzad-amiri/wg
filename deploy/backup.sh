#!/usr/bin/env bash
# Backup WireGuard configs, env files, and panel database.
# Usage: sudo wg-ops backup [label]
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "$SCRIPT_DIR/lib/common.sh"
set -u
require_root

LABEL="${1:-manual}"
backup_wg_configs "$LABEL"

if [[ -f /etc/wireguard/panel.db ]]; then
  ts="$(date +%Y%m%d-%H%M%S)"
  dest="/etc/wireguard/backups/${ts}-${LABEL}"
  mkdir -p "$dest"
  cp -a /etc/wireguard/panel.db "$dest/"
  log "Included panel.db in $dest"
fi

log "Backup complete."
