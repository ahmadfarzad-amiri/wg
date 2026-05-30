# /opt/wg layout

Target structure on the server:

```
/opt/wg/
├── README.md
├── client-panel/          # user VPN panel (port 8088)
│   ├── app.py
│   ├── static/
│   └── client_panel/
└── admin-panel/           # admin panel
    └── admin_app.py
```

## One-time migration (root)

```bash
sudo bash /opt/wg-panel/client-panel/deploy/migrate-to-opt-wg.sh
```

Or if client-panel is already under `/opt/wg-panel/client-panel`:

```bash
cd /opt/wg-panel/client-panel/deploy
sudo bash migrate-to-opt-wg.sh
```

## Manual run

```bash
sudo mkdir -p /opt/wg
sudo mv /opt/wg-panel/client-panel /opt/wg/client-panel
sudo mv /opt/wg-admin-panel /opt/wg/admin-panel
sudo cp /opt/wg/client-panel/deploy/wg-panel.service /etc/systemd/system/
sudo cp /opt/wg/client-panel/deploy/wg-admin-panel.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl restart wg-panel wg-admin-panel
```

## Test

```bash
/usr/bin/python3 /opt/wg/client-panel/app.py
```
