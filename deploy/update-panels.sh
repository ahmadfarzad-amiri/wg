#!/usr/bin/env bash
# Update panel code without touching WireGuard keys.
# Usage: sudo bash deploy/update-panels.sh
#        curl -fsSL .../deploy/update-panels.sh | sudo bash
set -eo pipefail

# curl | bash: save to a temp file and re-run so stdin is not the script body.
if [[ -z "${WG_DEPLOY_REEXEC:-}" && ! -t 0 ]]; then
  export WG_DEPLOY_REEXEC=1
  GITHUB_RAW_BASE="${GITHUB_RAW_BASE:-https://raw.githubusercontent.com/ahmadfarzad-amiri/wg/main}"
  _WG_INSTALLER="$(mktemp /tmp/wg-update-panels-XXXXXX.sh)"
  curl -fsSL "$GITHUB_RAW_BASE/deploy/update-panels.sh" -o "$_WG_INSTALLER"
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
  GITHUB_RAW_BASE="${GITHUB_RAW_BASE:-https://raw.githubusercontent.com/ahmadfarzad-amiri/wg/main}"
  curl -fsSL "$GITHUB_RAW_BASE/deploy/repo.conf" -o "$_BOOT/deploy/repo.conf"
  curl -fsSL "$GITHUB_RAW_BASE/deploy/lib/common.sh" -o "$_BOOT/deploy/lib/common.sh"
  SCRIPT_DIR="$_BOOT/deploy"
  # shellcheck source=lib/common.sh
  source "$SCRIPT_DIR/lib/common.sh"
fi
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
rsync -a --delete \
  --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
  "$REPO_DIR/wg_common/" "$INSTALL_DIR/wg_common/"

systemctl restart wg-panel wg-admin-panel
log "Panels restarted."
if [[ -f "$INSTALL_DIR/client-panel/client_panel/config/settings.py" ]]; then
  _ver="$(grep -E '^VERSION[[:space:]]*=' "$INSTALL_DIR/client-panel/client_panel/config/settings.py" \
    | sed -E "s/.*[\"']([^\"']+)[\"'].*/\1/" | head -1)"
  log "Client panel VERSION (CSS cache bust): ${_ver:-unknown}"
  log "Verify UI: sudo bash ${SCRIPT_DIR}/check-sync-panel-styles.sh"
fi
