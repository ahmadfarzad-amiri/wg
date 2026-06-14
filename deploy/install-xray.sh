#!/usr/bin/env bash
# Install Xray-core on the ENTRY server alongside the existing WireGuard panels.
#
# This script adds three alternative inbounds that work reliably from Iran:
#   1. VLESS + Reality (port 443)  — best DPI resistance, impersonates real TLS
#   2. VLESS + WebSocket + TLS (port 8443) — CDN-compatible, works behind Cloudflare
#   3. Shadowsocks 2022 (port 8388) — simple fallback, fast
#
# Usage (non-interactive):
#   sudo WG_XRAY_REALITY_SNI=www.microsoft.com \
#        WG_XRAY_WS_DOMAIN=vpn.example.com \
#        bash deploy/install-xray.sh
#
# Usage (interactive):
#   sudo WG_INSTALL_INTERACTIVE=1 bash deploy/install-xray.sh
#
# After running:
#   - Client configs are written to /etc/xray/clients/
#   - Run: sudo bash deploy/install-xray.sh --show-client NAME  to print config
#   - Combine with xray-client-add.sh to create new client profiles
#
set -eo pipefail
set -u

XRAY_DIR="/etc/xray"
XRAY_CLIENTS_DIR="$XRAY_DIR/clients"
XRAY_BIN="/usr/local/bin/xray"
XRAY_SERVICE="/etc/systemd/system/xray.service"

die()  { echo "ERROR: $*" >&2; exit 1; }
log()  { echo "[xray-install] $*"; }
warn() { echo "[xray-install] WARN: $*" >&2; }

require_root() {
  [ "$(id -u)" -eq 0 ] || die "Run as root: sudo bash $0"
}

detect_public_ip() {
  local ip
  ip="$(curl -fsSL --max-time 5 https://api.ipify.org 2>/dev/null \
        || curl -fsSL --max-time 5 https://checkip.amazonaws.com 2>/dev/null \
        || true)"
  echo "${ip:-127.0.0.1}"
}

prompt() {
  local var="$1" prompt_text="$2" default="${3:-}"
  if [[ -n "${!var:-}" ]]; then
    log "$prompt_text: ${!var}"
    return
  fi
  read -rp "$prompt_text [${default}]: " val
  eval "$var=\"${val:-$default}\""
}

prompt_required() {
  local var="$1" prompt_text="$2"
  while true; do
    if [[ -n "${!var:-}" ]]; then
      log "$prompt_text: ${!var}"
      return
    fi
    read -rp "$prompt_text: " val
    if [[ -n "$val" ]]; then
      eval "$var=\"$val\""
      return
    fi
    echo "Required. Please enter a value."
  done
}

install_xray_binary() {
  log "Downloading Xray-core latest release..."
  local tmp_dir
  tmp_dir="$(mktemp -d)"

  local arch
  arch="$(uname -m)"
  case "$arch" in
    x86_64)  arch="64"   ;;
    aarch64) arch="arm64-v8a" ;;
    armv7*)  arch="arm32-v7a" ;;
    *)       die "Unsupported architecture: $arch" ;;
  esac

  local filename="Xray-linux-${arch}.zip"

  # Resolve the latest version tag — try GitHub API, then fall back to a pinned version.
  local version=""
  version="$(curl -fsSL --connect-timeout 8 \
    "https://api.github.com/repos/XTLS/Xray-core/releases/latest" 2>/dev/null \
    | grep '"tag_name"' | cut -d'"' -f4)"
  if [[ -z "$version" ]]; then
    # Pinned fallback — update this when a new LTS release is available
    version="v25.3.6"
    warn "GitHub API unreachable — falling back to pinned Xray version ${version}"
  fi

  # Try multiple download sources in order; stop at the first that works.
  # GitHub is often blocked in Iran; ghfast.top and ghproxy.com are CDN proxies.
  local base_gh="https://github.com/XTLS/Xray-core/releases/download/${version}"
  local downloaded=0
  local src
  for src in \
    "${base_gh}/${filename}" \
    "https://ghfast.top/${base_gh}/${filename}" \
    "https://mirror.ghproxy.com/${base_gh}/${filename}" \
    "https://gh-proxy.com/${base_gh}/${filename}"; do
    log "Trying: $src"
    if curl -fsSL --connect-timeout 12 --max-time 120 "$src" -o "$tmp_dir/xray.zip" 2>/dev/null; then
      downloaded=1
      break
    fi
  done

  if [[ "$downloaded" -eq 0 ]]; then
    rm -rf "$tmp_dir"
    die "Could not download Xray ${version} for ${arch}. Set a reachable mirror with WG_XRAY_DOWNLOAD_MIRROR or download manually."
  fi

  unzip -o "$tmp_dir/xray.zip" -d "$tmp_dir/xray" xray geoip.dat geosite.dat >/dev/null
  install -m 755 "$tmp_dir/xray/xray" "$XRAY_BIN"
  mkdir -p /usr/local/share/xray
  cp "$tmp_dir/xray/geoip.dat"   /usr/local/share/xray/ 2>/dev/null || true
  cp "$tmp_dir/xray/geosite.dat" /usr/local/share/xray/ 2>/dev/null || true
  rm -rf "$tmp_dir"
  log "Xray binary installed: $("$XRAY_BIN" version | head -1)"
}

generate_reality_keys() {
  "$XRAY_BIN" x25519 2>/dev/null | awk '
  /PrivateKey:/ {priv=$NF}
  /Password \(PublicKey\):/ {pub=$NF}
  /Private key/ {priv=$NF}
  /Public key/ {pub=$NF}
  END {print priv, pub}
'
}

generate_uuid() {
  "$XRAY_BIN" uuid 2>/dev/null || python3 -c "import uuid; print(uuid.uuid4())"
}

generate_ss_password() {
  openssl rand -base64 32
}

write_xray_config() {
  local server_ip="$1"
  local reality_private_key="$2"
  local reality_public_key="$3"
  local reality_short_id="$4"
  local reality_sni="$5"
  local ws_domain="$6"
  local ws_cert="$7"
  local ws_key="$8"
  local ss_password="$9"
  local server_uuid="${10}"

  mkdir -p "$XRAY_DIR"
  chmod 700 "$XRAY_DIR"

  cat > "$XRAY_DIR/config.json" <<CONFIG
{
  "log": {
    "loglevel": "warning",
    "access": "/var/log/xray/access.log",
    "error": "/var/log/xray/error.log"
  },
  "inbounds": [
    {
      "tag": "vless-reality",
      "listen": "0.0.0.0",
      "port": 443,
      "protocol": "vless",
      "settings": {
        "clients": [],
        "decryption": "none"
      },
      "streamSettings": {
        "network": "tcp",
        "security": "reality",
        "realitySettings": {
          "show": false,
          "dest": "${reality_sni}:443",
          "xver": 0,
          "serverNames": ["${reality_sni}"],
          "privateKey": "${reality_private_key}",
          "shortIds": ["${reality_short_id}"]
        }
      },
      "sniffing": {
        "enabled": true,
        "destOverride": ["http", "tls", "quic"]
      }
    },
    {
      "tag": "vless-ws-tls",
      "listen": "127.0.0.1",
      "port": 8443,
      "protocol": "vless",
      "settings": {
        "clients": [],
        "decryption": "none"
      },
      "streamSettings": {
        "network": "ws",
        "wsSettings": {
          "path": "/vless"
        }
      }
    },
    {
      "tag": "shadowsocks",
      "listen": "0.0.0.0",
      "port": 8388,
      "protocol": "shadowsocks",
      "settings": {
        "method": "2022-blake3-aes-256-gcm",
        "password": "${ss_password}",
        "network": "tcp,udp"
      }
    }
  ],
  "dns": {
    "servers": ["8.8.8.8", "1.1.1.1", "localhost"]
  },
  "outbounds": [
    {
      "tag": "direct",
      "protocol": "freedom",
      "settings": {}
    },
    {
      "tag": "blocked",
      "protocol": "blackhole",
      "settings": {}
    }
  ],
  "routing": {
    "domainStrategy": "AsIs",
    "rules": [
      {
        "type": "field",
        "ip": [
          "10.0.0.0/8",
          "172.16.0.0/12",
          "192.168.0.0/16",
          "127.0.0.0/8",
          "100.64.0.0/10",
          "::1/128",
          "fc00::/7",
          "fe80::/10"
        ],
        "outboundTag": "blocked"
      },
      {
        "type": "field",
        "outboundTag": "direct",
        "network": "tcp,udp"
      }
    ]
  }
}
CONFIG
  chmod 600 "$XRAY_DIR/config.json"
  log "Xray config written to $XRAY_DIR/config.json"
}

write_systemd_service() {
  cat > "$XRAY_SERVICE" <<SERVICE
[Unit]
Description=Xray Service (VLESS/Reality/Shadowsocks)
Documentation=https://github.com/XTLS/Xray-core
After=network.target nss-lookup.target

[Service]
Type=simple
User=root
EnvironmentFile=-/etc/xray/env
ExecStart=${XRAY_BIN} run -config ${XRAY_DIR}/config.json
Restart=on-failure
RestartSec=3
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
SERVICE
  systemctl daemon-reload
  systemctl enable xray
  log "Xray systemd service installed"
}

add_client_to_inbound() {
  local inbound_tag="$1"
  local client_id="$2"   # UUID for VLESS
  local client_email="$3"
  local config="$XRAY_DIR/config.json"

  python3 - "$config" "$inbound_tag" "$client_id" "$client_email" <<'PY'
import json, sys
config_path, tag, client_id, email = sys.argv[1:]
with open(config_path) as f:
    cfg = json.load(f)
for ib in cfg["inbounds"]:
    if ib.get("tag") == tag:
        clients = ib["settings"].setdefault("clients", [])
        for c in clients:
            if c.get("id") == client_id or c.get("email") == email:
                sys.exit(0)  # already exists
        clients.append({"id": client_id, "email": email, "flow": "xtls-rprx-vision"})
        break
with open(config_path, "w") as f:
    json.dump(cfg, f, indent=2, ensure_ascii=False)
print(f"Added client {email} to {tag}")
PY
}

show_client_configs() {
  local client_name="$1"
  local server_ip="$2"
  local reality_public_key="$3"
  local reality_short_id="$4"
  local reality_sni="$5"
  local client_uuid="$6"
  local ws_domain="$7"
  local ss_password="$8"

  echo ""
  echo "========================================================"
  echo "  Client configs for: $client_name"
  echo "========================================================"
  echo ""
  echo "--- 1. VLESS + Reality (best for Iran, paste in v2rayNG/Hiddify) ---"
  echo "vless://${client_uuid}@${server_ip}:443?encryption=none&flow=xtls-rprx-vision&security=reality&sni=${reality_sni}&fp=chrome&pbk=${reality_public_key}&sid=${reality_short_id}&type=tcp&headerType=none#${client_name}-reality"
  echo ""
  echo "--- 2. VLESS + WebSocket + TLS (behind Cloudflare CDN) ---"
  echo "vless://${client_uuid}@${ws_domain}:443?encryption=none&security=tls&sni=${ws_domain}&type=ws&path=%2Fvless#${client_name}-ws"
  echo ""
  echo "--- 3. Shadowsocks 2022 (simple fallback) ---"
  echo "ss://$(echo -n "2022-blake3-aes-256-gcm:${ss_password}" | base64 -w0)@${server_ip}:8388#${client_name}-ss"
  echo ""
  echo "========================================================"
  echo "Recommended apps:"
  echo "  iOS:     Hiddify, Streisand, Shadowrocket"
  echo "  Android: v2rayNG, Hiddify, NekoBox"
  echo "  Windows: Hiddify, v2rayN, Nekoray"
  echo "  macOS:   Hiddify, V2Box, Clash Verge"
  echo "  Linux:   Hiddify, v2rayA, sing-box CLI"
  echo "========================================================"
}

main() {
  require_root

  log "=== Xray-core installer for restricted networks (Iran-optimized) ==="
  log "This installs VLESS+Reality, VLESS+WebSocket+TLS, and Shadowsocks 2022"
  log "alongside your existing WireGuard setup."
  echo ""

  # Prefer the authoritative entry-server IP recorded during WireGuard install.
  # /etc/wireguard/wg-endpoint contains "IP:PORT" — extract just the IP.
  _wg_entry_ip() {
    local ep
    ep="$(cat /etc/wireguard/wg-endpoint 2>/dev/null || true)"
    echo "${ep%%:*}"
  }
  SERVER_IP="${WG_XRAY_SERVER_IP:-$(_wg_entry_ip)}"
  SERVER_IP="${SERVER_IP:-$(detect_public_ip)}"
  REALITY_SNI="${WG_XRAY_REALITY_SNI:-}"
  WS_DOMAIN="${WG_XRAY_WS_DOMAIN:-}"
  ENABLE_WS_TLS="${WG_XRAY_ENABLE_WS:-yes}"

  if [[ "${WG_INSTALL_INTERACTIVE:-0}" == "1" || -t 0 ]]; then
    echo "Interactive mode — press Enter to accept [defaults]."
    echo ""
    prompt SERVER_IP "Entry server public IP" "$SERVER_IP"
    prompt REALITY_SNI "Reality SNI (domain to impersonate, e.g. www.microsoft.com)" "${REALITY_SNI:-www.microsoft.com}"
    echo "WebSocket+TLS inbound is used behind Cloudflare CDN."
    echo "Set WS domain to your Cloudflare-proxied domain, or leave blank to skip."
    prompt WS_DOMAIN "WebSocket domain (blank to skip)" "${WS_DOMAIN:-}"
  else
    REALITY_SNI="${REALITY_SNI:-www.microsoft.com}"
    log "Server IP:   $SERVER_IP"
    log "Reality SNI: $REALITY_SNI"
    log "WS domain:   ${WS_DOMAIN:-(skipped)}"
  fi

  # Install dependencies
  apt-get install -y unzip curl openssl python3 2>/dev/null || true

  # Install Xray binary
  if [[ ! -x "$XRAY_BIN" ]]; then
    install_xray_binary
  else
    log "Xray already installed: $("$XRAY_BIN" version | head -1)"
    log "To upgrade, delete $XRAY_BIN and re-run this script."
  fi

  # Generate cryptographic material
  log "Generating Reality keys..."
  read -r REALITY_PRIV REALITY_PUB < <(generate_reality_keys)
  [[ -n "$REALITY_PRIV" ]] || die "Reality private key generation failed — is xray binary working? Try: $XRAY_BIN x25519"
  [[ -n "$REALITY_PUB"  ]] || die "Reality public key generation failed — try: $XRAY_BIN x25519"
  REALITY_SHORT_ID="$(openssl rand -hex 8)"
  [[ -n "$REALITY_SHORT_ID" ]] || die "openssl rand failed — is openssl installed?"
  SERVER_UUID="$(generate_uuid)"
  SS_PASSWORD="$(generate_ss_password)"

  log "Reality public key:  $REALITY_PUB"
  log "Reality short ID:    $REALITY_SHORT_ID"
  log "Server UUID:         $SERVER_UUID"

  # TLS cert paths for WebSocket+TLS inbound
  WS_CERT=""
  WS_KEY=""
  if [[ -n "$WS_DOMAIN" ]]; then
    WS_CERT="/etc/letsencrypt/live/${WS_DOMAIN}/fullchain.pem"
    WS_KEY="/etc/letsencrypt/live/${WS_DOMAIN}/privkey.pem"
    if [[ ! -f "$WS_CERT" ]]; then
      warn "TLS cert not found for $WS_DOMAIN at $WS_CERT"
      warn "WebSocket+TLS inbound will use HTTP — only safe behind Cloudflare SSL"
    fi
  fi

  mkdir -p "$XRAY_CLIENTS_DIR" /var/log/xray
  chmod 700 "$XRAY_CLIENTS_DIR" "$XRAY_DIR"

  # Write main config
  write_xray_config \
    "$SERVER_IP" \
    "$REALITY_PRIV" \
    "$REALITY_PUB" \
    "$REALITY_SHORT_ID" \
    "$REALITY_SNI" \
    "$WS_DOMAIN" \
    "$WS_CERT" \
    "$WS_KEY" \
    "$SS_PASSWORD" \
    "$SERVER_UUID"

  # Save server secrets for client generation later
  cat > "$XRAY_DIR/server-secrets.env" <<ENV
XRAY_SERVER_IP=${SERVER_IP}
XRAY_REALITY_PUB=${REALITY_PUB}
XRAY_REALITY_PRIV=${REALITY_PRIV}
XRAY_REALITY_SHORT_ID=${REALITY_SHORT_ID}
XRAY_REALITY_SNI=${REALITY_SNI}
XRAY_SS_PASSWORD=${SS_PASSWORD}
XRAY_WS_DOMAIN=${WS_DOMAIN}
ENV
  chmod 600 "$XRAY_DIR/server-secrets.env"

  # Write firewall rules (UFW)
  if command -v ufw >/dev/null 2>&1; then
    ufw allow 443/tcp comment "xray-reality" 2>/dev/null || true
    ufw allow 8388/tcp comment "xray-ss"     2>/dev/null || true
    ufw allow 8388/udp comment "xray-ss-udp" 2>/dev/null || true
    log "UFW rules added for ports 443/tcp, 8388/tcp+udp"
  fi

  # Check for port 443 conflict BEFORE starting the service
  PORT443_HOLDER=""
  if ss -tlnp 2>/dev/null | grep -qE ':443\b'; then
    PORT443_HOLDER="$(ss -tlnp 2>/dev/null | grep -E ':443\b' | awk '{print $NF}' | head -1)"
  fi
  if [[ -n "$PORT443_HOLDER" ]]; then
    warn "Port 443 is already in use by: ${PORT443_HOLDER}"
    warn "VLESS+Reality requires port 443. Options:"
    warn "  1. Disable SSL on nginx: remove the listen 443 block for your panel domain"
    warn "     then re-run this script so Xray can own port 443."
    warn "  2. Use nginx stream SNI routing (advanced) — see docs/OPERATIONS.md."
    warn "Starting Xray anyway; it will fail until port 443 is freed."
  fi

  # Nginx WebSocket proxy — forwards CDN traffic to the Xray WS backend on 127.0.0.1:8443
  setup_nginx_ws_proxy() {
    local ws_domain="$1"
    if ! command -v nginx >/dev/null 2>&1; then
      warn "nginx not found — WebSocket proxy not configured. Install nginx and add:"
      warn "  proxy_pass http://127.0.0.1:8443 for location /vless on ${ws_domain}"
      return
    fi
    local conf="/etc/nginx/sites-available/xray-ws.conf"
    cat > "$conf" << NGINX_WS
# Xray WebSocket proxy — generated by install-xray.sh
# ${ws_domain}/vless → 127.0.0.1:8443 (Xray VLESS+WS backend)
# TLS is terminated by Cloudflare (orange-cloud required on this domain).
server {
    listen 80;
    server_name ${ws_domain};

    location /vless {
        proxy_pass http://127.0.0.1:8443;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
    }

    location / {
        return 403;
    }
}
NGINX_WS
    ln -sf "$conf" /etc/nginx/sites-enabled/xray-ws.conf
    if nginx -t 2>/dev/null; then
      systemctl reload nginx 2>/dev/null || true
      log "Nginx WebSocket proxy configured: ${ws_domain}/vless → 127.0.0.1:8443"
    else
      warn "nginx config test failed for xray-ws.conf — WebSocket proxy not active"
      rm -f /etc/nginx/sites-enabled/xray-ws.conf
    fi
  }

  if [[ -n "$WS_DOMAIN" ]]; then
    setup_nginx_ws_proxy "$WS_DOMAIN"
  fi

  write_systemd_service
  systemctl restart xray
  sleep 2
  if systemctl is-active --quiet xray; then
    log "Xray service running successfully"
  else
    warn "Xray service failed to start — check: journalctl -u xray -n 50"
    if [[ -n "$PORT443_HOLDER" ]]; then
      warn "Most likely cause: port 443 conflict with ${PORT443_HOLDER}"
      warn "Fix: free port 443 first, then: sudo systemctl start xray"
    fi
  fi

  # Show configs for the default server UUID
  show_client_configs \
    "default" \
    "$SERVER_IP" \
    "$REALITY_PUB" \
    "$REALITY_SHORT_ID" \
    "$REALITY_SNI" \
    "$SERVER_UUID" \
    "$WS_DOMAIN" \
    "$SS_PASSWORD"

  log ""
  log "To add a new client: sudo bash deploy/xray-client-add.sh CLIENT_NAME"
  log "To view logs:        journalctl -u xray -f"
  log "Config location:     $XRAY_DIR/config.json"
  log "Server secrets:      $XRAY_DIR/server-secrets.env"
  log ""
  log "IMPORTANT: For clients from Iran, use VLESS+Reality (option 1)."
  log "           If the server IP is blocked, use VLESS+WebSocket behind Cloudflare."
  log ""
  log "Cloud firewall: allow TCP 443 and TCP+UDP 8388 from all (clients connect directly)."
  log "Port 8443 (WS backend) does NOT need to be open — nginx/CDN proxies it."
}

main "$@"
