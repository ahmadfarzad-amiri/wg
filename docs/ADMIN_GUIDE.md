# Admin guide (admin panel)

This guide is for **administrators** who manage users, WireGuard clients, and support requests on the entry server.

## Access

| Item | Default |
|------|---------|
| URL | `http://127.0.0.1:8090/admin/login` (local) or your nginx URL + `/admin` |
| Credentials | Set at install (`WG_ADMIN_PASS`) or in **Settings** |
| Language | Persian / English via header switcher |

Log in with the admin username (default `admin` unless changed) and password.

---

## Navigation overview

| Tab | Use for |
|-----|---------|
| **Dashboard** | Quick stats, recent requests, system snapshot |
| **Clients** | WireGuard peers: create, limits, enable/disable |
| **Users** | Panel accounts: approve, assign configs, passwords |
| **Requests** | User support tickets |
| **Active** | Who is connected right now |
| **Tools** | Change entry/exit IP, run infra scripts |
| **Settings** | Change admin password |

On mobile, use the bottom bar; filters stick below the header on list pages.

---

## Daily workflow: new user registration

### Step 1 — Check pending users

1. Open **Users**.
2. Filter: **pending** (default on first load).
3. Find the new username and registration date.

### Step 2 — Create or pick a WireGuard client

**Option A — New client (most common)**

1. Open **Clients**.
2. Expand **Add client** (bottom of page).
3. Enter client name (e.g. `alice`), optional limit/expiry, VPN mode (`twohop` or `direct`).
4. Submit → client appears in the list.

**Option B — Existing unassigned client**

Use a client already in **Clients** with no user assigned.

### Step 3 — Approve and link

1. Return to **Users**.
2. On the pending user row, enter the **client name** in the approve form (if not pre-filled).
3. Click **Approve**.

What happens automatically:

- Client is created if missing (`wg-client`).
- Config is assigned to the user in `panel.db`.
- User status → **approved**.

Tell the user they can log in and download config from **Settings**.

### Alternative actions on pending users

| Action | Result |
|--------|--------|
| **Reject** | User stays rejected; no VPN access |
| **Change password** | Set a new password (min 6 chars) without approving |

---

## Managing users (approved)

### Assign another config (multi-device / multi-tunnel)

1. **Users** → find **approved** user.
2. In **Assign config**, enter another client name.
3. Submit.

User downloads all assigned configs as ZIP from the client panel.

### Unassign a config

1. Use **Unassign** next to a assigned config name.
2. Primary client name on the user row updates automatically.

If sync fails, an error message is shown (config assignment may still have changed — refresh and verify).

### Disable / enable panel login

| Action | When | Effect |
|--------|------|--------|
| **Disable** | User is approved | User cannot use panel; VPN may still work until client disabled |
| **Enable** | User is disabled | Restores **approved** if configs exist; optionally re-enables WG client |

### Re-approve rejected users

Use **Approve** with a client name, same as pending flow.

---

## Managing clients

### Client list columns (simplified)

Shows name, status, usage/limit, expiry, assigned user(s), and primary actions.

### Common actions

| Action | Purpose |
|--------|---------|
| **Enable / Disable** | Toggle WireGuard peer without deleting |
| **Disconnect** | Drop live session (handshake reset) |
| **Delete** | Remove client (confirm) — detaches from users |
| **Edit subscription** | Open **details** row: change expiry, data limit, days |

### Add client form fields

| Field | Notes |
|-------|-------|
| Name | Required; safe characters only |
| Limit | e.g. `20G` or empty for unlimited |
| Days | Subscription length; empty = unlimited time |
| VPN mode | `twohop` (exit IP) or `direct` (entry IP) |

CLI equivalent: `sudo wg-client add NAME --vpn-mode twohop`

---

## Handling support requests

1. Open **Requests**.
2. Filter **pending** (default).
3. Read **request type** (renew, enable, etc.) and user.

### Typical responses

| Request | Admin action |
|---------|--------------|
| Renew | **Clients** → extend expiry/limit; mark request done in Requests |
| Enable | **Clients** → enable client; **Users** → enable if disabled |
| Custom | Follow your policy; reject if invalid |

Approve or reject from the request row actions. User sees updated status under client panel **Support**.

---

## Active connections

**Active** shows clients with a recent WireGuard handshake (~2 minutes).

- Use to verify someone is online.
- No RX/TX columns (simplified view); open **Clients** for usage details.

If the list is empty but clients should be connected, check `wg show wg-clients` on the server and the hint message on the page.

---

## Tools — server infrastructure

Use when migrating to a new entry or exit VPS.

### Change entry endpoint (all client `.conf` files)

1. **Tools** → **Change entry**.
2. Enter new `IP:51820` and optional old IP to replace in files.
3. Confirm → runs `change-entry-server.sh`.

Update DNS/firewall so UDP **51820** points to the new entry IP.

### Change exit server

1. **Tools** → **Change exit**.
2. Enter new exit IP and tunnel public key.
3. On the **new exit** server, run `add-entry-peer.sh` with this entry's tunnel key.

See [Operations](OPERATIONS.md) for full migration checklist.

### Maintenance

Tools may expose backup hints and recent **audit log** entries (admin actions).

---

## Settings

1. Open **Settings**.
2. Enter current password, new password (min **8** chars for admin), confirmation.
3. Submit.

Admin password is stored in `/etc/wireguard/admin.json` (not in `panel.db`).

---

## Filters and search

List pages (**Users**, **Clients**, **Requests**) support:

- **Search** box — filters visible rows client-side
- **Status filter** — dropdown; page refreshes filter on load

On small screens, tables become **cards** with the same actions in expandable sections.

---

## Best practices

1. **Approve only after** creating/choosing a valid client name.
2. Use **twohop** for privacy; use **direct** for speed-sensitive users (`wg-client set-mode NAME direct`). See [Performance guide](../docs/PERFORMANCE.md).
3. **Disable** instead of delete when pausing service temporarily.
4. Keep admin panel behind nginx + HTTPS; do not expose port 8090 publicly without a proxy.
5. Run `deploy/backup.sh` before bulk changes (Tools or CLI).

---

## CLI equivalents (SSH on entry server)

| Task | Command |
|------|---------|
| Add client | `sudo wg-client add NAME` |
| Set VPN mode | `sudo wg-client set-mode NAME twohop` |
| Sync modes | `sudo wg-client sync-vpn-modes` |
| Show status | `sudo wg show wg-clients` |

---

## Related docs

- [User guide](USER_GUIDE.md) — what your customers see
- [Architecture](ARCHITECTURE.md) — two-hop design
- [Operations](OPERATIONS.md) — install, backup, troubleshooting
