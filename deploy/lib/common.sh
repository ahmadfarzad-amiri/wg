#!/usr/bin/env bash
# Shared helpers for WireGuard panel deployment scripts.
# Callers enable strict mode (set -euo pipefail) after bootstrap.

_DEPLOY_LIB="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
if [[ -f "$_DEPLOY_LIB/../repo.conf" ]]; then
  # shellcheck source=../repo.conf
  source "$_DEPLOY_LIB/../repo.conf"
fi

GITHUB_OWNER="${GITHUB_OWNER:-ahmadfarzad-amiri}"
GITHUB_REPO_NAME="${GITHUB_REPO_NAME:-wg}"
GITHUB_BRANCH="${GITHUB_BRANCH:-main}"
GITHUB_REPO_URL="${GITHUB_REPO_URL:-https://github.com/${GITHUB_OWNER}/${GITHUB_REPO_NAME}.git}"
# jsDelivr CDN mirrors raw.githubusercontent.com and works where GitHub is blocked (e.g. Iran).
# Override with WG_RAW_BASE if you need a different mirror.
GITHUB_RAW_BASE="${GITHUB_RAW_BASE:-https://cdn.jsdelivr.net/gh/${GITHUB_OWNER}/${GITHUB_REPO_NAME}@${GITHUB_BRANCH}}"

log() { printf '[wg-deploy] %s\n' "$*"; }
warn() { printf '[wg-deploy] WARN: %s\n' "$*" >&2; }
die() { printf '[wg-deploy] ERROR: %s\n' "$*" >&2; exit 1; }

require_root() {
  [[ "$(id -u)" -eq 0 ]] || die "Run as root: sudo bash $0"
}

require_exit_server() {
  if [[ -f /etc/wireguard/entry-server.env ]] && [[ ! -f /etc/wireguard/exit-server.env ]]; then
    die "This command must run on the EXIT server (found entry-server.env only). add-entry-peer.sh links the entry tunnel peer on exit."
  fi
}

require_entry_server() {
  if [[ -f /etc/wireguard/exit-server.env ]] && [[ ! -f /etc/wireguard/entry-server.env ]]; then
    die "This command must run on the ENTRY server (found exit-server.env only)."
  fi
}

server_role() {
  if [[ -f /etc/wireguard/entry-server.env ]]; then
    printf 'entry'
  elif [[ -f /etc/wireguard/exit-server.env ]]; then
    printf 'exit'
  else
    printf 'unknown'
  fi
}

_have_tty() {
  [[ -e /dev/tty && -r /dev/tty && -w /dev/tty ]]
}

_prompt_show() {
  local text="$1"
  if _have_tty; then
    printf '%s' "$text" >/dev/tty
  else
    printf '[wg-deploy] %s\n' "$text"
  fi
}

_read_line() {
  local __var="$1"
  local __line=""
  if _have_tty; then
    IFS= read -r __line </dev/tty 2>/dev/null || true
  else
    IFS= read -r __line || true
  fi
  printf -v "$__var" '%s' "$__line"
}

_read_secret() {
  local __var="$1"
  local __line=""
  if _have_tty; then
    IFS= read -r -s __line </dev/tty 2>/dev/null || true
    printf '\n' >/dev/tty
  else
    IFS= read -r -s __line || true
    printf '\n'
  fi
  printf -v "$__var" '%s' "$__line"
}

prompt() {
  local var_name="$1"
  local message="$2"
  local default="${3:-}"
  local value=""
  if [[ -n "$default" ]]; then
    _prompt_show "$message [$default]: "
    _read_line value
    value="${value:-$default}"
  else
    if ! _have_tty; then
      die "No terminal for required input: $message"
    fi
    _prompt_show "$message: "
    _read_line value
    while [[ -z "$value" ]]; do
      _prompt_show "$message: "
      _read_line value
    done
  fi
  printf -v "$var_name" '%s' "$value"
}

# Like prompt(), but Enter without typing keeps empty (optional fields).
prompt_optional() {
  local var_name="$1"
  local message="$2"
  local default="${3:-}"
  local value=""
  if [[ -n "$default" ]]; then
    _prompt_show "$message [$default]: "
  else
    _prompt_show "$message (optional, Enter to skip): "
  fi
  _read_line value
  value="${value:-$default}"
  printf -v "$var_name" '%s' "$value"
}

prompt_secret() {
  local var_name="$1"
  local message="$2"
  local value=""
  _prompt_show "$message: "
  _read_secret value
  while [[ -z "$value" ]]; do
    _prompt_show "$message: "
    _read_secret value
  done
  printf -v "$var_name" '%s' "$value"
}

prompt_yes_no() {
  local var_name="$1"
  local message="$2"
  local default="${3:-N}"
  local value=""
  _prompt_show "$message [y/N]: "
  _read_line value
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

clean_stale_panel_nginx() {
  local domain="${1:-}"
  local f base
  shopt -s nullglob
  for f in /etc/nginx/sites-enabled/wg-panels-le-ssl.conf \
    /etc/nginx/sites-available/wg-panels-le-ssl.conf; do
    rm -f "$f"
  done
  if [[ -n "$domain" ]]; then
    for base in \
      "/etc/nginx/sites-enabled/${domain}" \
      "/etc/nginx/sites-enabled/${domain}.conf" \
      "/etc/nginx/sites-available/${domain}" \
      "/etc/nginx/sites-available/${domain}.conf"; do
      rm -f "$base"
    done
  fi
}

install_panel_nginx() {
  local template="$1"
  local out="$2"
  local domain="$3"
  local client_port="$4"
  local admin_port="$5"
  clean_stale_panel_nginx "$domain"
  render_template "$template" "$out" \
    __PANEL_DOMAIN__ "$domain" \
    __CLIENT_PORT__ "$client_port" \
    __ADMIN_PORT__ "$admin_port"
  if [[ -n "${6:-}" && -n "${7:-}" && -f "${6}" && -f "${7}" ]]; then
    nginx_ssl_server_block "$domain" "$6" "$7" "$client_port" "$admin_port" >> "$out"
  elif [[ -n "${6:-}" || -n "${7:-}" ]]; then
    warn "Skipping nginx HTTPS block — certificate files not found yet"
  fi
}

nginx_reload_or_start() {
  if systemctl is-active --quiet nginx 2>/dev/null; then
    systemctl reload nginx
  else
    systemctl start nginx
  fi
}

install_certbot_https() {
  local domain="$1"
  local email="$2"
  log "Installing certbot and requesting Let's Encrypt certificate for ${domain}..."
  if command -v apt-get >/dev/null 2>&1; then
    install_packages certbot python3-certbot-nginx
  elif command -v dnf >/dev/null 2>&1; then
    dnf install -y certbot python3-certbot-nginx 2>/dev/null || dnf install -y certbot
  elif command -v yum >/dev/null 2>&1; then
    yum install -y certbot python3-certbot-nginx 2>/dev/null || yum install -y certbot
  else
    warn "Install certbot manually, then run: certbot --nginx -d ${domain}"
    return 1
  fi
  if certbot --nginx -d "$domain" --non-interactive --agree-tos -m "$email" --redirect; then
    log "HTTPS enabled for ${domain}"
    return 0
  fi
  warn "certbot failed — ensure DNS for ${domain} points to this server, then run:"
  warn "  certbot --nginx -d ${domain}"
  return 1
}

load_deploy_bootstrap() {
  source_deploy_lib "${1:-}"
}

default_route_iface() {
  ip route show default 2>/dev/null | awk '{print $5; exit}'
}

_is_public_ipv4() {
  local ip="$1"
  [[ -n "$ip" && "$ip" != "127.0.0.1" ]] || return 1
  # Skip RFC1918, link-local, and CGNAT — common on VPS where the primary iface is private.
  [[ "$ip" =~ ^10\. ]] && return 1
  [[ "$ip" =~ ^172\.(1[6-9]|2[0-9]|3[0-1])\. ]] && return 1
  [[ "$ip" =~ ^192\.168\. ]] && return 1
  [[ "$ip" =~ ^169\.254\. ]] && return 1
  [[ "$ip" =~ ^100\.(6[4-9]|[7-9][0-9]|1[01][0-9]|12[0-7])\. ]] && return 1
  return 0
}

detect_public_ip() {
  local ip=""

  # Prefer a routable address on a local iface; fall through if only private IPs exist.
  while IFS= read -r ip; do
    if _is_public_ipv4 "$ip"; then
      printf '%s' "$ip"
      return 0
    fi
  done < <(ip -4 -o addr show scope global 2>/dev/null | awk '{print $4}' | cut -d/ -f1)

  while IFS= read -r ip; do
    if _is_public_ipv4 "$ip"; then
      printf '%s' "$ip"
      return 0
    fi
  done < <(hostname -I 2>/dev/null | tr ' ' '\n')

  # External lookup with a hard cap (curl alone can hang on DNS).
  if command -v timeout >/dev/null 2>&1; then
    ip="$(timeout 6 bash -c '
      curl -4fsS --connect-timeout 2 --max-time 3 https://ifconfig.me 2>/dev/null ||
      curl -4fsS --connect-timeout 2 --max-time 3 https://api.ipify.org 2>/dev/null
    ' 2>/dev/null || true)"
    ip="${ip//$'\n'/}"
    if [[ -n "$ip" ]]; then
      printf '%s' "$ip"
      return 0
    fi
  else
    ip="$(curl -4fsS --connect-timeout 2 --max-time 3 https://ifconfig.me 2>/dev/null || true)"
    if [[ -n "$ip" ]]; then
      printf '%s' "$ip"
      return 0
    fi
  fi

  printf '%s' "127.0.0.1"
}

should_prompt() {
  [[ "${WG_INSTALL_INTERACTIVE:-0}" == "1" ]] && _have_tty
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
  if command -v wg >/dev/null 2>&1 && command -v wg-quick >/dev/null 2>&1; then
    log "WireGuard tools already installed"
    return 0
  fi

  log "Installing WireGuard and dependencies..."
  if command -v apt-get >/dev/null 2>&1; then
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    apt-get install -y -qq curl ca-certificates iproute2 iptables wireguard wireguard-tools \
      || apt-get install -y -qq curl ca-certificates iproute2 iptables wireguard-tools
  elif command -v dnf >/dev/null 2>&1; then
    dnf install -y curl wireguard-tools iptables iproute2 \
      || dnf install -y curl wireguard-tools
  elif command -v yum >/dev/null 2>&1; then
    yum install -y curl wireguard-tools iptables iproute2 \
      || yum install -y curl wireguard-tools
  else
    die "Unsupported package manager. Install wireguard-tools manually, then re-run."
  fi

  command -v wg >/dev/null 2>&1 \
    || die "Could not install wg. Try: apt-get install -y wireguard wireguard-tools"
  command -v wg-quick >/dev/null 2>&1 \
    || die "Could not install wg-quick. Try: apt-get install -y wireguard-tools"
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
  # jsDelivr works where raw.githubusercontent.com is blocked (Iran, etc.)
  GITHUB_RAW_BASE="${GITHUB_RAW_BASE:-https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@main}"
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

_git_clone_with_fallback() {
  local repo_url="$1" branch="$2" dest="$3"
  # Keep each attempt short — hung mirrors used to burn minutes during install.
  local clone_timeout="${WG_GIT_CLONE_TIMEOUT:-5}"

  _git_clone_once() {
    local url="$1"
    if command -v timeout >/dev/null 2>&1; then
      GIT_TERMINAL_PROMPT=0 timeout "$clone_timeout" \
        git -c http.version=HTTP/1.1 \
        -c http.lowSpeedLimit=1000 -c http.lowSpeedTime=3 \
        clone --depth 1 --branch "$branch" --single-branch "$url" "$dest" 2>/dev/null
    else
      GIT_TERMINAL_PROMPT=0 \
        git -c http.version=HTTP/1.1 \
        -c http.lowSpeedLimit=1000 -c http.lowSpeedTime=3 \
        clone --depth 1 --branch "$branch" --single-branch "$url" "$dest" 2>/dev/null
    fi
  }

  # Order: direct → gh-proxy (when GitHub is blocked).
  local gh_path
  gh_path="$(echo "$repo_url" | sed 's|.*github\.com/||')"
  local url
  for url in \
    "$repo_url" \
    "https://gh-proxy.com/https://github.com/${gh_path}"; do
    if [[ "$url" == "$repo_url" ]]; then
      log "Trying direct clone (timeout ${clone_timeout}s)"
    else
      log "Trying proxy: $url (timeout ${clone_timeout}s)"
    fi
    rm -rf "$dest" 2>/dev/null || true
    if _git_clone_once "$url"; then
      [[ "$url" != "$repo_url" ]] && log "Cloned via proxy: $url"
      return 0
    fi
  done

  warn "All git clone attempts failed. Options:"
  warn "  Set WG_GITHUB_REPO to a reachable proxy:"
  warn "    WG_GITHUB_REPO='https://gh-proxy.com/https://github.com/${gh_path}'"
  return 1
}

clone_or_update_repo() {
  local repo_url="$1"
  local branch="$2"
  local dest="$3"
  if [[ -d "$dest/.git" ]]; then
    log "Updating existing repo at $dest"
    if ! git -C "$dest" fetch origin "$branch" 2>/dev/null; then
      warn "git fetch failed (GitHub may be blocked) — skipping update, using existing code"
      return 0
    fi
    git -C "$dest" checkout "$branch"
    git -C "$dest" pull --ff-only origin "$branch"
  else
    log "Cloning $repo_url (branch $branch) -> $dest"
    _git_clone_with_fallback "$repo_url" "$branch" "$dest"
  fi
}

clone_repo_if_needed() {
  local dest="$1"
  local repo_url="${WG_GITHUB_REPO:-$GITHUB_REPO_URL}"
  local branch="${WG_GITHUB_BRANCH:-$GITHUB_BRANCH}"
  if [[ -f "$dest/client-panel/bin/wg-client" ]]; then
    log "Using existing repo at $dest"
    return 0
  fi
  install_packages git curl
  clone_or_update_repo "$repo_url" "$branch" "$dest"
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

# Install operator CLI + cache deploy scripts under /opt/wg-ops (does not clash with native `wg`).
install_wg_ops() {
  local deploy_dir="${1:-}"
  local ops_dir="${WG_OPS_DIR:-/opt/wg-ops}"
  local bin_path="${WG_OPS_BIN:-/usr/local/bin/wg-ops}"
  mkdir -p "$ops_dir/lib" /usr/local/bin

  # Full local deploy tree (repo checkout): copy everything.
  if [[ -n "$deploy_dir" \
    && -f "$deploy_dir/wg-ops" \
    && -f "$deploy_dir/lib/common.sh" \
    && -f "$deploy_dir/test-connectivity.sh" \
    && -f "$deploy_dir/diagnose-vpn.sh" ]]; then
    rsync -a --delete \
      --exclude='.git' \
      --exclude='__pycache__' \
      --exclude='*.pyc' \
      "$deploy_dir/" "$ops_dir/"
    install -m 755 "$deploy_dir/wg-ops" "$bin_path"
    log "Installed $bin_path (scripts in $ops_dir)"
    return 0
  fi

  # Bootstrap CLI, then pull the full script set from CDN/Git.
  if [[ -n "$deploy_dir" && -f "$deploy_dir/wg-ops" ]]; then
    install -m 755 "$deploy_dir/wg-ops" "$bin_path"
  elif command -v curl >/dev/null 2>&1; then
    curl -fsSL "${GITHUB_RAW_BASE}/deploy/wg-ops" -o "$bin_path"
    chmod 755 "$bin_path"
  else
    warn "wg-ops not installed (no local deploy tree and no curl)"
    return 0
  fi

  if WG_OPS_DIR="$ops_dir" WG_OPS_BIN="$bin_path" WG_RAW_BASE="${GITHUB_RAW_BASE}" \
    bash "$bin_path" pull; then
    log "Installed $bin_path (scripts in $ops_dir)"
  else
    warn "wg-ops CLI installed but pull failed — run: sudo wg-ops pull"
  fi
}

ensure_wg_dirs() {
  mkdir -p /etc/wireguard/{clients,client-state,backups}
  chmod 700 /etc/wireguard /etc/wireguard/clients /etc/wireguard/client-state
}

wg_exit_tunnel_routes_down() {
  local client_cidr="${1:-10.10.10.0/24}"
  local tunnel_peer_ip="${2:-10.200.0.2/32}"
  local tunnel_if="${3:-wg-tunnel}"
  ip route del "$client_cidr" dev "$tunnel_if" 2>/dev/null || true
  ip route del "$tunnel_peer_ip" dev "$tunnel_if" 2>/dev/null || true
}

wg_exit_tunnel_routes_up() {
  local client_cidr="${1:-10.10.10.0/24}"
  local tunnel_peer_ip="${2:-10.200.0.2/32}"
  local tunnel_if="${3:-wg-tunnel}"
  if ! ip link show "$tunnel_if" >/dev/null 2>&1; then
    warn "Exit routes skipped — $tunnel_if is not up"
    return 1
  fi
  ip route replace "$client_cidr" dev "$tunnel_if"
  ip route replace "$tunnel_peer_ip" dev "$tunnel_if"
}

wg_exit_route_to_client_ok() {
  local sample_ip="${1:-10.10.10.2}"
  local tunnel_if="${2:-wg-tunnel}"
  ip route get "$sample_ip" 2>/dev/null | grep -q "dev ${tunnel_if}"
}

tunnel_handshake_recent() {
  local max_age="${1:-180}"
  local tunnel_if="${2:-wg-tunnel}"
  local now hs age
  now="$(date +%s)"
  # Use newest handshake across all peers (ignore stale/zero peers listed first).
  hs="$(wg show "$tunnel_if" latest-handshakes 2>/dev/null \
    | awk 'NF >= 2 { t = $NF + 0; if (t > max) max = t } END { print max + 0 }')"
  hs="${hs:-0}"
  age=$((now - hs))
  [[ "$hs" -gt 0 && "$age" -le "$max_age" ]]
}

ensure_wg_conf_permissions() {
  local f
  for f in /etc/wireguard/*.conf; do
    [[ -f "$f" ]] || continue
    chmod 600 "$f"
  done
}

wg_entry_tunnel_routes_down() {
  local client_cidr="${1:-10.10.10.0/24}"
  local tunnel_if="${2:-wg-tunnel}"
  ip rule del from "$client_cidr" lookup 100 priority 100 2>/dev/null || true
  ip route del default dev "$tunnel_if" table 100 2>/dev/null || true
}

wg_entry_tunnel_routes_up() {
  local client_cidr="${1:-10.10.10.0/24}"
  local tunnel_if="${2:-wg-tunnel}"
  ip rule del from "$client_cidr" lookup 100 priority 100 2>/dev/null || true
  ip rule add from "$client_cidr" lookup 100 priority 100
  ip route del default dev "$tunnel_if" table 100 2>/dev/null || true
  ip route add default dev "$tunnel_if" table 100
}

wg_entry_client_subnet_route_up() {
  local client_cidr="${1:-10.10.10.0/24}"
  local client_if="${2:-wg-clients}"
  if ! ip link show "$client_if" >/dev/null 2>&1; then
    warn "Client subnet route skipped — $client_if is not up"
    return 1
  fi
  ip route replace "$client_cidr" dev "$client_if" scope link
}

wg_entry_client_subnet_route_ok() {
  local sample_ip="${1:-10.10.10.2}"
  local client_if="${2:-wg-clients}"
  ip route get "$sample_ip" 2>/dev/null | grep -q "dev ${client_if}"
}

ensure_entry_client_postup_in_conf() {
  # Ensure wg-clients PostUp is route-only (FORWARD rules live in wg-tunnel PostUp).
  local conf="${1:-/etc/wireguard/wg-clients.conf}"
  local client_if="${2:-wg-clients}"
  local client_cidr="${3:-10.10.10.0/24}"
  local needs_rewrite=0
  [[ -f "$conf" ]] || return 0
  if grep -qE 'PostUp = .*iptables .*FORWARD' "$conf" 2>/dev/null; then
    needs_rewrite=1
  elif ! grep -q 'ip route replace' "$conf" 2>/dev/null; then
    needs_rewrite=1
  fi
  [[ "$needs_rewrite" == "1" ]] || return 0
  awk -v cif="$client_if" -v cidr="$client_cidr" '
    BEGIN { posted=0 }
    /^PostUp[[:space:]]*=/ { next }
    /^PostDown[[:space:]]*=/ { next }
    /^Address[[:space:]]*=/ && !posted {
      print
      print "PostUp = ip route replace " cidr " dev " cif " scope link"
      print "PostDown = ip route del " cidr " dev " cif " scope link 2>/dev/null || true"
      posted=1
      next
    }
    { print }
    END {
      if (!posted) {
        print "PostUp = ip route replace " cidr " dev " cif " scope link"
        print "PostDown = ip route del " cidr " dev " cif " scope link 2>/dev/null || true"
      }
    }
  ' "$conf" > "${conf}.tmp"
  chmod 600 "${conf}.tmp"
  mv "${conf}.tmp" "$conf"
  log "Normalized client subnet route PostUp in $conf (FORWARD belongs on wg-tunnel)"
}

wg_entry_forward_rules_up() {
  local client_if="${1:-wg-clients}"
  local tunnel_if="${2:-wg-tunnel}"
  local def_if
  def_if="$(default_route_iface)"
  def_if="${def_if:-eth0}"

  # Narrow path only: client ↔ tunnel. Do not ACCEPT all wg-clients forwards
  # (that allows accidental WAN egress when policy routing is missing).
  wg_iptables_ensure FORWARD -i "$client_if" -o "$tunnel_if" -j ACCEPT
  # Stateful RELATED,ESTABLISHED alone breaks UDP/DNS return with policy routing.
  wg_iptables_delete_all FORWARD -i "$tunnel_if" -o "$client_if" -m state --state RELATED,ESTABLISHED -j ACCEPT
  wg_iptables_ensure FORWARD -i "$tunnel_if" -o "$client_if" -j ACCEPT

  # Remove broad ACCEPT rules that would bypass the narrow path.
  wg_iptables_delete_all FORWARD -i "$client_if" -j ACCEPT
  wg_iptables_delete_all FORWARD -o "$client_if" -j ACCEPT

  # Anti-leak: drop client→WAN unless a higher-priority ACCEPT exists (direct mode).
  # Direct-mode rules are inserted at priority via wg-client apply_direct_routing_for_ip.
  if [[ "${WG_ENTRY_ANTILEAK:-1}" != "0" && -n "$def_if" ]]; then
    wg_iptables_ensure FORWARD -i "$client_if" -o "$def_if" -j DROP
  fi
}

wg_entry_forward_rules_down() {
  local client_if="${1:-wg-clients}"
  local tunnel_if="${2:-wg-tunnel}"
  local def_if
  def_if="$(default_route_iface)"
  def_if="${def_if:-eth0}"
  wg_iptables_delete_all FORWARD -i "$client_if" -o "$tunnel_if" -j ACCEPT
  wg_iptables_delete_all FORWARD -i "$tunnel_if" -o "$client_if" -j ACCEPT
  wg_iptables_delete_all FORWARD -i "$tunnel_if" -o "$client_if" -m state --state RELATED,ESTABLISHED -j ACCEPT
  wg_iptables_delete_all FORWARD -i "$client_if" -j ACCEPT
  wg_iptables_delete_all FORWARD -o "$client_if" -j ACCEPT
  if [[ -n "$def_if" ]]; then
    wg_iptables_delete_all FORWARD -i "$client_if" -o "$def_if" -j DROP
  fi
}

wg_entry_docker_forward_rules_up() {
  local client_if="${1:-wg-clients}"
  local tunnel_if="${2:-wg-tunnel}"
  if ! iptables -L DOCKER-USER -n >/dev/null 2>&1; then
    return 0
  fi
  # Prefer no Docker on VPN hosts; bypass only if Docker is present.
  wg_iptables_delete_all DOCKER-USER -i "$tunnel_if" -o "$client_if" -j ACCEPT
  wg_iptables_delete_all DOCKER-USER -i "$client_if" -o "$tunnel_if" -j ACCEPT
  iptables -I DOCKER-USER 1 -i "$tunnel_if" -o "$client_if" -j ACCEPT
  iptables -I DOCKER-USER 1 -i "$client_if" -o "$tunnel_if" -j ACCEPT
  log "Docker DOCKER-USER bypass for ${client_if} ↔ ${tunnel_if}"
}

wg_install_docker_forward_systemd() {
  if ! iptables -L DOCKER-USER -n >/dev/null 2>&1; then
    return 0
  fi
  cat > /etc/systemd/system/wg-docker-forward.service <<'EOF'
[Unit]
Description=Allow WireGuard forwarding through Docker DOCKER-USER chain
After=docker.service wg-quick@wg-clients.service wg-quick@wg-tunnel.service
Wants=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/sh -c '\
  C=0; while iptables -D DOCKER-USER -i wg-tunnel -o wg-clients -j ACCEPT 2>/dev/null; do C=1; done; \
  while iptables -D DOCKER-USER -i wg-clients -o wg-tunnel -j ACCEPT 2>/dev/null; do C=1; done; \
  iptables -C DOCKER-USER -i wg-clients -o wg-tunnel -j ACCEPT 2>/dev/null || \
    iptables -I DOCKER-USER 1 -i wg-clients -o wg-tunnel -j ACCEPT; \
  iptables -C DOCKER-USER -i wg-tunnel -o wg-clients -j ACCEPT 2>/dev/null || \
    iptables -I DOCKER-USER 1 -i wg-tunnel -o wg-clients -j ACCEPT'

[Install]
WantedBy=multi-user.target
EOF
  systemctl daemon-reload 2>/dev/null || true
  systemctl enable wg-docker-forward.service 2>/dev/null || true
  systemctl start wg-docker-forward.service 2>/dev/null || true
}

# Idempotent iptables helpers — avoid duplicate rules after wg-quick restart + fix scripts.
# Args: [-t table] CHAIN rule-specification...
_wg_iptables_parse() {
  _WG_IPT_TABLE=()
  if [[ "${1:-}" == "-t" ]]; then
    _WG_IPT_TABLE=("-t" "$2")
    shift 2
  fi
  _WG_IPT_REST=("$@")
}

wg_iptables_has() {
  _wg_iptables_parse "$@"
  iptables "${_WG_IPT_TABLE[@]}" -C "${_WG_IPT_REST[@]}" 2>/dev/null
}

wg_iptables_ensure() {
  _wg_iptables_parse "$@"
  if iptables "${_WG_IPT_TABLE[@]}" -C "${_WG_IPT_REST[@]}" 2>/dev/null; then
    return 0
  fi
  iptables "${_WG_IPT_TABLE[@]}" -A "${_WG_IPT_REST[@]}"
}

wg_iptables_ensure_insert() {
  # Insert at position 1 if missing (high-priority ACCEPT before DROP).
  _wg_iptables_parse "$@"
  if iptables "${_WG_IPT_TABLE[@]}" -C "${_WG_IPT_REST[@]}" 2>/dev/null; then
    return 0
  fi
  iptables "${_WG_IPT_TABLE[@]}" -I "${_WG_IPT_REST[0]}" 1 "${_WG_IPT_REST[@]:1}"
}

wg_iptables_delete_all() {
  _wg_iptables_parse "$@"
  while iptables "${_WG_IPT_TABLE[@]}" -C "${_WG_IPT_REST[@]}" 2>/dev/null; do
    iptables "${_WG_IPT_TABLE[@]}" -D "${_WG_IPT_REST[@]}" || break
  done
}

wg_iptables_count_matches() {
  # Count rules in CHAIN whose iptables-save line matches PATTERN (grep -E).
  local table="${1:-filter}"
  local chain="$2"
  local pattern="$3"
  iptables-save -t "$table" 2>/dev/null \
    | awk -v c="$chain" '($1=="-" || $1=="-A") && $2==c {print}' \
    | grep -E "$pattern" \
    | wc -l \
    | tr -d ' '
}

wg_apply_ip_forward() {
  sysctl -w net.ipv4.ip_forward=1 >/dev/null
  # Managed drop-in — avoid fragile unscoped appends to /etc/sysctl.conf.
  cat > /etc/sysctl.d/99-wg-forward.conf <<'EOF'
# Managed by WireGuard VPN install — IPv4 forwarding for two-hop stack
net.ipv4.ip_forward = 1
EOF
  sysctl -p /etc/sysctl.d/99-wg-forward.conf >/dev/null 2>&1 || true
}

wg_server_mtu() {
  # Server WG interface MTU (payload size on wg-clients / wg-tunnel).
  # Default 1420 = 1500 underlay − ~80 bytes headroom (WG ~60 + common VPS overhead).
  echo "${WG_SERVER_MTU:-1420}"
}

wg_tunnel_mtu() {
  # Entry↔exit tunnel may differ from client-facing MTU; defaults to WG_SERVER_MTU.
  echo "${WG_TUNNEL_MTU:-$(wg_server_mtu)}"
}

wg_clients_mtu() {
  echo "${WG_CLIENTS_MTU:-$(wg_server_mtu)}"
}

wg_validate_mtu() {
  local mtu="$1"
  local label="${2:-MTU}"
  if ! [[ "$mtu" =~ ^[0-9]+$ ]]; then
    die "${label} must be an integer (got: ${mtu})"
  fi
  if [[ "$mtu" -lt 1280 || "$mtu" -gt 1500 ]]; then
    die "${label}=${mtu} out of safe range 1280–1500"
  fi
}

wg_apply_mss_clamp() {
  if [[ "${WG_ENABLE_MSS_CLAMP:-1}" == "0" ]]; then
    wg_iptables_delete_all -t mangle FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --clamp-mss-to-pmtu
    return 0
  fi
  # Collapse duplicates to a single clamp-to-PMTU rule.
  wg_iptables_delete_all -t mangle FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --clamp-mss-to-pmtu
  iptables -t mangle -A FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --clamp-mss-to-pmtu
  log "TCP MSS clamp enabled on FORWARD chain (single rule)"
}

wg_install_mss_clamp_systemd() {
  # Persist MSS clamp across reboot (not only until next iptables flush).
  if [[ "${WG_ENABLE_MSS_CLAMP:-1}" == "0" ]]; then
    systemctl disable --now wg-mss-clamp.service 2>/dev/null || true
    rm -f /etc/systemd/system/wg-mss-clamp.service 2>/dev/null || true
    systemctl daemon-reload 2>/dev/null || true
    return 0
  fi
  cat > /etc/systemd/system/wg-mss-clamp.service <<'EOF'
[Unit]
Description=WireGuard TCP MSS clamp on FORWARD (PMTU)
After=network-online.target wg-quick@wg-clients.service wg-quick@wg-tunnel.service
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/sh -c 'while iptables -t mangle -C FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --clamp-mss-to-pmtu 2>/dev/null; do iptables -t mangle -D FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --clamp-mss-to-pmtu; done; iptables -t mangle -A FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --clamp-mss-to-pmtu'
ExecStop=/bin/sh -c 'while iptables -t mangle -D FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --clamp-mss-to-pmtu 2>/dev/null; do :; done'

[Install]
WantedBy=multi-user.target
EOF
  systemctl daemon-reload 2>/dev/null || true
  systemctl enable wg-mss-clamp.service 2>/dev/null || true
  systemctl start wg-mss-clamp.service 2>/dev/null || true
  log "MSS clamp systemd unit enabled (survives reboot)"
}

wg_ensure_mtu_in_conf() {
  local conf="$1"
  local mtu="${2:-$(wg_server_mtu)}"
  [[ -f "$conf" ]] || return 0
  if grep -qE '^[[:space:]]*MTU[[:space:]]*=' "$conf"; then
    sed -i -E "s/^[[:space:]]*MTU[[:space:]]*=.*/MTU = ${mtu}/" "$conf"
  else
    # Insert MTU after Address= in the Interface section.
    awk -v mtu="$mtu" '
      BEGIN { done=0 }
      /^\[Interface\]/ { in_iface=1 }
      /^\[/ && $0 !~ /^\[Interface\]/ { in_iface=0 }
      in_iface && /^Address[[:space:]]*=/ && !done {
        print
        print "MTU = " mtu
        done=1
        next
      }
      { print }
      END {
        if (!done) { }
      }
    ' "$conf" > "${conf}.tmp"
    chmod 600 "${conf}.tmp"
    mv "${conf}.tmp" "$conf"
  fi
}

wg_set_live_mtu() {
  local ifname="$1"
  local mtu="${2:-$(wg_server_mtu)}"
  if ip link show "$ifname" >/dev/null 2>&1; then
    ip link set dev "$ifname" mtu "$mtu" 2>/dev/null || true
  fi
}

wg_apply_server_mtus() {
  local clients_mtu tunnel_mtu
  clients_mtu="$(wg_clients_mtu)"
  tunnel_mtu="$(wg_tunnel_mtu)"
  wg_validate_mtu "$clients_mtu" "WG_CLIENTS_MTU/WG_SERVER_MTU"
  wg_validate_mtu "$tunnel_mtu" "WG_TUNNEL_MTU"
  if [[ -f /etc/wireguard/wg-clients.conf ]]; then
    wg_ensure_mtu_in_conf /etc/wireguard/wg-clients.conf "$clients_mtu"
    wg_set_live_mtu wg-clients "$clients_mtu"
  fi
  if [[ -f /etc/wireguard/wg-tunnel.conf ]]; then
    wg_ensure_mtu_in_conf /etc/wireguard/wg-tunnel.conf "$tunnel_mtu"
    wg_set_live_mtu wg-tunnel "$tunnel_mtu"
  fi
  log "Server WireGuard MTU: wg-clients=${clients_mtu} wg-tunnel=${tunnel_mtu}"
}

wg_bbr_available() {
  [[ -d /sys/module/tcp_bbr ]] && return 0
  modprobe tcp_bbr 2>/dev/null || return 1
  [[ -d /sys/module/tcp_bbr ]]
}

wg_apply_performance_sysctl() {
  if [[ "${WG_ENABLE_BBR:-1}" == "0" ]]; then
    log "Performance sysctl skipped (WG_ENABLE_BBR=0)"
    return 0
  fi
  local sysctl_file="/etc/sysctl.d/99-wg-performance.conf"
  local bbr_line="# BBR unavailable on this kernel — left at system default"
  local qdisc_line="net.core.default_qdisc = fq"
  if wg_bbr_available; then
    bbr_line="net.ipv4.tcp_congestion_control = bbr"
  else
    warn "tcp_bbr not available — skipping BBR (buffers still applied)"
    qdisc_line="# net.core.default_qdisc left unchanged (no BBR)"
  fi

  # Set socket *max* buffers high; do not raise *default* (wastes RAM on small VPS).
  # TCP buffer triples are min/default/max. Conntrack only if nf_conntrack is loaded.
  cat > "$sysctl_file" <<EOF
# Managed by WireGuard VPN — two-hop throughput tuning
${qdisc_line}
${bbr_line}
net.core.rmem_max = 67108864
net.core.wmem_max = 67108864
net.ipv4.tcp_rmem = 4096 87380 67108864
net.ipv4.tcp_wmem = 4096 65536 67108864
net.core.netdev_max_backlog = 25000
net.core.somaxconn = 4096
net.ipv4.udp_rmem_min = 8192
net.ipv4.udp_wmem_min = 8192
EOF
  if [[ -e /proc/sys/net/netfilter/nf_conntrack_max ]] \
    || modprobe nf_conntrack 2>/dev/null; then
    cat >> "$sysctl_file" <<'EOF'
net.netfilter.nf_conntrack_max = 262144
net.netfilter.nf_conntrack_buckets = 65536
EOF
  fi
  sysctl -p "$sysctl_file" 2>/dev/null || sysctl --system 2>/dev/null || true
  log "Performance sysctl applied (UDP/TCP max buffers 64MB; BBR if available)"
}

wg_apply_vpn_performance() {
  wg_apply_mss_clamp
  wg_install_mss_clamp_systemd
  wg_apply_performance_sysctl
  wg_apply_server_mtus
}

wg_performance_enabled() {
  [[ "${WG_ENABLE_BBR:-1}" != "0" ]]
}

wg_apply_rp_filter_for_wg() {
  # Entry VPN router: asymmetric paths (policy routing + tunnel return) need rp_filter off.
  # Do NOT set this in wg-quick PostUp — some hosts block /proc writes from PostUp and
  # wg-quick rolls the interface back down on PostUp failure.
  local sysctl_file="/etc/sysctl.d/99-z-wg-entry-vpn.conf"
  local fwd_conf="/etc/sysctl.d/99-wireguard-forward.conf"
  cat > "$sysctl_file" <<'EOF'
# WireGuard entry server — allow asymmetric forward paths (client ↔ tunnel ↔ exit).
# Filename 99-z-* loads after 99-wireguard-forward.conf on some hosts.
net.ipv4.conf.all.rp_filter = 0
net.ipv4.conf.default.rp_filter = 0
EOF
  rm -f /etc/sysctl.d/99-wg-entry-vpn.conf 2>/dev/null || true
  if [[ -f "$fwd_conf" ]] && grep -q 'rp_filter' "$fwd_conf"; then
    sed -i 's/^[[:space:]]*net\.ipv4\.conf\..*\.rp_filter[[:space:]]*=.*$/# & (disabled — breaks VPN return path)/' "$fwd_conf"
    log "Neutralized rp_filter entries in $fwd_conf"
  fi
  sysctl -p "$sysctl_file" 2>/dev/null || sysctl --system 2>/dev/null || true
  wg_install_rp_filter_systemd_hooks
  wg_set_wg_rp_filter_now
}

wg_set_wg_rp_filter_now() {
  local iface
  for iface in wg-clients wg-tunnel; do
    if [[ -d "/proc/sys/net/ipv4/conf/${iface}" ]]; then
      echo 0 > "/proc/sys/net/ipv4/conf/${iface}/rp_filter" 2>/dev/null || true
    fi
  done
}

wg_install_rp_filter_systemd_hooks() {
  # ExecStartPost runs as root outside wg-quick PostUp (works when PostUp /proc writes fail).
  # Set rp_filter on both wg interfaces from each unit — no shell loop (systemd expands $i).
  local dropin dir
  for dir in wg-clients wg-tunnel; do
    mkdir -p "/etc/systemd/system/wg-quick@${dir}.service.d"
    cat > "/etc/systemd/system/wg-quick@${dir}.service.d/rpfilter.conf" <<'EOF'
[Service]
ExecStartPost=/bin/sh -c '[ -e /proc/sys/net/ipv4/conf/wg-clients/rp_filter ] && echo 0 > /proc/sys/net/ipv4/conf/wg-clients/rp_filter'
ExecStartPost=/bin/sh -c '[ -e /proc/sys/net/ipv4/conf/wg-tunnel/rp_filter ] && echo 0 > /proc/sys/net/ipv4/conf/wg-tunnel/rp_filter'
EOF
  done
  systemctl daemon-reload 2>/dev/null || true
}

strip_rp_filter_from_wg_postup() {
  local conf="$1"
  [[ -f "$conf" ]] || return 0
  if ! grep -q 'rp_filter' "$conf"; then
    return 0
  fi
  awk '
    /^PostUp = / {
      sub(/; echo 0 > \/proc\/sys\/net\/ipv4\/conf\/[^;]*rp_filter[^;]*; echo 0 > \/proc\/sys\/net\/ipv4\/conf\/[^;]*rp_filter[^;]*/, "")
      sub(/; sysctl -w net\.ipv4\.conf\.[^;]*rp_filter[^;]*; sysctl -w net\.ipv4\.conf\.[^;]*rp_filter[^;]*/, "")
    }
    { print }
  ' "$conf" > "${conf}.tmp"
  chmod 600 "${conf}.tmp"
  mv "${conf}.tmp" "$conf"
  log "Removed rp_filter PostUp hooks from $conf (use /etc/sysctl.d/99-z-wg-entry-vpn.conf)"
}

fix_entry_tunnel_postup_in_conf() {
  local conf="${1:-/etc/wireguard/wg-tunnel.conf}"
  [[ -f "$conf" ]] || return 0
  if grep -q 'RELATED,ESTABLISHED' "$conf"; then
    sed -i \
      's/-i ${TUNNEL_IF} -o ${CLIENT_IF} -m state --state RELATED,ESTABLISHED -j ACCEPT/-i ${TUNNEL_IF} -o ${CLIENT_IF} -j ACCEPT/g' \
      "$conf"
    sed -i \
      's/-i wg-tunnel -o wg-clients -m state --state RELATED,ESTABLISHED -j ACCEPT/-i wg-tunnel -o wg-clients -j ACCEPT/g' \
      "$conf"
    log "Patched $conf (stateless tunnel→client forward)"
  fi
}

strip_wrong_entry_tunnel_peer_block() {
  # add-entry-peer.sh belongs on exit only; if run on entry it adds a useless self-peer block.
  local conf="${1:-/etc/wireguard/wg-tunnel.conf}"
  [[ -f "$conf" ]] || return 0
  if ! grep -q 'BEGIN ENTRY TUNNEL PEER' "$conf"; then
    return 0
  fi
  awk '
    /# BEGIN ENTRY TUNNEL PEER/ { skip=1; next }
    /# END ENTRY TUNNEL PEER/ { skip=0; next }
    !skip { print }
  ' "$conf" > "${conf}.tmp"
  chmod 600 "${conf}.tmp"
  mv "${conf}.tmp" "$conf"
  log "Removed exit-only ENTRY TUNNEL PEER block from $conf"
}

wg_sync_all_client_modes() {
  if command -v wg-client >/dev/null 2>&1; then
    wg-client sync-vpn-modes 2>/dev/null || warn "wg-client sync-vpn-modes failed"
  fi
}

apply_entry_vpn_routing_fix() {
  local client_if="${WG_IF:-wg-clients}"
  local tunnel_if="${WG_TUNNEL_IF:-wg-tunnel}"
  local client_cidr="${WG_CLIENT_CIDR:-10.10.10.0/24}"
  wg_apply_ip_forward
  wg_entry_docker_forward_rules_up "$client_if" "$tunnel_if"
  wg_entry_forward_rules_up "$client_if" "$tunnel_if"
  wg_entry_tunnel_routes_up "$client_cidr" "$tunnel_if"
  wg_entry_client_subnet_route_up "$client_cidr" "$client_if"
  strip_wrong_entry_tunnel_peer_block "/etc/wireguard/${tunnel_if}.conf"
  strip_rp_filter_from_wg_postup "/etc/wireguard/${tunnel_if}.conf"
  strip_rp_filter_from_wg_postup "/etc/wireguard/${client_if}.conf"
  fix_entry_tunnel_postup_in_conf "/etc/wireguard/${tunnel_if}.conf"
  ensure_entry_client_postup_in_conf "/etc/wireguard/${client_if}.conf" "$client_if" "$client_cidr"
  wg_apply_rp_filter_for_wg
  wg_install_docker_forward_systemd
  wg_apply_vpn_performance
  ensure_wg_conf_permissions

  if wg_entry_client_subnet_route_ok "10.10.10.2" "$client_if"; then
    log "Entry routing fix applied (${client_cidr} → ${client_if}, egress via ${tunnel_if})"
  else
    warn "Entry: ip route get 10.10.10.2 still does not use ${client_if} — provider may inject a conflicting route; try: ip route replace ${client_cidr} dev ${client_if} scope link"
  fi
  wg_sync_all_client_modes
}

apply_exit_vpn_routing_fix() {
  local tunnel_if="${WG_TUNNEL_IF:-wg-tunnel}"
  local client_cidr="${WG_CLIENT_CIDR:-10.10.10.0/24}"
  local tunnel_peer_ip="${WG_TUNNEL_PEER_IP:-10.200.0.2/32}"
  local def_if
  def_if="$(default_route_iface)"
  def_if="${def_if:-eth0}"

  wg_apply_ip_forward
  # Collapse duplicate NAT / FORWARD rules from older PostUp + fix runs.
  wg_iptables_delete_all -t nat POSTROUTING -s "$client_cidr" -o "$def_if" -j MASQUERADE
  iptables -t nat -A POSTROUTING -s "$client_cidr" -o "$def_if" -j MASQUERADE
  wg_iptables_delete_all FORWARD -i "$tunnel_if" -j ACCEPT
  wg_iptables_delete_all FORWARD -o "$tunnel_if" -j ACCEPT
  iptables -A FORWARD -i "$tunnel_if" -j ACCEPT
  iptables -A FORWARD -o "$tunnel_if" -j ACCEPT
  wg_exit_tunnel_routes_up "$client_cidr" "$tunnel_peer_ip" "$tunnel_if"
  wg_apply_vpn_performance
  ensure_wg_conf_permissions

  if wg_exit_route_to_client_ok "10.10.10.2" "$tunnel_if"; then
    log "Exit routing fix applied (${client_cidr} → ${tunnel_if}, NAT on ${def_if})"
  else
    warn "Exit: ip route get 10.10.10.2 still does not use ${tunnel_if} — check wg-tunnel peer AllowedIPs"
  fi
}

wg_stop_if() {
  local ifname="$1"
  local conf="/etc/wireguard/${ifname}.conf"
  if [[ -f /etc/wireguard/exit-server.env ]]; then
    if [[ "$ifname" == "wg-tunnel" ]]; then
      wg_exit_tunnel_routes_down
    fi
  elif [[ "$ifname" == "wg-tunnel" ]]; then
    wg_entry_tunnel_routes_down
  fi
  if [[ -f "$conf" ]]; then
    wg-quick down "$ifname" 2>/dev/null || true
  fi
  if [[ -f /etc/wireguard/exit-server.env ]]; then
    if [[ "$ifname" == "wg-tunnel" ]]; then
      wg_exit_tunnel_routes_down
    fi
  elif [[ "$ifname" == "wg-tunnel" ]]; then
    wg_entry_tunnel_routes_down
  fi
  ip link del "$ifname" 2>/dev/null || true
}

wg_quick_up() {
  local conf="$1"
  local ifname="$2"
  [[ -f "$conf" ]] || die "WireGuard config missing: $conf"
  chmod 600 "$conf" 2>/dev/null || true
  wg_stop_if "$ifname"
  log "Starting ${ifname}..."
  wg-quick up "$conf" || die "wg-quick up failed for ${ifname}"
  chmod 600 "$conf" 2>/dev/null || true
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

backup_wg_configs() {
  local label="${1:-manual}"
  ensure_wg_dirs
  local ts dest
  ts="$(date +%Y%m%d-%H%M%S)"
  dest="/etc/wireguard/backups/${ts}-${label}"
  mkdir -p "$dest"
  shopt -s nullglob
  for f in /etc/wireguard/*.conf /etc/wireguard/*.env /etc/wireguard/*.pub \
    /etc/wireguard/admin-panel.json /etc/wireguard/wg-endpoint; do
    [[ -f "$f" ]] && cp -a "$f" "$dest/"
  done
  shopt -u nullglob
  log "Backup saved to $dest"
}

read_admin_password() {
  if [[ -n "${WG_ADMIN_PASS:-}" ]]; then
    ADMIN_PASS="$WG_ADMIN_PASS"
    return 0
  fi
  if [[ -n "${WG_ADMIN_PASS_FILE:-}" && -f "$WG_ADMIN_PASS_FILE" ]]; then
    ADMIN_PASS="$(<"$WG_ADMIN_PASS_FILE")"
    ADMIN_PASS="${ADMIN_PASS//$'\n'/}"
    [[ -n "$ADMIN_PASS" ]] || die "WG_ADMIN_PASS_FILE is empty"
    return 0
  fi
  if should_prompt; then
    prompt_secret ADMIN_PASS "Admin panel password (min 8 chars)"
  else
    die "Set WG_ADMIN_PASS or WG_ADMIN_PASS_FILE for non-interactive install"
  fi
}

require_fresh_install() {
  # Fresh-install only: refuse when managed config already exists.
  local marker="${1:-/etc/wireguard/wg-tunnel.conf}"
  if [[ -f "$marker" ]]; then
    die "Existing install detected (${marker}). This installer supports clean servers only. Uninstall first: sudo WG_UNINSTALL_CONFIRM=yes wg-ops uninstall"
  fi
}

maybe_enable_ufw() {
  if [[ "${WG_UFW_ENABLE:-0}" == "1" ]] && command -v ufw >/dev/null 2>&1; then
    ufw --force enable || true
    log "ufw enabled (WG_UFW_ENABLE=1)"
  fi
}

# Resolve UDP port range for firewall (single port or min:max).
# Set WG_UDP_PORT_RANGE=51820:51830 or WG_UDP_PORT_MIN + WG_UDP_PORT_MAX.
wg_udp_port_range() {
  local min="${WG_UDP_PORT_MIN:-${WG_CLIENT_PORT:-51820}}"
  local max="${WG_UDP_PORT_MAX:-$min}"
  if [[ -n "${WG_UDP_PORT_RANGE:-}" ]]; then
    min="${WG_UDP_PORT_RANGE%%:*}"
    max="${WG_UDP_PORT_RANGE#*:}"
    max="${max:-$min}"
  fi
  printf '%s %s\n' "$min" "$max"
}

wg_ufw_allow_udp_ports() {
  command -v ufw >/dev/null 2>&1 || return 0
  local min max
  read -r min max <<< "$(wg_udp_port_range)"
  if [[ "$min" == "$max" ]]; then
    ufw allow "${min}/udp" comment 'wg udp' 2>/dev/null || ufw allow "${min}/udp" || true
    log "ufw: allowed UDP ${min}"
  else
    ufw allow "${min}:${max}/udp" comment 'wg udp range' 2>/dev/null \
      || ufw allow "${min}:${max}/udp" || true
    log "ufw: allowed UDP ${min}-${max}"
  fi
}

# Fixed ListenPort on entry wg-tunnel (return path from exit); random ports often fail on VPS NAT.
ensure_tunnel_listen_port_in_conf() {
  local conf="${1:-/etc/wireguard/wg-tunnel.conf}"
  local port="${2:-${WG_TUNNEL_LISTEN_PORT:-51822}}"
  [[ -f "$conf" ]] || return 0
  if grep -q '^ListenPort' "$conf"; then
    return 0
  fi
  sed -i "/^\[Interface\]/a ListenPort = ${port}" "$conf"
  log "Set ListenPort = ${port} in ${conf}"
}

wg_conf_private_key() {
  local conf="$1"
  grep -m1 '^PrivateKey' "$conf" 2>/dev/null | cut -d= -f2- | tr -d ' \t'
}

wg_conf_public_key() {
  local priv
  priv="$(wg_conf_private_key "$1")"
  [[ -n "$priv" ]] || return 1
  printf '%s' "$priv" | wg pubkey
}

wg_exit_forward_nat_down() {
  local client_cidr="${1:-10.10.10.0/24}"
  local tunnel_if="${2:-wg-tunnel}"
  local tunnel_peer_ip="${3:-10.200.0.2/32}"
  local def_if
  def_if="$(default_route_iface)"
  def_if="${def_if:-eth0}"
  iptables -t nat -D POSTROUTING -s "$client_cidr" -o "$def_if" -j MASQUERADE 2>/dev/null || true
  iptables -D FORWARD -i "$tunnel_if" -j ACCEPT 2>/dev/null || true
  iptables -D FORWARD -o "$tunnel_if" -j ACCEPT 2>/dev/null || true
  wg_exit_tunnel_routes_down "$client_cidr" "$tunnel_peer_ip" "$tunnel_if"
}

wg_entry_docker_forward_rules_down() {
  local client_if="${1:-wg-clients}"
  local tunnel_if="${2:-wg-tunnel}"
  if ! iptables -L DOCKER-USER -n >/dev/null 2>&1; then
    return 0
  fi
  while iptables -D DOCKER-USER -i "$tunnel_if" -o "$client_if" -j ACCEPT 2>/dev/null; do :; done
  while iptables -D DOCKER-USER -i "$client_if" -o "$tunnel_if" -j ACCEPT 2>/dev/null; do :; done
}

parse_panel_domain_from_nginx() {
  local conf="${1:-/etc/nginx/sites-available/wg-panels.conf}"
  [[ -f "$conf" ]] || return 1
  grep -m1 'server_name' "$conf" 2>/dev/null \
    | sed 's/.*server_name[[:space:]]*//;s/[;].*//' \
    | awk '{ for (i = 1; i <= NF; i++) if ($i != "localhost" && $i != "127.0.0.1") { print $i; exit } }'
}

detect_uninstall_role() {
  local role
  role="$(server_role)"
  if [[ "$role" != "unknown" ]]; then
    printf '%s' "$role"
    return 0
  fi
  if [[ -f /etc/systemd/system/wg-panel.service || -d /opt/wg/admin-panel ]]; then
    printf 'entry'
    return 0
  fi
  if [[ -f /etc/wireguard/wg-tunnel.conf || -f /etc/wireguard/wg-clients.conf ]]; then
    if [[ -f /etc/wireguard/wg-clients.conf ]]; then
      printf 'entry'
    else
      printf 'exit'
    fi
    return 0
  fi
  printf 'unknown'
}

require_uninstall_confirm() {
  if [[ "${WG_UNINSTALL_CONFIRM:-}" == "yes" ]]; then
    return 0
  fi
  local answer=""
  warn "This permanently removes WireGuard VPN, web panels, database, keys, nginx site, and all /etc/wireguard data."
  _prompt_show "Type 'uninstall' to confirm: "
  _read_line answer
  [[ "$answer" == "uninstall" ]] || die "Uninstall cancelled."
}

stop_systemd_unit() {
  local unit="$1"
  systemctl stop "$unit" 2>/dev/null || true
  systemctl disable "$unit" 2>/dev/null || true
}

remove_systemd_unit_file() {
  local path="$1"
  [[ -f "$path" ]] || return 0
  rm -f "$path"
  log "Removed $path"
}

uninstall_wg_systemd_units() {
  local role="$1"
  stop_systemd_unit wg-panel.service
  stop_systemd_unit wg-admin-panel.service
  stop_systemd_unit wg-docker-forward.service
  stop_systemd_unit wg-mss-clamp.service
  stop_systemd_unit wg-client-enforce.timer
  stop_systemd_unit wg-client-enforce.service
  stop_systemd_unit "wg-quick@wg-clients.service"
  stop_systemd_unit "wg-quick@wg-tunnel.service"

  remove_systemd_unit_file /etc/systemd/system/wg-panel.service
  remove_systemd_unit_file /etc/systemd/system/wg-admin-panel.service
  remove_systemd_unit_file /etc/systemd/system/wg-docker-forward.service
  remove_systemd_unit_file /etc/systemd/system/wg-mss-clamp.service
  remove_systemd_unit_file /etc/systemd/system/wg-client-enforce.service
  remove_systemd_unit_file /etc/systemd/system/wg-client-enforce.timer

  local dir
  for dir in wg-clients wg-tunnel; do
    rm -rf "/etc/systemd/system/wg-quick@${dir}.service.d"
  done

  systemctl daemon-reload 2>/dev/null || true
  systemctl reset-failed 2>/dev/null || true
}

uninstall_wg_stop_interfaces() {
  local role="$1"
  if [[ "$role" == "entry" ]]; then
    wg_stop_if wg-clients
    wg_stop_if wg-tunnel
    wg_entry_forward_rules_down wg-clients wg-tunnel
    wg_entry_tunnel_routes_down "${WG_CLIENT_CIDR:-10.10.10.0/24}" wg-tunnel
    wg_entry_docker_forward_rules_down wg-clients wg-tunnel
    ip route del "${WG_CLIENT_CIDR:-10.10.10.0/24}" dev wg-clients scope link 2>/dev/null || true
  else
    wg_stop_if wg-tunnel
    wg_exit_forward_nat_down \
      "${WG_CLIENT_CIDR:-10.10.10.0/24}" \
      "${WG_TUNNEL_IF:-wg-tunnel}" \
      "${WG_TUNNEL_PEER_IP:-10.200.0.2/32}"
  fi
  iptables -t mangle -D FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --clamp-mss-to-pmtu 2>/dev/null || true
}

uninstall_wg_nginx() {
  local domain="${1:-}"
  clean_stale_panel_nginx "$domain"
  rm -f /etc/nginx/sites-available/wg-panels.conf \
    /etc/nginx/sites-enabled/wg-panels.conf \
    /etc/nginx/sites-enabled/wg-panels-le-ssl.conf \
    /etc/nginx/sites-available/wg-panels-le-ssl.conf

  if [[ -f /etc/nginx/sites-available/default && ! -e /etc/nginx/sites-enabled/default ]]; then
    ln -sf /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default
    log "Restored nginx default site"
  fi

  if command -v nginx >/dev/null 2>&1; then
    if nginx -t 2>/dev/null; then
      nginx_reload_or_start
    else
      warn "nginx config test failed after panel site removal — fix /etc/nginx manually"
    fi
  fi
}

uninstall_wg_certbot() {
  local domain="$1"
  [[ -n "$domain" ]] || return 0
  command -v certbot >/dev/null 2>&1 || return 0
  if certbot delete --cert-name "$domain" --non-interactive 2>/dev/null; then
    log "Removed Let's Encrypt certificate for ${domain}"
  else
    warn "Could not delete certbot certificate for ${domain} — run: certbot delete --cert-name ${domain}"
  fi
}

uninstall_wg_ufw_rules() {
  command -v ufw >/dev/null 2>&1 || return 0
  local rule
  for rule in \
    "${WG_CLIENT_PORT:-51820}/udp" \
    "${WG_PANEL_PORT:-8088}/tcp" \
    "${WG_ADMIN_PORT:-8090}/tcp" \
    "${WG_TUNNEL_PORT:-51821}/udp" \
    "80/tcp" "443/tcp"; do
    ufw delete allow "$rule" 2>/dev/null || true
  done
  if [[ -n "${WG_EXIT_IP:-}" && -n "${WG_TUNNEL_PORT:-}" ]]; then
    ufw delete allow from "${WG_EXIT_IP}" to any port "${WG_TUNNEL_PORT}" proto udp 2>/dev/null || true
  fi
  if [[ -n "${WG_ENTRY_PUBLIC_IP:-${WG_EXIT_IP:-}}" && -n "${WG_TUNNEL_PORT:-}" ]]; then
    ufw delete allow from "${WG_ENTRY_PUBLIC_IP:-}" to any port "${WG_TUNNEL_PORT}" proto udp 2>/dev/null || true
  fi
}

uninstall_wg_bin_tools() {
  local tool
  for tool in wg-client wg-client-single wg-panel-admin wg-client-rotate-keys wg-client-import-existing wg-ops; do
    if [[ -f "/usr/local/bin/$tool" ]]; then
      rm -f "/usr/local/bin/$tool"
      log "Removed /usr/local/bin/$tool"
    fi
  done
}

uninstall_xray() {
  stop_systemd_unit xray.service
  remove_systemd_unit_file /etc/systemd/system/xray.service
  systemctl daemon-reload 2>/dev/null || true
  rm -f /etc/nginx/sites-enabled/xray-ws.conf /etc/nginx/sites-available/xray-ws.conf
  if command -v nginx >/dev/null 2>&1 && nginx -t 2>/dev/null; then
    nginx_reload_or_start || true
  fi
  if command -v ufw >/dev/null 2>&1; then
    ufw delete allow 443/tcp 2>/dev/null || true
    ufw delete allow 8388/tcp 2>/dev/null || true
    ufw delete allow 8388/udp 2>/dev/null || true
  fi
  rm -rf /etc/xray /var/log/xray
  # Keep binary unless explicitly requested — shared host tools may use it.
  if [[ "${WG_REMOVE_XRAY_BIN:-0}" == "1" ]]; then
    rm -f /usr/local/bin/xray
    rm -rf /usr/local/share/xray
  fi
  log "Xray removed (/etc/xray, service, nginx ws site)"
}

uninstall_wg_data_dirs() {
  local install_dir="${WG_INSTALL_DIR:-/opt/wg}"
  local repo_dir="${WG_REPO_DIR:-/opt/wg-src}"
  local ops_dir="${WG_OPS_DIR:-/opt/wg-ops}"
  uninstall_xray
  rm -rf "$install_dir" "$repo_dir" "$ops_dir"
  log "Removed $install_dir, $repo_dir, and $ops_dir"
  if [[ -d /etc/wireguard ]]; then
    rm -rf /etc/wireguard
    log "Removed /etc/wireguard"
  fi
  rm -f /etc/sysctl.d/99-z-wg-entry-vpn.conf /etc/sysctl.d/99-wg-entry-vpn.conf
  rm -f /etc/sysctl.d/99-wg-performance.conf
  rm -f /etc/sysctl.d/99-wg-forward.conf
  rm -f /tmp/wg-install-*.sh /tmp/wg-fix-routing-*.sh /tmp/wg-uninstall-*.sh /tmp/wg-tune-perf-*.sh /tmp/wg-diagnose-*.sh 2>/dev/null || true
}

load_uninstall_env() {
  local role="$1"
  if [[ "$role" == "entry" && -f /etc/wireguard/entry-server.env ]]; then
    # shellcheck disable=SC1091
    source /etc/wireguard/entry-server.env
  elif [[ "$role" == "exit" && -f /etc/wireguard/exit-server.env ]]; then
    # shellcheck disable=SC1091
    source /etc/wireguard/exit-server.env
  fi
  if [[ -f /etc/wireguard/wg-endpoint ]]; then
    local ep port
    ep="$(< /etc/wireguard/wg-endpoint)"
    port="${ep##*:}"
    if [[ -n "$port" && "$port" != "$ep" ]]; then
      WG_CLIENT_PORT="${WG_CLIENT_PORT:-$port}"
    fi
  fi
}

# --- Configuration validation (fail early; never partially apply after failure) ---

wg_is_ipv4() {
  local ip="$1"
  [[ "$ip" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]] || return 1
  local o IFS=.
  # shellcheck disable=SC2086
  set -- $ip
  for o in "$@"; do
    [[ "$o" -ge 0 && "$o" -le 255 ]] || return 1
  done
  return 0
}

wg_is_cidr_v4() {
  local cidr="$1"
  local ip="${cidr%/*}"
  local prefix="${cidr#*/}"
  wg_is_ipv4 "$ip" || return 1
  [[ "$prefix" =~ ^[0-9]+$ ]] || return 1
  [[ "$prefix" -ge 0 && "$prefix" -le 32 ]]
}

wg_is_port() {
  local p="$1"
  [[ "$p" =~ ^[0-9]+$ ]] || return 1
  [[ "$p" -ge 1 && "$p" -le 65535 ]]
}

wg_is_wg_pubkey() {
  local key="$1"
  # WireGuard public keys are 32-byte base64 (44 chars, often ending with =).
  [[ "$key" =~ ^[A-Za-z0-9+/]{42,44}={0,2}$ ]]
}

wg_is_iface_name() {
  local name="$1"
  [[ "$name" =~ ^[a-zA-Z0-9_.:-]{1,15}$ ]]
}

wg_require_tool() {
  local tool="$1"
  command -v "$tool" >/dev/null 2>&1 || die "Required tool missing: ${tool}"
}

wg_validate_kernel_wg() {
  if [[ -e /sys/module/wireguard ]]; then
    return 0
  fi
  if modprobe wireguard 2>/dev/null; then
    return 0
  fi
  warn "Kernel wireguard module not loaded — ensure wireguard-tools can start interfaces"
}

wg_validate_exit_install_env() {
  local ip="${WG_EXIT_PUBLIC_IP:-${PUBLIC_IP:-}}"
  local port="${WG_TUNNEL_PORT:-51821}"
  local cidr="${WG_CLIENT_CIDR:-10.10.10.0/24}"
  local mtu="${WG_TUNNEL_MTU:-${WG_SERVER_MTU:-1420}}"

  wg_require_tool wg
  wg_require_tool wg-quick
  wg_require_tool iptables
  wg_require_tool ip
  wg_validate_kernel_wg

  if [[ -n "$ip" && "$ip" != "127.0.0.1" ]]; then
    wg_is_ipv4 "$ip" || die "Invalid WG_EXIT_PUBLIC_IP: ${ip}"
  fi
  wg_is_port "$port" || die "Invalid WG_TUNNEL_PORT: ${port}"
  wg_is_cidr_v4 "$cidr" || die "Invalid WG_CLIENT_CIDR: ${cidr}"
  wg_validate_mtu "$mtu" "WG_TUNNEL_MTU/WG_SERVER_MTU"
}

wg_validate_entry_install_env() {
  local entry_ip="${WG_ENTRY_PUBLIC_IP:-${ENTRY_IP:-}}"
  local exit_ip="${WG_EXIT_PUBLIC_IP:-${EXIT_IP:-}}"
  local exit_pub="${WG_EXIT_TUNNEL_PUB:-${EXIT_TUNNEL_PUB:-}}"
  local exit_port="${WG_EXIT_TUNNEL_PORT:-51821}"
  local client_port="${WG_CLIENT_PORT:-51820}"
  local cidr="${WG_CLIENT_CIDR:-10.10.10.0/24}"
  local server_mtu="${WG_SERVER_MTU:-1420}"
  local client_mtu="${WG_CLIENT_MTU_TWOHOP:-${WG_CLIENT_MTU:-1380}}"

  wg_require_tool wg
  wg_require_tool wg-quick
  wg_require_tool iptables
  wg_require_tool ip
  wg_validate_kernel_wg

  [[ -n "$entry_ip" ]] || die "WG_ENTRY_PUBLIC_IP is required"
  wg_is_ipv4 "$entry_ip" || die "Invalid WG_ENTRY_PUBLIC_IP: ${entry_ip}"
  _is_public_ipv4 "$entry_ip" || warn "WG_ENTRY_PUBLIC_IP ${entry_ip} looks private — clients may not reach it"

  [[ -n "$exit_ip" ]] || die "WG_EXIT_PUBLIC_IP is required"
  wg_is_ipv4 "$exit_ip" || die "Invalid WG_EXIT_PUBLIC_IP: ${exit_ip}"

  [[ -n "$exit_pub" ]] || die "WG_EXIT_TUNNEL_PUB is required"
  wg_is_wg_pubkey "$exit_pub" || die "WG_EXIT_TUNNEL_PUB does not look like a WireGuard public key"

  wg_is_port "$exit_port" || die "Invalid WG_EXIT_TUNNEL_PORT: ${exit_port}"
  wg_is_port "$client_port" || die "Invalid WG_CLIENT_PORT: ${client_port}"
  wg_is_cidr_v4 "$cidr" || die "Invalid WG_CLIENT_CIDR: ${cidr}"
  wg_validate_mtu "$server_mtu" "WG_SERVER_MTU"
  wg_validate_mtu "$client_mtu" "WG_CLIENT_MTU_TWOHOP"

  if [[ "$client_mtu" -gt "$server_mtu" ]]; then
    die "WG_CLIENT_MTU_TWOHOP (${client_mtu}) must be <= WG_SERVER_MTU (${server_mtu})"
  fi
  if [[ "$client_mtu" -gt 1420 ]]; then
    warn "Two-hop client MTU ${client_mtu} is high — expect fragmentation on 1500 underlays"
  fi

  if [[ -n "${WG_DNS:-}" ]]; then
    local dns d
    dns="$(echo "${WG_DNS}" | tr ',' ' ')"
    for d in $dns; do
      d="${d// /}"
      [[ -z "$d" ]] && continue
      wg_is_ipv4 "$d" || die "Invalid DNS address in WG_DNS: ${d}"
    done
  fi
}

wg_check_duplicate_client_addresses() {
  local dir="${1:-/etc/wireguard/clients}"
  [[ -d "$dir" ]] || return 0
  local dup
  dup="$(grep -hE '^Address[[:space:]]*=' "$dir"/*.conf 2>/dev/null \
    | sed 's/.*=[[:space:]]*//;s|/.*||' \
    | sort | uniq -d || true)"
  if [[ -n "$dup" ]]; then
    die "Duplicate client Address values detected: ${dup}"
  fi
}

wg_render_entry_tunnel_postup() {
  local client_if="${1:-wg-clients}"
  local tunnel_if="${2:-wg-tunnel}"
  local client_cidr="${3:-10.10.10.0/24}"
  printf 'iptables -C FORWARD -i %s -o %s -j ACCEPT 2>/dev/null || iptables -A FORWARD -i %s -o %s -j ACCEPT; iptables -C FORWARD -i %s -o %s -j ACCEPT 2>/dev/null || iptables -A FORWARD -i %s -o %s -j ACCEPT; ip rule del from %s lookup 100 priority 100 2>/dev/null || true; ip rule add from %s lookup 100 priority 100; ip route del default dev %s table 100 2>/dev/null || true; ip route add default dev %s table 100\n' \
    "$client_if" "$tunnel_if" "$client_if" "$tunnel_if" \
    "$tunnel_if" "$client_if" "$tunnel_if" "$client_if" \
    "$client_cidr" "$client_cidr" "$tunnel_if" "$tunnel_if"
}
