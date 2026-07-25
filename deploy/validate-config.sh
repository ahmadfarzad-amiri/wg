#!/usr/bin/env bash
# Validate install/runtime configuration before applying changes.
#
# Usage:
#   sudo wg-ops validate --role entry|exit|runtime [--dry-run]
#
# Exit codes: 0 = valid, 1 = validation failed
# Does not modify the system.
set -eo pipefail

if [[ -z "${WG_DEPLOY_REEXEC:-}" && ! -t 0 ]]; then
  export WG_DEPLOY_REEXEC=1
  if [[ -z "${GITHUB_RAW_BASE:-}" ]]; then
    if [[ -n "${WG_RAW_BASE:-}" ]]; then
      GITHUB_RAW_BASE="$WG_RAW_BASE"
    elif [[ -n "${WG_VERSION:-}" ]]; then
      GITHUB_RAW_BASE="https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@v${WG_VERSION#v}"
    else
      GITHUB_RAW_BASE="https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@latest"
    fi
  fi
  _WG_INSTALLER="$(mktemp /tmp/wg-validate-XXXXXX.sh)"
  curl -fsSL "$GITHUB_RAW_BASE/deploy/validate-config.sh" -o "$_WG_INSTALLER"
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
  if [[ -z "${GITHUB_RAW_BASE:-}" ]]; then
    if [[ -n "${WG_RAW_BASE:-}" ]]; then
      GITHUB_RAW_BASE="$WG_RAW_BASE"
    elif [[ -n "${WG_VERSION:-}" ]]; then
      GITHUB_RAW_BASE="https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@v${WG_VERSION#v}"
    else
      GITHUB_RAW_BASE="https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@latest"
    fi
  fi
  curl -fsSL "$GITHUB_RAW_BASE/deploy/repo.conf" -o "$_BOOT/deploy/repo.conf"
  curl -fsSL "$GITHUB_RAW_BASE/deploy/lib/common.sh" -o "$_BOOT/deploy/lib/common.sh"
  SCRIPT_DIR="$_BOOT/deploy"
  # shellcheck source=lib/common.sh
  source "$SCRIPT_DIR/lib/common.sh"
fi
set -u

ROLE="auto"
DRY_RUN=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --role) ROLE="${2:-}"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help)
      echo "Usage: $0 --role entry|exit|runtime [--dry-run]"
      exit 0
      ;;
    *) die "Unknown argument: $1" ;;
  esac
done

if [[ "$ROLE" == "auto" ]]; then
  ROLE="$(server_role)"
  if [[ "$ROLE" == "unknown" ]]; then
    die "Could not detect role — pass --role entry|exit|runtime"
  fi
fi

log "=== Validate configuration (role=${ROLE}) ==="
if [[ "$DRY_RUN" -eq 1 ]]; then
  log "Dry-run mode — checks only"
fi

case "$ROLE" in
  exit)
    wg_validate_exit_install_env
    if [[ -f /etc/wireguard/exit-server.env ]]; then
      # shellcheck disable=SC1091
      source /etc/wireguard/exit-server.env
      wg_validate_exit_install_env
      wg_is_iface_name "${WG_TUNNEL_IF:-wg-tunnel}" \
        || die "Invalid WG_TUNNEL_IF"
    fi
    if [[ -f /etc/wireguard/wg-tunnel.conf ]]; then
      local_key_mode="$(stat -c '%a' /etc/wireguard/wg-tunnel.conf 2>/dev/null \
        || stat -f '%Lp' /etc/wireguard/wg-tunnel.conf 2>/dev/null || echo unknown)"
      if [[ "$local_key_mode" != "unknown" && "$local_key_mode" != "600" && "$local_key_mode" != "400" ]]; then
        warn "wg-tunnel.conf permissions are ${local_key_mode} (prefer 600)"
      fi
    fi
    log "Exit configuration: OK"
    ;;
  entry)
    if [[ -f /etc/wireguard/entry-server.env ]]; then
      # shellcheck disable=SC1091
      source /etc/wireguard/entry-server.env
    fi
    wg_validate_entry_install_env
    wg_check_duplicate_client_addresses /etc/wireguard/clients
    if [[ -f /etc/wireguard/wg-clients.conf ]]; then
      if grep -qE 'iptables -A FORWARD -i wg-clients -j ACCEPT' /etc/wireguard/wg-clients.conf; then
        die "Broad FORWARD PostUp in wg-clients.conf — run: sudo wg-ops fix-routing (or uninstall and reinstall)"
      fi
    fi
    log "Entry configuration: OK"
    ;;
  runtime)
    ROLE_DETECTED="$(server_role)"
    [[ "$ROLE_DETECTED" != "unknown" ]] || die "No entry-server.env or exit-server.env found"
    if [[ "$ROLE_DETECTED" == "entry" ]]; then
      # shellcheck disable=SC1091
      source /etc/wireguard/entry-server.env
      wg_validate_entry_install_env
      wg_check_duplicate_client_addresses /etc/wireguard/clients
      if wg_entry_is_standalone; then
        iptables -C FORWARD -i wg-clients -o "$(default_route_iface 2>/dev/null || echo eth0)" -j ACCEPT 2>/dev/null \
          || warn "Standalone: missing client→WAN FORWARD (run: sudo wg-ops fix-routing)"
        if ! iptables -t nat -S POSTROUTING 2>/dev/null | grep -qE "\-s ${WG_CLIENT_CIDR:-10.10.10.0/24} .*-j MASQUERADE"; then
          die "Standalone entry missing subnet MASQUERADE for ${WG_CLIENT_CIDR:-10.10.10.0/24}"
        fi
      else
        ip rule show | grep -q 'lookup 100' \
          || die "Missing policy rule lookup 100 (two-hop egress)"
        iptables -C FORWARD -i wg-clients -o wg-tunnel -j ACCEPT 2>/dev/null \
          || die "Missing client→tunnel FORWARD rule"
        iptables -C FORWARD -i wg-tunnel -o wg-clients -j ACCEPT 2>/dev/null \
          || die "Missing tunnel→client FORWARD rule"
        # NAT must not masquerade the whole client subnet on entry (exit owns internet NAT).
        if iptables -t nat -S POSTROUTING 2>/dev/null | grep -qE "\-s ${WG_CLIENT_CIDR:-10.10.10.0/24} .*-j MASQUERADE"; then
          warn "Entry has subnet MASQUERADE for ${WG_CLIENT_CIDR:-10.10.10.0/24} — unexpected double-NAT risk (per-IP direct-mode NAT is OK)"
        fi
      fi
    else
      # shellcheck disable=SC1091
      source /etc/wireguard/exit-server.env
      wg_validate_exit_install_env
      iptables -t nat -S POSTROUTING 2>/dev/null | grep -q MASQUERADE \
        || die "Exit missing MASQUERADE rule"
    fi
    log "Runtime configuration: OK"
    ;;
  *)
    die "Usage: $0 --role entry|exit|runtime [--dry-run]"
    ;;
esac
