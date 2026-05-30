#!/bin/bash
# Serve client panel on http://localhost (port 80) via nginx — run as root.
set -euo pipefail

CONF=/etc/nginx/sites-available/access.bsla.dev.conf

if [[ ! -f "$CONF" ]]; then
  install -m 644 /opt/wg/client-panel/deploy/access.bsla.dev.conf "$CONF"
  ln -sf "$CONF" /etc/nginx/sites-enabled/access.bsla.dev.conf 2>/dev/null || true
else
  sed -i 's/server_name access.bsla.dev;/server_name access.bsla.dev localhost 127.0.0.1;/g' "$CONF"
fi

nginx -t
systemctl reload nginx

echo "Client panel available at:"
echo "  http://127.0.0.1:8088/login   (direct)"
echo "  http://localhost/login        (via nginx)"
echo "  http://127.0.0.1/login        (via nginx)"
