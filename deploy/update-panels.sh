#!/usr/bin/env bash
# Update panel code without touching WireGuard keys.
# Usage: sudo bash deploy/update-panels.sh
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "$SCRIPT_DIR/lib/common.sh"
set -u
require_root

REPO_DIR="${WG_REPO_DIR:-/opt/wg-src}"
INSTALL_DIR="${WG_INSTALL_DIR:-/opt/wg}"
ENV_FILE="/etc/wireguard/entry-server.env"

[[ -f "$ENV_FILE" ]] || die "Not an entry server ($ENV_FILE missing)"

if [[ -f "$SCRIPT_DIR/../client-panel/app.py" ]]; then
  REPO_DIR="$SCRIPT_DIR/.."
else
  install_packages git curl
  clone_or_update_repo "${WG_GITHUB_REPO:-$GITHUB_REPO_URL}" "${WG_GITHUB_BRANCH:-$GITHUB_BRANCH}" "$REPO_DIR"
fi

log "Updating panels in $INSTALL_DIR from $REPO_DIR"
mkdir -p "$INSTALL_DIR"
rsync -a --delete \
  --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
  "$REPO_DIR/client-panel/" "$INSTALL_DIR/client-panel/"
rsync -a --delete \
  --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
  "$REPO_DIR/admin-panel/" "$INSTALL_DIR/admin-panel/"

systemctl restart wg-panel wg-admin-panel
log "Panels restarted."
