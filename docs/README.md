# WireGuard Access Panels — Documentation

This folder is the main guide for **end users**, **administrators**, and **operators** who run the two-hop VPN stack.

## Who should read what

| Guide | Audience | What it covers |
|-------|----------|----------------|
| [Architecture](ARCHITECTURE.md) | Everyone (optional) | How traffic flows, servers, panels, and data fit together |
| [User guide](USER_GUIDE.md) | VPN customers | Register, login, connect, download configs, support requests |
| [Admin guide](ADMIN_GUIDE.md) | Panel administrators | Approve users, manage clients, handle requests, daily operations |
| [Operations](OPERATIONS.md) | Server operators / DevOps | Install, upgrade, backup, change servers, troubleshooting |
| [Performance](PERFORMANCE.md) | Operators / admins | Speed tuning, VPN modes, MTU, BBR, server placement |

## Quick links

- **Repository:** [github.com/ahmadfarzad-amiri/wg](https://github.com/ahmadfarzad-amiri/wg)
- **Install (operators):** [deploy/README-DEPLOY.md](../deploy/README-DEPLOY.md)
- **Client panel code:** [client-panel/README.md](../client-panel/README.md)
- **Admin panel code:** [admin-panel/README.md](../admin-panel/README.md)

## Default URLs (entry server)

| Panel | Typical URL | Port |
|-------|-------------|------|
| Client (users) | `http://ENTRY_IP:8088/login` | 8088 |
| Admin | `http://ENTRY_IP:8090/admin/login` | 8090 |

With nginx + HTTPS, use your domain instead (configured during install).

## Languages

Both panels support **Persian (fa)** and **English (en)**. Use the language switcher in the header.

## Support flow (summary)

1. User registers on the **client panel** → status **pending**
2. Admin approves on **Users** → creates/links a WireGuard client → status **approved**
3. User downloads config from **Settings** or scans QR on the dashboard
4. User connects with WireGuard app; internet exits via **two-hop** (default) or **direct** path

For step-by-step instructions, open the guide for your role above.
