# Architecture

## Traffic path

End-user devices never connect directly to the exit server. All client WireGuard traffic lands on the **entry** VPS; encrypted tunnel traffic carries it to the **exit** VPS for NAT to the internet.

```
┌─────────────┐   UDP 51820    ┌────────────────────┐  tunnel 51821  ┌──────────────┐
│ User device │ ─────────────► │ Entry VPS          │ ─────────────► │ Exit VPS     │ ──► internet
│ WireGuard   │   Endpoint     │ wg-clients + panels│   wg-tunnel    │ NAT + egress │
└─────────────┘                └────────────────────┘                └──────────────┘
```

| Server | Role | WireGuard interfaces | Who connects |
|--------|------|----------------------|--------------|
| Entry | Client endpoint + web panels | `wg-clients` (users), `wg-tunnel` (to exit) | All VPN users; admin UI |
| Exit | Internet egress | `wg-tunnel` (from entry only) | Entry server only — not end users |

Default client subnet: `10.10.10.0/24` (override with `WG_CLIENT_CIDR` on both servers).

## VPN modes (per client)

| Mode | Egress IP seen on the internet | When to use |
|------|--------------------------------|-------------|
| `twohop` (default) | Exit server public IP | Normal privacy path |
| `direct` | Entry server public IP | Lower latency; entry IP visible |

Set when creating a client (admin **Clients** page or `wg-client add NAME --vpn-mode direct|twohop`).

Performance tuning: [docs/PERFORMANCE.md](PERFORMANCE.md) · `sudo bash deploy/tune-vpn-performance.sh`

## Web panels

Both panels run on the **entry** server and share one SQLite database.

| Panel | Path on server | Entry script | systemd unit |
|-------|----------------|--------------|--------------|
| Client | `/opt/wg/client-panel/` | `app.py` | `wg-panel.service` |
| Admin | `/opt/wg/admin-panel/` | `app.py` | `wg-admin-panel.service` |

`admin-panel/admin_app.py` is a **legacy alias** that calls the same code as `app.py`. Install scripts and systemd use `app.py`.

### Shared data

| Resource | Location | Purpose |
|----------|----------|---------|
| User accounts | `/etc/wireguard/panel.db` | Registration, approval, config assignments |
| Client configs | `/etc/wireguard/clients/*.conf` | WireGuard `.conf` files |
| Client metadata | `/etc/wireguard/state/*.meta` | Limits, expiry, VPN mode, usage |
| Admin credentials | `/etc/wireguard/admin.json` | Admin login (PBKDF2 hash) |
| Endpoint | `/etc/wireguard/wg-endpoint` | `IP:51820` written into client configs |

Environment variables are loaded from `/etc/wireguard/entry-server.env` (see `deploy/config.env.example`).

## User lifecycle

```
Register (pending) → Admin approve + assign client → approved → download config → connect
                              ↓
                    reject / disable / enable (admin)
```

- One panel user can have **multiple** WireGuard clients assigned.
- Primary client name is stored on the user row; full list is in `panel.db` assignment tables.
- Users download all assigned configs as a **ZIP** from Settings.

## Admin panel sections

| Tab | Purpose |
|-----|---------|
| Dashboard | Overview metrics, recent activity |
| Clients | Create, enable/disable, limits, subscription edits |
| Users | Approve registrations, assign configs, passwords |
| Requests | Support tickets from users (renew, enable, etc.) |
| Active | Currently connected clients (live `wg show`) |
| Tools | Change entry/exit server, maintenance scripts |
| Settings | Admin password, language |

## Client panel sections

| Tab | Purpose |
|-----|---------|
| Dashboard | Account status, setup steps, QR when active |
| Support | Submit renew/enable requests; view history |
| Settings | Change password, download configs (ZIP) |

## Security notes

- Admin panel binds to `127.0.0.1` by default; expose via nginx reverse proxy, not directly to the internet.
- Client panel may bind to `0.0.0.0:8088`; prefer HTTPS in production.
- Passwords use PBKDF2-SHA256 (300k iterations for new hashes; legacy 250k still accepted on login).
- CSRF tokens protect POST forms in both panels.

## Code layout (developers)

```
wg/
├── wg_common/             # Shared constants, passwords, client status logic
├── client-panel/          # User-facing panel + wg-client CLI
├── admin-panel/           # Administrator panel
├── deploy/                # Install, backup, routing scripts
├── tests/                 # Unit tests (wg_common)
└── docs/                  # Documentation
```

Panels are plain Python (`http.server`) with no external web framework. Shared logic lives in **`wg_common/`** (status constants, password hashing, client status evaluation). Static assets live under each panel's `static/` folder.
