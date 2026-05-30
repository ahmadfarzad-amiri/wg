#!/bin/bash
# Serve panels on port 80 via nginx. Run as root after panel install.
# Optional env: PANEL_DOMAIN CLIENT_PORT ADMIN_PORT SSL_CERT SSL_KEY
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../deploy/lib/common.sh
source "$SCRIPT_DIR/../../deploy/lib/common.sh"

require_root

PANEL_DOMAIN="${PANEL_DOMAIN:-}"
CLIENT_PORT="${CLIENT_PORT:-8088}"
ADMIN_PORT="${ADMIN_PORT:-8090}"

if [[ -z "$PANEL_DOMAIN" ]]; then
  prompt PANEL_DOMAIN "Public domain for nginx server_name" ""
fi

TEMPLATE="$SCRIPT_DIR/nginx-panels.conf.template"
OUT="/etc/nginx/sites-available/wg-panels.conf"

if [[ -n "${SSL_CERT:-}" && -n "${SSL_KEY:-}" ]]; then
  install_panel_nginx "$TEMPLATE" "$OUT" "$PANEL_DOMAIN" "$CLIENT_PORT" "$ADMIN_PORT" "$SSL_CERT" "$SSL_KEY"
else
  install_panel_nginx "$TEMPLATE" "$OUT" "$PANEL_DOMAIN" "$CLIENT_PORT" "$ADMIN_PORT"
fi

ln -sf "$OUT" /etc/nginx/sites-enabled/wg-panels.conf
rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true
nginx -t
systemctl reload nginx

echo "Panels available via nginx:"
echo "  http://${PANEL_DOMAIN}/login"
echo "  http://${PANEL_DOMAIN}/admin/login"
