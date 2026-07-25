#!/usr/bin/env bash
# Repair panel systemd units and verify Python imports (run on entry server).
#
# Usage:
#   sudo wg-ops fix-panels
set -eo pipefail

if [[ -z "${WG_DEPLOY_REEXEC:-}" && ! -t 0 ]]; then
  export WG_DEPLOY_REEXEC=1
  GITHUB_RAW_BASE="${GITHUB_RAW_BASE:-https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@v1.0.19}"
  _WG_INSTALLER="$(mktemp /tmp/wg-fix-panel-services-XXXXXX.sh)"
  curl -fsSL "$GITHUB_RAW_BASE/deploy/fix-panel-services.sh" -o "$_WG_INSTALLER"
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
  GITHUB_RAW_BASE="${GITHUB_RAW_BASE:-https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@v1.0.19}"
  curl -fsSL "$GITHUB_RAW_BASE/deploy/repo.conf" -o "$_BOOT/deploy/repo.conf"
  curl -fsSL "$GITHUB_RAW_BASE/deploy/lib/common.sh" -o "$_BOOT/deploy/lib/common.sh"
  SCRIPT_DIR="$_BOOT/deploy"
  # shellcheck source=lib/common.sh
  source "$SCRIPT_DIR/lib/common.sh"
fi
set -u
require_root
require_entry_server

INSTALL_DIR="${WG_INSTALL_DIR:-/opt/wg}"
ENV_FILE="/etc/wireguard/entry-server.env"
CLIENT_IF="${WG_IF:-wg-clients}"
PY_PATH="${INSTALL_DIR}:${INSTALL_DIR}/client-panel:${INSTALL_DIR}/admin-panel"

[[ -f "$ENV_FILE" ]] || die "Missing $ENV_FILE"

patch_unit() {
  local unit="$1"
  local exec_line="$2"
  local path_line="Environment=PYTHONPATH=${PY_PATH}"

  if grep -q '^Environment=PYTHONPATH=' "$unit" 2>/dev/null; then
    sed -i "s|^Environment=PYTHONPATH=.*|${path_line}|" "$unit"
  else
    sed -i "/^EnvironmentFile=/a ${path_line}" "$unit"
  fi
  sed -i "s|^ExecStart=.*|ExecStart=${exec_line}|" "$unit"
}

log "=== Fix panel systemd units ==="
log "Install dir: ${INSTALL_DIR}"
log "PYTHONPATH:  ${PY_PATH}"

for req in \
  "${INSTALL_DIR}/client-panel/app.py" \
  "${INSTALL_DIR}/admin-panel/app.py" \
  "${INSTALL_DIR}/client-panel/client_panel/db/user_configs.py" \
  "${INSTALL_DIR}/wg_common/__init__.py" \
  "${INSTALL_DIR}/admin-panel/admin_panel/bootstrap.py"; do
  [[ -f "$req" ]] || warn "Missing: $req (run update-panels.sh or rsync from repo)"
done

patch_unit /etc/systemd/system/wg-panel.service \
  "/usr/bin/python3 ${INSTALL_DIR}/client-panel/app.py"
patch_unit /etc/systemd/system/wg-admin-panel.service \
  "/usr/bin/python3 ${INSTALL_DIR}/admin-panel/app.py"

systemctl daemon-reload
systemctl restart wg-panel wg-admin-panel
sleep 2

log "Import check (client panel)..."
PYTHONPATH="$PY_PATH" python3 -c "
from client_panel.server.handler import Handler
print('client panel import OK')
" || die "Client panel import failed — sync: sudo rsync -a /opt/wg-src/client-panel/ ${INSTALL_DIR}/client-panel/"

log "Import check (admin panel)..."
PYTHONPATH="$PY_PATH" python3 -c "
from admin_panel.server.handler import Handler
print('admin panel import OK')
" || die "Admin panel import failed — sync: sudo rsync -a /opt/wg-src/admin-panel/ ${INSTALL_DIR}/admin-panel/"

if ss -tlnp 2>/dev/null | grep -q ':8088'; then
  log "wg-panel listening on 8088"
else
  warn "Nothing listening on 8088 — check: journalctl -u wg-panel -n 40"
fi
if ss -tlnp 2>/dev/null | grep -q ':8090'; then
  log "wg-admin-panel listening on 8090"
else
  warn "Nothing listening on 8090 — check: journalctl -u wg-admin-panel -n 40"
fi

# shellcheck disable=SC1090
source "$ENV_FILE"
curl -fsS "http://127.0.0.1:${WG_PANEL_PORT:-8088}/health" && log "Client health OK" || warn "Client health check failed"
curl -fsS "http://127.0.0.1:${WG_ADMIN_PORT:-8090}/admin/health" && log "Admin health OK" || warn "Admin health check failed"

log "Done."
