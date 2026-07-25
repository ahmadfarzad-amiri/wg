# WireGuard Access Panels — Documentation

Guides for **end users**, **administrators**, and **operators** running the two-hop VPN stack.

## Who should read what

| Guide | Audience | What it covers |
|-------|----------|----------------|
| [Architecture](ARCHITECTURE.md) | Everyone (reference) | Traffic path, panels, database schema, security |
| [Fresh deployment](FRESH_DEPLOYMENT.md) | Operators | Clean entry/exit install and acceptance checklist |
| [User guide](USER_GUIDE.md) | VPN users | Register, log in, connect, subscription links, connection test, support requests |
| [Admin guide](ADMIN_GUIDE.md) | Panel administrators | Approve users, bulk create clients, handle requests, audit log, server tools |
| [Operations guide](OPERATIONS.md) | Server operators | Install, validate, operate, troubleshoot, uninstall |
| [Performance guide](PERFORMANCE.md) | Operators / admins | Two-hop throughput, MTU, BBR, hop bandwidth tests |

## Quick links

- **Repository:** [github.com/ahmadfarzad-amiri/wg](https://github.com/ahmadfarzad-amiri/wg)
- **Server install:** [deploy/README-DEPLOY.md](../deploy/README-DEPLOY.md)
- **Client panel code:** [client-panel/README.md](../client-panel/README.md)
- **Admin panel code:** [admin-panel/README.md](../admin-panel/README.md)

## Default panel URLs (entry server)

| Panel | Default URL | Port |
|-------|-------------|------|
| Client (users) | `http://ENTRY_IP:8088/login` | 8088 |
| Admin | `http://ENTRY_IP:8090/admin/login` | 8090 |

With nginx + HTTPS, use your domain instead — configured automatically if `WG_DOMAIN` is set at install.

## Languages

Both panels support **Persian (fa)** and **English (en)**. Switch with the language selector in the header.
The UI is fully RTL for Persian and LTR for English, including table alignment, form fields, and navigation.

## How a user goes from registration to connected

```
1. User registers on the client panel  →  status: pending
2. Admin approves in Users tab         →  assigns a WireGuard client config
3. User logs in, downloads config      →  from Dashboard → Tools (ZIP) or Settings
          or scans QR code             →  from the Dashboard when account is active
          or uses subscription link    →  from Dashboard → Tools → Subscription link
4. User imports config into WireGuard app and connects
5. Internet exits via exit server      →  twohop (production default)
```

For step-by-step instructions, open the guide for your role above.
