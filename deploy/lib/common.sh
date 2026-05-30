#!/usr/bin/env bash
# Shared helpers for WireGuard panel deployment scripts.
set -euo pipefail

log() { printf '[wg-deploy] %s\n' "$*"; }
warn() { printf '[wg-deploy] WARN: %s\n' "$*" >&2; }
die() { printf '[wg-deploy] ERROR: %s\n' "$*" >&2; exit 1; }

require_root() {
  [[ "$(id -u)" -eq 0 ]] || die "Run as root: sudo bash $0"
}

prompt() {
  local var_name="$1"
  local message="$2"
  local default="${3:-}"
  local value=""
  if [[ -n "$default" ]]; then
    read -r -p "$message [$default]: " value || true
    value="${value:-$default}"
  else
    read -r -p "$message: " value || true
    while [[ -z "$value" ]]; do
      read -r -p "$message: " value || true
    done
  fi
  printf -v "$var_name" '%s' "$value"
}

prompt_secret() {
  local var_name="$1"
  local message="$2"
  local value=""
  read -r -s -p "$message: " value || true
  echo ""
  while [[ -z "$value" ]]; do
    read -r -s -p "$message: " value || true
    echo ""
  done
  printf -v "$var_name" '%s' "$value"
}

detect_public_ip() {
  curl -4fsS --max-time 5 https://api.ipify.org 2>/dev/null \
    || curl -4fsS --max-time 5 https://ifconfig.me 2>/dev/null \
    || hostname -I 2>/dev/null | awk '{print $1}' \
    || echo "127.0.0.1"
}

install_packages() {
  local pkgs=("$@")
  if command -v apt-get >/dev/null 2>&1; then
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    apt-get install -y -qq "${pkgs[@]}"
    return
  fi
  if command -v dnf >/dev/null 2>&1; then
    dnf install -y "${pkgs[@]}"
    return
  fi
  if command -v yum >/dev/null 2>&1; then
    yum install -y "${pkgs[@]}"
    return
  fi
  die "Unsupported package manager. Install manually: ${pkgs[*]}"
}

clone_or_update_repo() {
  local repo_url="$1"
  local branch="$2"
  local dest="$3"
  if [[ -d "$dest/.git" ]]; then
    log "Updating existing repo at $dest"
    git -C "$dest" fetch origin "$branch"
    git -C "$dest" checkout "$branch"
    git -C "$dest" pull --ff-only origin "$branch"
  else
    log "Cloning $repo_url (branch $branch) -> $dest"
    git clone --depth 1 --branch "$branch" "$repo_url" "$dest"
  fi
}

install_bin_tools() {
  local src_dir="$1"
  local required=(
    wg-client
    wg-client-single
    wg-panel-admin
    wg-client-rotate-keys
    wg-client-import-existing
  )
  mkdir -p /usr/local/bin
  local tool missing=0
  for tool in "${required[@]}"; do
    if [[ ! -f "$src_dir/$tool" ]]; then
      warn "Missing tool in repo: $src_dir/$tool"
      missing=1
      continue
    fi
    install -m 755 "$src_dir/$tool" "/usr/local/bin/$tool"
    log "Installed /usr/local/bin/$tool"
  done
  if [[ "$missing" -eq 1 ]]; then
    warn "Some CLI tools are missing from the repo."
    warn "Copy wg-client (and others) into client-panel/bin/ before production deploy."
  fi
}

ensure_wg_dirs() {
  mkdir -p /etc/wireguard/{clients,client-state,backups}
  chmod 700 /etc/wireguard /etc/wireguard/clients /etc/wireguard/client-state
}

write_env_file() {
  local path="$1"
  shift
  umask 077
  : > "$path"
  while [[ $# -ge 2 ]]; do
    printf '%s=%q\n' "$1" "$2" >> "$path"
    shift 2
  done
  chmod 600 "$path"
  log "Wrote $path"
}
