#!/usr/bin/env bash
# Check client/admin panel UI files on the entry server and optionally sync from repo.
#
# Usage (on entry server):
#   sudo wg-ops styles          # check only
#   sudo wg-ops styles --fix    # check, sync panels, restart
#
# One-liner from GitHub:
#   curl -fsSL https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@v1.0.8/deploy/check-sync-panel-styles.sh -o /tmp/check-panel-styles.sh
#   sudo bash /tmp/check-panel-styles.sh --fix
#
# Env:
#   WG_INSTALL_DIR=/opt/wg     installed panels
#   WG_REPO_DIR=/opt/wg-src    source to sync from (with --fix)
set -eo pipefail

if [[ -z "${WG_DEPLOY_REEXEC:-}" && ! -t 0 ]]; then
  export WG_DEPLOY_REEXEC=1
  GITHUB_RAW_BASE="${GITHUB_RAW_BASE:-https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@v1.0.8}"
  _WG_INSTALLER="$(mktemp /tmp/wg-check-panel-styles-XXXXXX.sh)"
  curl -fsSL "$GITHUB_RAW_BASE/deploy/check-sync-panel-styles.sh" -o "$_WG_INSTALLER"
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
  GITHUB_RAW_BASE="${GITHUB_RAW_BASE:-https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@v1.0.8}"
  curl -fsSL "$GITHUB_RAW_BASE/deploy/repo.conf" -o "$_BOOT/deploy/repo.conf"
  curl -fsSL "$GITHUB_RAW_BASE/deploy/lib/common.sh" -o "$_BOOT/deploy/lib/common.sh"
  SCRIPT_DIR="$_BOOT/deploy"
  # shellcheck source=lib/common.sh
  source "$SCRIPT_DIR/lib/common.sh"
fi
set -u

DO_FIX=0
for arg in "$@"; do
  case "$arg" in
    --fix) DO_FIX=1 ;;
    -h|--help)
      sed -n '2,14p' "$0" 2>/dev/null || true
      exit 0
      ;;
    *) die "Unknown option: $arg (use --fix or no args)" ;;
  esac
done

require_root

INSTALL_DIR="${WG_INSTALL_DIR:-/opt/wg}"
if [[ -n "${WG_REPO_DIR:-}" ]]; then
  REPO_DIR="$WG_REPO_DIR"
elif [[ -n "${SCRIPT_DIR:-}" && -d "${SCRIPT_DIR}/../client-panel" ]]; then
  REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
else
  REPO_DIR="/opt/wg-src"
fi
CLIENT_CSS="${INSTALL_DIR}/client-panel/static/css/panel.css"
ADMIN_CSS="${INSTALL_DIR}/admin-panel/static/css/admin.css"
CLIENT_LAYOUT="${INSTALL_DIR}/client-panel/client_panel/components/layout.py"
CLIENT_SETTINGS_VIEW="${INSTALL_DIR}/client-panel/client_panel/views/settings.py"
CLIENT_SETTINGS="${INSTALL_DIR}/client-panel/client_panel/config/settings.py"
PANEL_PORT="${WG_PANEL_PORT:-8088}"
ADMIN_PORT="${WG_ADMIN_PORT:-8090}"

pass=0
fail=0
warn_count=0

check_ok() {
  printf '  %-48s OK\n' "$1"
  pass=$((pass + 1))
}

check_fail() {
  printf '  %-48s FAIL\n' "$1"
  fail=$((fail + 1))
}

check_warn() {
  printf '  %-48s WARN\n' "$1"
  warn_count=$((warn_count + 1))
}

grep_file() {
  local path="$1"
  local pattern="$2"
  [[ -f "$path" ]] && grep -qE "$pattern" "$path"
}

file_mtime() {
  local path="$1"
  if [[ -f "$path" ]]; then
    stat -c '%y' "$path" 2>/dev/null || stat -f '%Sm' "$path" 2>/dev/null || echo "unknown"
  else
    echo "missing"
  fi
}

check_panel_css() {
  local label="$1"
  local css="$2"
  local layout="${3:-}"

  log "${label} UI files"
  if [[ ! -f "$css" ]]; then
    check_fail "${label} CSS present"
    return 1
  fi
  check_ok "${label} CSS present"
  log "    path: $css"
  log "    modified: $(file_mtime "$css")"

  if [[ "$label" == "Client" ]]; then
    if grep -A30 '^\.page-stack' "$css" 2>/dev/null | grep -qE 'margin-top:[[:space:]]*24px'; then
      check_ok "${label} page-stack block spacing 24px"
    else
      check_fail "${label} page-stack block spacing 24px"
    fi
  elif grep -A12 '^\.page-stack' "$css" 2>/dev/null | grep -qE 'gap:[[:space:]]*18px'; then
    check_ok "${label} page-stack gap 18px"
  else
    check_fail "${label} page-stack layout"
  fi

  if grep_file "$css" 'locale-bar-controls'; then
    check_ok "${label} locale-bar-controls"
  else
    check_fail "${label} locale-bar-controls"
  fi

  if grep_file "$css" 'display:[[:space:]]*contents'; then
    check_fail "${label} no display:contents (stale)"
  else
    check_ok "${label} no display:contents (stale)"
  fi

  if [[ "$label" == "Client" ]] && grep -q 'dashboard-metrics' "$css"; then
    check_ok "${label} dashboard-metrics grid"
  elif [[ "$label" == "Client" ]]; then
    check_fail "${label} dashboard-metrics grid"
  fi

  if [[ "$label" == "Client" ]]; then
    if [[ -f "$CLIENT_LAYOUT" ]] && grep -q 'locale_version_bar' "$CLIENT_LAYOUT" 2>/dev/null; then
      check_fail "${label} locale bar not in global layout"
    else
      check_ok "${label} locale bar not in global layout"
    fi
    if [[ -f "$CLIENT_SETTINGS_VIEW" ]] && grep -q 'locale_version_bar' "$CLIENT_SETTINGS_VIEW"; then
      check_ok "${label} locale bar on settings page"
    else
      check_fail "${label} locale bar on settings page"
    fi
  fi
}

check_client_static_cache() {
  local py="${INSTALL_DIR}/client-panel/client_panel/server/responses.py"
  if [[ ! -f "$py" ]]; then
    check_warn "client responses.py missing"
    return
  fi
  if grep -q 'max-age=3600, must-revalidate' "$py"; then
    check_ok "client static CSS/JS cache headers"
  else
    check_fail "client static CSS/JS cache headers"
  fi
}

check_client_version() {
  if [[ -f "$CLIENT_SETTINGS" ]]; then
    local ver
    ver="$(grep -E '^VERSION[[:space:]]*=' "$CLIENT_SETTINGS" 2>/dev/null | head -1 | sed -E "s/.*[\"']([^\"']+)[\"'].*/\1/")"
    log "Client panel VERSION (cache bust): ${ver:-unknown}"
    if [[ "${ver:-}" == "1.0.3" ]]; then
      check_ok "client VERSION ${ver} (cache bust)"
    elif [[ "${ver:-}" == "1.0.0" || "${ver:-}" == "1.0.1" || "${ver:-}" == "1.0.2" ]]; then
      check_warn "client VERSION is ${ver} (run --fix to bump to 1.0.3)"
    else
      check_warn "client VERSION is ${ver:-?} (expected 1.0.3)"
    fi
  else
    check_warn "client settings.py missing"
  fi
}

check_http_css() {
  local port="$1"
  local label="$2"
  local pattern="$3"
  local url="http://127.0.0.1:${port}/static/css/panel.css"
  if [[ "$label" == "admin" ]]; then
    url="http://127.0.0.1:${port}/admin/static/css/admin.css"
  fi
  local body
  if ! body="$(curl -fsS --max-time 5 "$url" 2>/dev/null)"; then
    check_warn "${label} HTTP static CSS (${url})"
    return
  fi
  if printf '%s' "$body" | grep -qE "$pattern"; then
    check_ok "${label} HTTP serves updated CSS"
  else
    check_fail "${label} HTTP serves updated CSS"
  fi
}

run_all_checks() {
  pass=0
  fail=0
  warn_count=0

  log "=== Panel UI style check (installed: ${INSTALL_DIR}) ==="

  if [[ ! -f /etc/wireguard/entry-server.env ]]; then
    warn "Not an entry server — panel UI runs on entry VPS only"
  fi

  check_panel_css "Client" "$CLIENT_CSS" ""
  check_client_static_cache
  check_client_version
  check_panel_css "Admin" "$ADMIN_CSS" ""

  if systemctl is-active wg-panel >/dev/null 2>&1; then
    check_http_css "$PANEL_PORT" "client" 'locale-bar-controls'
    local cc
    cc="$(curl -sI --max-time 5 "http://127.0.0.1:${PANEL_PORT}/static/css/panel.css" 2>/dev/null \
      | tr -d '\r' | grep -i '^[Cc]ache-[Cc]ontrol:' | head -1 || true)"
    if [[ "$cc" == *must-revalidate* ]]; then
      check_ok "client CSS Cache-Control (must-revalidate)"
    elif [[ "$cc" == *immutable* ]]; then
      check_fail "client CSS Cache-Control still immutable (stale)"
    else
      check_warn "client CSS Cache-Control: ${cc:-unknown}"
    fi
  else
    check_warn "wg-panel not active — skip HTTP CSS check"
  fi

  if systemctl is-active wg-admin-panel >/dev/null 2>&1; then
    check_http_css "$ADMIN_PORT" "admin" 'locale-bar-controls'
  else
    check_warn "wg-admin-panel not active — skip HTTP CSS check"
  fi

  if [[ -d "$REPO_DIR/client-panel" ]]; then
    if cmp -s "$REPO_DIR/client-panel/static/css/panel.css" "$CLIENT_CSS" 2>/dev/null; then
      check_ok "repo matches installed client CSS"
    else
      check_warn "repo differs from installed client CSS"
      log "    fix: sudo wg-ops update-panels"
    fi
  else
    check_warn "repo not found at ${REPO_DIR} (clone or set WG_REPO_DIR)"
  fi

  echo ""
  log "Results: ${pass} passed, ${fail} failed, ${warn_count} warnings"
}

run_all_checks

if [[ "$fail" -eq 0 && "$warn_count" -eq 0 ]]; then
  log "Panel UI files look up to date."
  log "If the browser still looks wrong: hard refresh (Ctrl+Shift+R) or clear site cache."
  exit 0
fi

if [[ "$DO_FIX" -eq 0 ]]; then
  echo ""
  log "To apply fixes from repo and restart panels:"
  log "  sudo bash ${SCRIPT_DIR}/check-sync-panel-styles.sh --fix"
  log "Or:"
  log "  sudo wg-ops update-panels"
  exit 1
fi

bump_client_panel_version() {
  local target="1.0.3"
  local bumped=0
  local f
  for f in \
    "$INSTALL_DIR/client-panel/client_panel/config/settings.py" \
    "$REPO_DIR/client-panel/client_panel/config/settings.py"; do
    [[ -f "$f" ]] || continue
    if ! grep -qE "^VERSION = \"${target}\"" "$f" 2>/dev/null; then
      sed -i "s/^VERSION = .*/VERSION = \"${target}\"/" "$f"
      bumped=1
    fi
  done
  if [[ "$bumped" -eq 1 ]]; then
    log "Set client panel VERSION to ${target} (forces new ?v= in browser)"
    systemctl restart wg-panel 2>/dev/null || true
    sleep 1
  fi
}

log "=== Applying panel sync (--fix) ==="
if [[ ! -f "$SCRIPT_DIR/update-panels.sh" ]]; then
  die "Missing ${SCRIPT_DIR}/update-panels.sh"
fi
export WG_REPO_DIR="$REPO_DIR"
bash "$SCRIPT_DIR/update-panels.sh"
bump_client_panel_version
echo ""
log "Re-running checks after sync..."
run_all_checks

if [[ "$fail" -eq 0 ]]; then
  log "Panel UI sync complete."
  if [[ "$warn_count" -gt 0 ]]; then
    log "Warnings are OK — hard refresh the client panel: Ctrl+Shift+R"
    log "CSS URL should load as panel.css?v=1.0.3"
  else
    log "Hard refresh the client panel once: Ctrl+Shift+R"
  fi
  exit 0
fi
exit 1
