# WireGuard Access Panels — Documentation

## Who should read what

| Guide | Audience | Start here if you want to… |
|-------|----------|----------------------------|
| **[Deployment](DEPLOYMENT.md)** | Operators | Install entry + exit for the first time (pinned CDN tag) |
| **[Operations](OPERATIONS.md)** | Operators | `pull` / `update`, backup, change servers, release/purge |
| **[Architecture](ARCHITECTURE.md)** | Everyone | Understand the two-hop design |
| **[Admin guide](ADMIN_GUIDE.md)** | Admins | Use the admin panel |
| **[User guide](USER_GUIDE.md)** | VPN users | Use the client panel |

**Repository:** [github.com/ahmadfarzad-amiri/wg](https://github.com/ahmadfarzad-amiri/wg)

## Default URLs (entry server)

| Panel | URL |
|-------|-----|
| Client | `http://ENTRY_IP:8088/login` |
| Admin | `http://ENTRY_IP:8090/admin/login` |

With HTTPS, use your domain instead.

## User journey (short)

1. User registers on the client panel → pending  
2. Admin approves and assigns a WireGuard config  
3. User downloads `.conf` / QR / subscription link and connects  
4. Internet exits via the **exit** server (`twohop`)

Panels support **Persian** and **English** (RTL/LTR).
