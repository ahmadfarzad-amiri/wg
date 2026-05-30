#!/usr/bin/env bash
# Shared helpers for WireGuard panel deployment scripts.
set -euo pipefail

_DEPLOY_LIB="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
if [[ -f "$_DEPLOY_LIB/../repo.conf" ]]; then
  # shellcheck source=../repo.conf
  source "$_DEPLOY_LIB/../repo.conf"
fi

GITHUB_OWNER="${GITHUB_OWNER:-ahmadfarzad-amiri}"
GITHUB_REPO_NAME="${GITHUB_REPO_NAME:-wg}"
GITHUB_BRANCH="${GITHUB_BRANCH:-main}"
GITHUB_REPO_URL="${GITHUB_REPO_URL:-https://github.com/${GITHUB_OWNER}/${GITHUB_REPO_NAME}.git}"
GITHUB_RAW_BASE="${GITHUB_RAW_BASE:-https://raw.githubusercontent.com/${GITHUB_OWNER}/${GITHUB_REPO_NAME}/${GITHUB_BRANCH}}"

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

prompt_yes_no() {
  local var_name="$1"
  local message="$2"
  local default="${3:-N}"
  local value=""
  read -r -p "$message [y/N]: " value || true
  value="${value:-$default}"
  if [[ "${value,,}" == "y" || "${value,,}" == "yes" ]]; then
    printf -v "$var_name" '%s' "yes"
  else
    printf -v "$var_name" '%s' "no"
  fi
}

_sed_escape() {
  printf '%s' "$1" | sed 's/[\\/&|]/\\&/g'
}

render_template() {
  local src="$1"
  local dst="$2"
  shift 2
  cp "$src" "$dst"
  while [[ $# -ge 2 ]]; do
    local key="$1"
    local val="$2"
    sed -i "s|$key|$(_sed_escape "$val")|g" "$dst"
    shift 2
  done
}

write_wg_endpoint() {
  local endpoint="$1"
  printf '%s\n' "$endpoint" > /etc/wireguard/wg-endpoint
  chmod 600 /etc/wireguard/wg-endpoint
  log "Wrote /etc/wireguard/wg-endpoint ($endpoint)"
}

nginx_ssl_server_block() {
  local domain="$1"
  local cert="$2"
  local key="$3"
  local client_port="$4"
  local admin_port="$5"
  cat <<EOF
server {
    listen 443 ssl;
    server_name ${domain} localhost 127.0.0.1;

    ssl_certificate ${cert};
    ssl_certificate_key ${key};

    client_max_body_size 10M;

    location = /admin {
        return 301 /admin/;
    }

    location ^~ /admin/ {
        proxy_pass http://127.0.0.1:${admin_port}/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_redirect off;
        proxy_buffering off;
    }

    location / {
        proxy_pass http://127.0.0.1:${client_port};
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_buffering off;
    }
}
EOF
}

install_panel_nginx() {
  local template="$1"
  local out="$2"
  local domain="$3"
  local client_port="$4"
  local admin_port="$5"
  render_template "$template" "$out" \
    __PANEL_DOMAIN__ "$domain" \
    __CLIENT_PORT__ "$client_port" \
    __ADMIN_PORT__ "$admin_port"
  if [[ -n "${6:-}" && -n "${7:-}" ]]; then
    nginx_ssl_server_block "$domain" "$6" "$7" "$client_port" "$admin_port" >> "$out"
  fi
}

install_exit_proxy_nginx() {
  local template="$1"
  local out="$2"
  local domain="$3"
  local inside_ip="$4"
  local client_port="$5"
  local admin_port="$6"
  render_template "$template" "$out" \
    __PROXY_DOMAIN__ "$domain" \
    __INSIDE_PANEL_IP__ "$inside_ip" \
    __CLIENT_PORT__ "$client_port" \
    __ADMIN_PORT__ "$admin_port"
}

load_deploy_bootstrap() {
  source_deploy_lib "${1:-}"
}

default_route_iface() {
  ip route show default 2>/dev/null | awk '{print $5; exit}'
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

install_wg_tools() {
  install_packages curl wireguard wireguard-tools iptables iproute2
  command -v wg >/dev/null 2>&1 || die "WireGuard tools (wg) not found after install"
  command -v wg-quick >/dev/null 2>&1 || die "WireGuard tools (wg-quick) not found after install"
}

fetch_deploy_helper_scripts() {
  local name
  for name in "$@"; do
    if [[ -f "$SCRIPT_DIR/$name" ]]; then
      continue
    fi
    curl -fsSL "$GITHUB_RAW_BASE/deploy/$name" -o "$SCRIPT_DIR/$name"
    chmod +x "$SCRIPT_DIR/$name"
  done
}

source_deploy_lib() {
  local script_ref="${1:-}"
  GITHUB_RAW_BASE="${GITHUB_RAW_BASE:-https://raw.githubusercontent.com/ahmadfarzad-amiri/wg/main}"
  if [[ -n "$script_ref" && -f "$(dirname "$script_ref")/lib/common.sh" ]]; then
    SCRIPT_DIR="$(cd "$(dirname "$script_ref")" && pwd)"
    # shellcheck source=lib/common.sh
    source "$SCRIPT_DIR/lib/common.sh"
    return 0
  fi
  _BOOT="$(mktemp -d)"
  mkdir -p "$_BOOT/deploy/lib"
  curl -fsSL "$GITHUB_RAW_BASE/deploy/repo.conf" -o "$_BOOT/deploy/repo.conf"
  curl -fsSL "$GITHUB_RAW_BASE/deploy/lib/common.sh" -o "$_BOOT/deploy/lib/common.sh"
  SCRIPT_DIR="$_BOOT/deploy"
  # shellcheck source=lib/common.sh
  source "$SCRIPT_DIR/lib/common.sh"
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

clone_repo_if_needed() {
  local dest="$1"
  if [[ -f "$dest/client-panel/bin/wg-client" ]]; then
    log "Using existing repo at $dest"
    return 0
  fi
  prompt GITHUB_REPO "GitHub repo URL" "$GITHUB_REPO_URL"
  prompt GITHUB_BRANCH "Git branch" "$GITHUB_BRANCH"
  install_packages git curl
  clone_or_update_repo "$GITHUB_REPO" "$GITHUB_BRANCH" "$dest"
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
