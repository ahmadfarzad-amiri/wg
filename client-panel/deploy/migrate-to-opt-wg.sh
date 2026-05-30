#!/bin/bash
# Move panels under /opt/wg — run as root: sudo bash migrate-to-opt-wg.sh
set -euo pipefail

mkdir -p /opt/wg

if [[ -d /opt/wg-panel/client-panel && ! -d /opt/wg/client-panel ]]; then
  mv /opt/wg-panel/client-panel /opt/wg/client-panel
  echo "Moved client-panel -> /opt/wg/client-panel"
elif [[ -d /opt/wg/client-panel ]]; then
  echo "client-panel already at /opt/wg/client-panel"
else
  echo "ERROR: /opt/wg-panel/client-panel not found" >&2
  exit 1
fi

if [[ -d /opt/wg-admin-panel && ! -d /opt/wg/admin-panel ]]; then
  mv /opt/wg-admin-panel /opt/wg/admin-panel
  echo "Moved admin-panel -> /opt/wg/admin-panel"
elif [[ -d /opt/wg/admin-panel ]]; then
  echo "admin-panel already at /opt/wg/admin-panel"
else
  echo "WARN: /opt/wg-admin-panel not found, skipping admin move"
fi

chmod +x /opt/wg/client-panel/app.py 2>/dev/null || true
chmod +x /opt/wg/admin-panel/admin_app.py 2>/dev/null || true

install -m 644 /opt/wg/client-panel/deploy/wg-panel.service /etc/systemd/system/wg-panel.service
install -m 644 /opt/wg/client-panel/deploy/wg-admin-panel.service /etc/systemd/system/wg-admin-panel.service

systemctl daemon-reload
systemctl restart wg-panel.service
systemctl restart wg-admin-panel.service 2>/dev/null || true

echo ""
echo "Done. Layout:"
ls -la /opt/wg/
systemctl is-active wg-panel.service || true
