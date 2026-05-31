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
GITHUB_RAW_BASE="${GITHUB_RAW_BASE:-https://raw.githubusercontent.com/${GITHUB_OWNER}/${GITHUB_REPO_NAME}/${GITHUB_BRANCH}}"

log() { printf '[wg-deploy] %s\n' "$*"; }
warn() { printf '[wg-deploy] WARN: %s\n' "$*" >&2; }
die() { printf '[wg-deploy] ERROR: %s\n' "$*" >&2; exit 1; }

require_root() {
  [[ "$(id -u)" -eq 0 ]] || die "Run as root: sudo bash $0"
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

install_exit_proxy_nginx() {
  # Legacy: panels now run on entry server only. Kept for reference.
  warn "install_exit_proxy_nginx is deprecated — panels run on the entry server."
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

wg_entry_forward_rules_up() {
  local client_if="${1:-wg-clients}"
  local tunnel_if="${2:-wg-tunnel}"
  iptables -C FORWARD -i "$client_if" -o "$tunnel_if" -j ACCEPT 2>/dev/null \
    || iptables -A FORWARD -i "$client_if" -o "$tunnel_if" -j ACCEPT
  # Legacy stateful rule breaks UDP/DNS return traffic with policy routing.
  iptables -D FORWARD -i "$tunnel_if" -o "$client_if" -m state --state RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || true
  iptables -C FORWARD -i "$tunnel_if" -o "$client_if" -j ACCEPT 2>/dev/null \
    || iptables -A FORWARD -i "$tunnel_if" -o "$client_if" -j ACCEPT
}

wg_entry_forward_rules_down() {
  local client_if="${1:-wg-clients}"
  local tunnel_if="${2:-wg-tunnel}"
  iptables -D FORWARD -i "$client_if" -o "$tunnel_if" -j ACCEPT 2>/dev/null || true
  iptables -D FORWARD -i "$tunnel_if" -o "$client_if" -j ACCEPT 2>/dev/null || true
  iptables -D FORWARD -i "$tunnel_if" -o "$client_if" -m state --state RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || true
}

wg_apply_ip_forward() {
  sysctl -w net.ipv4.ip_forward=1
  grep -q '^net.ipv4.ip_forward=1' /etc/sysctl.conf 2>/dev/null \
    || echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf
}

wg_apply_rp_filter_for_wg() {
  # Entry VPN router: asymmetric paths (policy routing + tunnel return) need rp_filter off.
  # Do NOT set this in wg-quick PostUp — some hosts block /proc writes from PostUp and
  # wg-quick rolls the interface back down on PostUp failure.
  local sysctl_file="/etc/sysctl.d/99-wg-entry-vpn.conf"
  cat > "$sysctl_file" <<'EOF'
# WireGuard entry server — allow asymmetric forward paths (client ↔ tunnel ↔ exit).
net.ipv4.conf.all.rp_filter = 0
net.ipv4.conf.default.rp_filter = 0
EOF
  sysctl -p "$sysctl_file" 2>/dev/null || sysctl --system 2>/dev/null || true
  local iface
  for iface in wg-clients wg-tunnel; do
    if [[ -d "/proc/sys/net/ipv4/conf/${iface}" ]]; then
      echo 0 > "/proc/sys/net/ipv4/conf/${iface}/rp_filter" 2>/dev/null || true
    fi
  done
}

strip_rp_filter_from_wg_postup() {
  local conf="$1"
  [[ -f "$conf" ]] || return 0
  if grep -q 'rp_filter' "$conf"; then
    sed -i \
      's|; echo 0 > /proc/sys/net/ipv4/conf/wg-tunnel/rp_filter; echo 0 > /proc/sys/net/ipv4/conf/wg-clients/rp_filter||g; \
       s|; echo 0 > /proc/sys/net/ipv4/conf/${TUNNEL_IF}/rp_filter; echo 0 > /proc/sys/net/ipv4/conf/${CLIENT_IF}/rp_filter||g; \
       s|; sysctl -w net.ipv4.conf.wg-tunnel.rp_filter=0; sysctl -w net.ipv4.conf.wg-clients.rp_filter=0||g; \
       s|; sysctl -w net.ipv4.conf.${TUNNEL_IF}.rp_filter=0; sysctl -w net.ipv4.conf.${CLIENT_IF}.rp_filter=0||g' \
      "$conf"
    log "Removed rp_filter PostUp hooks from $conf (use /etc/sysctl.d/99-wg-entry-vpn.conf)"
  fi
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

apply_entry_vpn_routing_fix() {
  local client_if="${WG_IF:-wg-clients}"
  local tunnel_if="${WG_TUNNEL_IF:-wg-tunnel}"
  local client_cidr="${WG_CLIENT_CIDR:-10.10.10.0/24}"
  wg_apply_ip_forward
  wg_apply_rp_filter_for_wg
  wg_entry_forward_rules_up "$client_if" "$tunnel_if"
  wg_entry_tunnel_routes_up "$client_cidr" "$tunnel_if"
  strip_wrong_entry_tunnel_peer_block "/etc/wireguard/${tunnel_if}.conf"
  strip_rp_filter_from_wg_postup "/etc/wireguard/${tunnel_if}.conf"
  strip_rp_filter_from_wg_postup "/etc/wireguard/${client_if}.conf"
  fix_entry_tunnel_postup_in_conf "/etc/wireguard/${tunnel_if}.conf"
  wg_apply_rp_filter_for_wg
  ensure_wg_conf_permissions
  log "Entry routing fix applied (${client_if} ↔ ${tunnel_if})"
}

apply_exit_vpn_routing_fix() {
  local tunnel_if="${WG_TUNNEL_IF:-wg-tunnel}"
  local client_cidr="${WG_CLIENT_CIDR:-10.10.10.0/24}"
  local tunnel_peer_ip="${WG_TUNNEL_PEER_IP:-10.200.0.2/32}"
  local def_if
  def_if="$(default_route_iface)"
  def_if="${def_if:-eth0}"

  wg_apply_ip_forward
  iptables -t nat -C POSTROUTING -s "$client_cidr" -o "$def_if" -j MASQUERADE 2>/dev/null \
    || iptables -t nat -A POSTROUTING -s "$client_cidr" -o "$def_if" -j MASQUERADE
  iptables -C FORWARD -i "$tunnel_if" -j ACCEPT 2>/dev/null \
    || iptables -A FORWARD -i "$tunnel_if" -j ACCEPT
  iptables -C FORWARD -o "$tunnel_if" -j ACCEPT 2>/dev/null \
    || iptables -A FORWARD -o "$tunnel_if" -j ACCEPT
  wg_exit_tunnel_routes_up "$client_cidr" "$tunnel_peer_ip" "$tunnel_if"
  ensure_wg_conf_permissions

  if wg_exit_route_to_client_ok "10.10.10.2" "$tunnel_if"; then
    log "Exit routing fix applied (${client_cidr} → ${tunnel_if})"
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

require_fresh_or_upgrade() {
  local marker="${1:-/etc/wireguard/wg-tunnel.conf}"
  local mode="${WG_INSTALL_MODE:-fresh}"
  if [[ "$mode" == "upgrade" ]]; then
    log "Upgrade mode — preserving existing WireGuard keys where possible"
    return 0
  fi
  if [[ -f "$marker" ]]; then
    if [[ "${WG_INSTALL_FORCE:-0}" != "1" ]]; then
      die "Existing install detected. Set WG_INSTALL_MODE=upgrade to preserve keys, or WG_INSTALL_FORCE=1 to overwrite."
    fi
    warn "WG_INSTALL_FORCE=1 — overwriting existing configuration"
  fi
  backup_wg_configs "pre-install"
}

maybe_enable_ufw() {
  if [[ "${WG_UFW_ENABLE:-0}" == "1" ]] && command -v ufw >/dev/null 2>&1; then
    ufw --force enable || true
    log "ufw enabled (WG_UFW_ENABLE=1)"
  fi
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

preserve_tunnel_keys() {
  local conf="$1"
  local pub_file="$2"
  if [[ "${WG_INSTALL_MODE:-fresh}" != "upgrade" ]]; then
    return 1
  fi
  if [[ ! -f "$conf" ]]; then
    return 1
  fi
  TUNNEL_PRIV="$(wg_conf_private_key "$conf")"
  [[ -n "$TUNNEL_PRIV" ]] || return 1
  if [[ -f "$pub_file" ]]; then
    TUNNEL_PUB="$(<"$pub_file")"
  else
    TUNNEL_PUB="$(printf '%s' "$TUNNEL_PRIV" | wg pubkey)"
  fi
  log "Reusing existing tunnel keys from $conf"
  return 0
}
