#!/usr/bin/env bash
# Add a new Xray client and print their connection configs.
#
# Usage: sudo wg-ops xray-client CLIENT_NAME
#
# The script reads server secrets from /etc/xray/server-secrets.env,
# generates a UUID for the client, adds them to both VLESS inbounds in
# the Xray config, restarts Xray, and prints the share links.
#
set -eo pipefail
set -u

XRAY_DIR="/etc/xray"
XRAY_BIN="/usr/local/bin/xray"
SECRETS_FILE="$XRAY_DIR/server-secrets.env"

die()  { echo "ERROR: $*" >&2; exit 1; }
log()  { echo "[xray-client] $*"; }

require_root() {
  [ "$(id -u)" -eq 0 ] || die "Run as root: sudo bash $0 CLIENT_NAME"
}

sanitize_name() {
  echo "$1" | tr -cs 'A-Za-z0-9_.-' '_'
}

generate_uuid() {
  "$XRAY_BIN" uuid 2>/dev/null || python3 -c "import uuid; print(uuid.uuid4())"
}

main() {
  require_root

  local raw_name="${1:-}"
  [[ -n "$raw_name" ]] || die "Usage: sudo wg-ops xray-client CLIENT_NAME"
  local name
  name="$(sanitize_name "$raw_name")"

  [[ -f "$SECRETS_FILE" ]] || die "Server secrets not found at $SECRETS_FILE — run install-xray.sh first"
  [[ -x "$XRAY_BIN" ]]    || die "Xray binary not found at $XRAY_BIN — run install-xray.sh first"

  # shellcheck source=/dev/null
  source "$SECRETS_FILE"

  local config="$XRAY_DIR/config.json"
  [[ -f "$config" ]] || die "Xray config not found at $config — run install-xray.sh first"

  # Check if client already exists
  local client_file="$XRAY_DIR/clients/${name}.env"
  if [[ -f "$client_file" ]]; then
    log "Client '$name' already exists — loading existing UUID"
    # shellcheck source=/dev/null
    source "$client_file"
  else
    CLIENT_UUID="$(generate_uuid)"
    cat > "$client_file" <<ENV
CLIENT_NAME=${name}
CLIENT_UUID=${CLIENT_UUID}
ENV
    chmod 600 "$client_file"
    log "Created client '$name' with UUID $CLIENT_UUID"
  fi

  # Add UUID to VLESS inbounds (Reality gets flow; WebSocket must not).
  python3 - "$config" "$name" "$CLIENT_UUID" <<'PY'
import json, sys
config_path, name, client_id = sys.argv[1:]
with open(config_path) as f:
    cfg = json.load(f)
changed = False
for ib in cfg["inbounds"]:
    if ib.get("protocol") != "vless":
        continue
    tag = ib.get("tag", "")
    clients = ib["settings"].setdefault("clients", [])
    exists = any(c.get("id") == client_id for c in clients)
    if not exists:
        entry = {"id": client_id, "email": name}
        if tag == "vless-reality":
            entry["flow"] = "xtls-rprx-vision"
        clients.append(entry)
        changed = True
        print(f"Added {name} to inbound {tag or '?'}")
    else:
        # Repair wrong flow on WebSocket if an older installer added it.
        for c in clients:
            if c.get("id") != client_id:
                continue
            if tag == "vless-ws-tls" and c.pop("flow", None) is not None:
                changed = True
                print(f"Removed invalid flow from {name} on {tag}")
            elif tag == "vless-reality" and c.get("flow") != "xtls-rprx-vision":
                c["flow"] = "xtls-rprx-vision"
                changed = True
                print(f"Set Reality flow for {name} on {tag}")
        print(f"Client {name} already in inbound {tag or '?'}")
if changed:
    with open(config_path, "w") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
PY

  # Reload Xray config live (no restart needed if xray supports SIGHUP)
  if systemctl is-active --quiet xray 2>/dev/null; then
    systemctl reload xray 2>/dev/null || systemctl restart xray
    log "Xray config reloaded"
  fi

  local server_ip="${XRAY_SERVER_IP:-}"
  local reality_pub="${XRAY_REALITY_PUB:-}"
  local reality_sid="${XRAY_REALITY_SHORT_ID:-}"
  local reality_sni="${XRAY_REALITY_SNI:-}"
  local ss_pass="${XRAY_SS_PASSWORD:-}"
  local ws_domain="${XRAY_WS_DOMAIN:-}"

  echo ""
  echo "========================================================"
  echo "  Connection configs for: $name"
  echo "========================================================"
  echo ""
  echo "--- 1. VLESS + Reality (recommended for Iran) ---"
  echo "vless://${CLIENT_UUID}@${server_ip}:443?encryption=none&flow=xtls-rprx-vision&security=reality&sni=${reality_sni}&fp=chrome&pbk=${reality_pub}&sid=${reality_sid}&type=tcp&headerType=none#${name}-reality"
  echo ""
  if [[ -n "$ws_domain" ]]; then
    echo "--- 2. VLESS + WebSocket + TLS (Cloudflare CDN fallback) ---"
    echo "vless://${CLIENT_UUID}@${ws_domain}:443?encryption=none&security=tls&sni=${ws_domain}&type=ws&path=%2Fvless#${name}-ws"
    echo ""
  fi
  echo "--- 3. Shadowsocks 2022 (simple fallback) ---"
  echo "ss://$(echo -n "2022-blake3-aes-256-gcm:${ss_pass}" | base64 -w0)@${server_ip}:8388#${name}-ss"
  echo ""
  echo "========================================================"
  echo "Apps: Hiddify (all platforms), v2rayNG (Android), v2rayN (Windows)"
  echo "========================================================"
}

main "$@"
