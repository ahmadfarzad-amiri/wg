#!/usr/bin/env bash
# Fail if the repo contains suspicious hardcoded IPv4 addresses.
# Allowed: loopback, link-local, RFC 1918 private defaults used as VPN/CIDR
# defaults, RFC 5737 documentation ranges, and explicitly approved public DNS.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

# Collect IPv4-looking tokens from tracked text (exclude .git and caches).
RG_BIN="$(command -v rg || true)"
if [[ -z "$RG_BIN" && -x /Applications/Cursor.app/Contents/Resources/app/node_modules/@vscode/ripgrep/bin/rg ]]; then
  RG_BIN=/Applications/Cursor.app/Contents/Resources/app/node_modules/@vscode/ripgrep/bin/rg
fi

if [[ -n "$RG_BIN" ]]; then
  "$RG_BIN" -n --no-heading \
    -g '!.git/**' \
    -g '!**/__pycache__/**' \
    -g '!*.pyc' \
    -g '!*.png' \
    -g '!*.woff*' \
    -g '!*.ttf' \
    -g '!*.otf' \
    -g '!*.ico' \
    -g '!*.jpg' \
    -g '!*.jpeg' \
    -g '!*.gif' \
    -g '!*.webp' \
    -g '!*.svg' \
    --regexp '\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b' \
    "$ROOT" > "$TMP" || true
else
  grep -RInE \
    --exclude-dir=.git \
    --exclude-dir=__pycache__ \
    --exclude='*.pyc' \
    --exclude='*.png' \
    --exclude='*.woff*' \
    --exclude='*.ttf' \
    '\b((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b' \
    "$ROOT" > "$TMP" || true
fi

is_allowed() {
  local ip="$1"
  # Loopback
  [[ "$ip" == 127.* ]] && return 0
  # Link-local
  [[ "$ip" == 169.254.* ]] && return 0
  # RFC 1918 — deliberate VPN / Docker / LAN defaults only
  [[ "$ip" == 10.* ]] && return 0
  [[ "$ip" == 192.168.* ]] && return 0
  if [[ "$ip" =~ ^172\.(1[6-9]|2[0-9]|3[0-1])\. ]]; then
    return 0
  fi
  # Carrier-grade NAT
  [[ "$ip" == 100.64.* || "$ip" == 100.65.* || "$ip" == 100.66.* || "$ip" == 100.67.* ]] && return 0
  # RFC 5737 documentation
  [[ "$ip" == 192.0.2.* ]] && return 0
  [[ "$ip" == 198.51.100.* ]] && return 0
  [[ "$ip" == 203.0.113.* ]] && return 0
  # Well-known public DNS (approved protocol constants for client DNS defaults)
  case "$ip" in
    8.8.8.8|8.8.4.4|1.1.1.1|1.0.0.1|9.9.9.9|149.112.112.112|\
    208.67.222.222|208.67.220.220|94.140.14.14|94.140.15.15)
      return 0
      ;;
  esac
  # 0.0.0.0 bind / any
  [[ "$ip" == "0.0.0.0" ]] && return 0
  return 1
}

fail=0
while IFS= read -r line; do
  [[ -z "$line" ]] && continue
  # Extract all IPs on the line
  ips="$(printf '%s\n' "$line" | grep -oE '\b((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b' || true)"
  for ip in $ips; do
    if ! is_allowed "$ip"; then
      echo "FORBIDDEN IP: $ip"
      echo "  $line"
      fail=$((fail + 1))
    fi
  done
done < "$TMP"

if [[ "$fail" -gt 0 ]]; then
  echo
  echo "Found ${fail} forbidden IP reference(s). Use env vars, config, or RFC 5737 examples."
  exit 1
fi

echo "OK: no suspicious hardcoded public/infrastructure IPv4 addresses"
