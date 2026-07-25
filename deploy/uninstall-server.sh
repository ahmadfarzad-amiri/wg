#!/usr/bin/env bash
# Remove WireGuard VPN deployment — panels, database, configs, nginx, systemd units.
# Works on entry or exit servers (auto-detected). Fresh-install stack only.
#
# Preferred:
#   sudo WG_UNINSTALL_CONFIRM=yes wg-ops uninstall
#
# Optional config snapshot before removal:
#   sudo WG_UNINSTALL_BACKUP=1 WG_UNINSTALL_CONFIRM=yes wg-ops uninstall
#
# Direct path after wg-ops pull:
#   sudo bash /opt/wg-ops/uninstall-server.sh
set -eo pipefail

if [[ -z "${WG_DEPLOY_REEXEC:-}" && ! -t 0 ]]; then
  export WG_DEPLOY_REEXEC=1
  GITHUB_RAW_BASE="${GITHUB_RAW_BASE:-https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@v1.0.10}"
  _WG_INSTALLER="$(mktemp /tmp/wg-uninstall-XXXXXX.sh)"
  curl -fsSL "$GITHUB_RAW_BASE/deploy/uninstall-server.sh" -o "$_WG_INSTALLER"
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
  GITHUB_RAW_BASE="${GITHUB_RAW_BASE:-https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@v1.0.10}"
  curl -fsSL "$GITHUB_RAW_BASE/deploy/repo.conf" -o "$_BOOT/deploy/repo.conf"
  curl -fsSL "$GITHUB_RAW_BASE/deploy/lib/common.sh" -o "$_BOOT/deploy/lib/common.sh"
  SCRIPT_DIR="$_BOOT/deploy"
  # shellcheck source=lib/common.sh
  source "$SCRIPT_DIR/lib/common.sh"
fi
set -u
require_root

ROLE="${1:-auto}"
if [[ "$ROLE" == "--role" ]]; then
  ROLE="${2:-auto}"
fi
if [[ "$ROLE" == "auto" ]]; then
  ROLE="$(detect_uninstall_role)"
fi

if [[ "$ROLE" == "unknown" ]]; then
  die "No WireGuard panel install detected on this server."
fi

log "=== Uninstall WireGuard deployment (${ROLE} server) ==="
require_uninstall_confirm

load_uninstall_env "$ROLE"
PANEL_DOMAIN="${WG_PANEL_DOMAIN:-}"
if [[ -z "$PANEL_DOMAIN" ]]; then
  PANEL_DOMAIN="$(parse_panel_domain_from_nginx 2>/dev/null || true)"
fi

if [[ "${WG_UNINSTALL_BACKUP:-0}" == "1" ]]; then
  backup_wg_configs "pre-uninstall"
  _latest_backup="$(ls -td /etc/wireguard/backups/*-pre-uninstall 2>/dev/null | head -1 || true)"
  if [[ -n "$_latest_backup" ]]; then
    _preserve="/root/wg-backup-$(basename "$_latest_backup")"
    cp -a "$_latest_backup" "$_preserve"
    log "Backup preserved at $_preserve"
  fi
fi

log "Stopping services..."
stop_systemd_unit wg-panel.service
stop_systemd_unit wg-admin-panel.service
stop_systemd_unit wg-docker-forward.service
stop_systemd_unit wg-mss-clamp.service
stop_systemd_unit wg-client-enforce.timer
stop_systemd_unit wg-client-enforce.service

log "Bringing down WireGuard interfaces and cleaning routing..."
uninstall_wg_stop_interfaces "$ROLE"

log "Removing systemd units..."
uninstall_wg_systemd_units "$ROLE"

if [[ "$ROLE" == "entry" ]]; then
  log "Removing nginx panel site..."
  uninstall_wg_nginx "$PANEL_DOMAIN"
  if [[ -n "$PANEL_DOMAIN" ]]; then
    uninstall_wg_certbot "$PANEL_DOMAIN"
  fi
fi

log "Removing firewall rules (ufw)..."
uninstall_wg_ufw_rules

log "Removing installed files..."
uninstall_wg_bin_tools
uninstall_wg_data_dirs

cat <<EOF

=== Uninstall complete ===
Role removed : ${ROLE}
WireGuard VPN, panels, database, keys, and configs have been removed from this server.

Note: system packages (wireguard-tools, nginx, python3, certbot) were not removed.
      ip_forward in /etc/sysctl.conf was left unchanged in case other services need it.

EOF
