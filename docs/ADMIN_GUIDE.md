# Admin guide — admin panel

This guide is for **administrators** who manage users, WireGuard clients, and support requests.

> **First time deploying?** Start with [Operations guide](OPERATIONS.md). For end-user help, see [User guide](USER_GUIDE.md).

---

## Access

| Item | Default |
|------|---------|
| URL | `http://ENTRY_IP:8090/admin/login` or your nginx domain + `/admin/login` |
| Username | `admin` (unless changed) |
| Password | Set at install via `WG_ADMIN_PASS`, changeable in **Settings** |
| Language | Persian / English — use the switcher in the header |

---

## Navigation overview

| Tab | Use for |
|-----|---------|
| **Dashboard** | Quick stats, recent requests, system health |
| **Clients** | WireGuard peers — create, bulk add, set limits, enable/disable |
| **Users** | Panel accounts — approve, assign configs, reset passwords |
| **Requests** | Support tickets submitted by users |
| **Active** | Who is currently connected (live WireGuard status) |
| **Xray** | Xray protocol status; add/delete VLESS+Reality, WebSocket, Shadowsocks clients |
| **Tools** | Change entry/exit server IPs, view audit log |
| **Settings** | Change admin password |

On mobile, use the bottom navigation bar. Filters appear below the header on list pages.

---

## Daily workflow: approving a new user

### Step 1 — Check for pending users

1. Open **Users**.
2. The **pending** filter is active by default — pending accounts appear at the top.
3. Note the username and registration date.

### Step 2 — Create a WireGuard client

**Option A — Create a new client (most common)**

1. Open **Clients**.
2. Expand **Add client** at the bottom of the page.
3. Fill in the fields:

   | Field | Notes |
   |-------|-------|
   | Name | Required. Letters, numbers, hyphens. E.g. `alice` |
   | Data limit | E.g. `20G` or leave blank for unlimited |
   | Days | Subscription length; blank = unlimited |
   | VPN mode | `twohop` (exit IP — **production default**) or `direct` (entry IP — diagnostic only) |

4. Click **Add client**. The client appears in the list.

> **Xray auto-create:** If Xray is installed on the entry server, an Xray profile with the same name is created automatically. The client's Xray links (VLESS+Reality, WebSocket, Shadowsocks) appear in the **Xray** tab and in the user's client panel dashboard.

**Option B — Use an existing unassigned client**

Skip to Step 3, using the name of an existing client that has no user assigned.

**Option C — Bulk create clients**

To add many clients at once:

1. Open **Clients**.
2. Expand **Add clients in bulk**.
3. Enter one client name per line (max 50 names).
4. Choose VPN mode, days, and limit (apply to all).
5. Click **Create**. A summary shows how many were created, skipped (already exist), or failed.

> Xray profiles are auto-created for each new client if Xray is installed.

### Step 3 — Approve and link

1. Return to **Users**.
2. Find the pending user and enter the **client name** in the approve form.
3. Click **Approve**.

What happens automatically:
- The client config is created if it did not already exist.
- The config is linked to the user in the database.
- User status changes to **approved**.

Tell the user they can now log in and import their config.

---

## Managing approved users

### Assign an additional config (multi-device)

1. **Users** → find the approved user.
2. In the **Assign config** field, enter another client name.
3. Click **Assign**.

The user downloads all assigned configs as a single ZIP from **Settings** or **Dashboard → Tools**.

### Unassign a config

1. Click **Unassign** next to the config name in the user row.
2. The primary client name on the row updates automatically.

### Disable or enable a user

| Action | When to use | Effect |
|--------|-------------|--------|
| **Disable** | User should lose panel access | Panel login blocked; WireGuard may still pass traffic until the client is also disabled |
| **Enable** | Restoring a disabled user | Status returns to approved; optionally re-enables the WireGuard client |

### Reset a password

1. Find the user in **Users**.
2. Click **Change password**, enter a new password (min 6 chars), confirm, and submit.

### Re-approve a rejected user

Use **Approve** with a client name, exactly like the initial approval flow.

---

## Managing clients

### Client list at a glance

Each row shows: name, status (enabled/disabled), usage vs limit, expiry, assigned user(s), and action buttons.

### Actions on a client

| Action | What it does |
|--------|--------------|
| **Enable / Disable** | Toggles the WireGuard peer without deleting it |
| **Disconnect** | Drops the live session by resetting the handshake |
| **Delete** | Removes the client permanently (requires confirmation) |
| **Edit** | Opens the details row — change expiry, data limit, or days |

### CLI equivalents (SSH on entry server)

```bash
sudo wg-client add alice --vpn-mode twohop
sudo wg-client set-mode alice direct
sudo wg-client sync-vpn-modes
sudo wg show wg-clients
```

---

## Handling support requests

1. Open **Requests**.
2. The **pending** filter is active by default.
3. Read the request type and the username.

### Typical responses

| Request type | Admin action |
|--------------|--------------|
| Renew | **Clients** → extend expiry or data limit → mark request done |
| Enable | **Clients** → enable client; **Users** → enable if the user was also disabled |
| Custom | Follow your policy; reject if the request is invalid |

Click **Approve** or **Reject** in the request row. The user sees the updated status in their **Support** tab.

---

## Active connections

**Active** lists clients with a WireGuard handshake in the last ~2 minutes.

- Use it to confirm that a specific user is online.
- For usage data (transfer totals), check the **Clients** tab.

If the list is empty when clients should be connected:
```bash
sudo wg show wg-clients
```
If that shows no output, the WireGuard interface may be down — check service status.

---

## Tools — server infrastructure

### Change entry endpoint (client `.conf` files)

Use when the entry VPS IP or port changes.

1. **Tools → Change entry**.
2. Enter the new `IP:51820` (and optionally the old IP to replace).
3. Confirm — this rewrites all client `.conf` files on disk.

Also update your cloud firewall and any DNS records. Connected users must reconnect.

### Change exit server

1. **Tools → Change exit**.
2. Enter the new exit server IP and its tunnel public key.
3. Then on the **new exit** server, run:
```bash
   sudo wg-ops add-peer 'ENTRY_TUNNEL_PUBKEY' 'ENTRY_PUBLIC_IP'
```

See [Operations guide](OPERATIONS.md) for changing entry/exit servers and day-2 ops.

---

## Xray protocols (VLESS+Reality, WebSocket, Shadowsocks 2022)

Xray provides alternative connection protocols that work when WireGuard UDP is blocked or throttled — common on Iranian ISPs.

### Prerequisites

Xray must be installed on the entry server. The install is included in the entry server setup when `WG_XRAY_REALITY_SNI` is set. To install it separately:

```bash
sudo WG_XRAY_REALITY_SNI=www.microsoft.com wg-ops install-xray
```

The **Xray** tab shows `installed` / `not installed` status. If not installed, the command above is shown.

### Automatic client creation

When you create a WireGuard client (single or bulk), an Xray profile with the **same name** is created automatically. The three protocol links appear in the **Xray** tab and in the user's dashboard under **Alternative protocols**.

### Manual client management

If you need to add an Xray client separately or re-sync after a failed auto-create:

1. Open **Xray**.
2. Under **Add Xray client**, enter the client name.
3. Click **Create Xray client**.

To delete: click **Delete** on the client card.

### What users get

Each Xray client has three links:

| Protocol | Use when |
|----------|----------|
| **VLESS + Reality** | WireGuard is blocked; looks like HTTPS traffic |
| **VLESS + WebSocket** | Behind Cloudflare CDN; only if `WG_XRAY_WS_DOMAIN` is set |
| **Shadowsocks 2022** | Lightweight fallback; works on most obstructed networks |

Users can copy these links from their dashboard and paste them into Xray/v2rayN/Hiddify apps.

---

### Audit log

Tools shows the **50 most recent admin actions** with:

- **When** — timestamp of the action
- **Who** — admin username that performed it
- **From** — client IP address
- **Action** and detail

Use the audit log to track approvals, bulk operations, server changes, and other admin activity.

---

## Settings

1. Open **Settings**.
2. Enter your current password, a new password (minimum **8** characters for admin), and confirmation.
3. Click **Save**.

Admin credentials are stored in `/etc/wireguard/admin.json` (not in `panel.db`).

---

## Search and filters

List pages (**Users**, **Clients**, **Requests**) have:

- **Search box** — filters the visible rows in real time (client-side)
- **Status filter** — dropdown; reloads the page with the selected filter

On small screens, tables become **cards** with the same action buttons in expandable sections.

---

## Best practices

1. Always create or choose a valid client **before** approving a user.
2. Keep clients on **twohop** (exit IP). Use **direct** only for short hop-isolation tests — not as a production speed fix.
3. **Disable** rather than **delete** when suspending service temporarily — deletion cannot be undone.
4. Keep the admin panel behind nginx + HTTPS. Do not expose port `8090` to the public internet directly.
5. Take an operational backup before bulk destructive operations:
```bash
   sudo wg-ops backup
```

---

## Related guides

- [User guide](USER_GUIDE.md) — what your users see in the client panel
- [Architecture](ARCHITECTURE.md) — two-hop design and data layout
- [Operations guide](OPERATIONS.md) — install, backup, server changes
- [Performance guide](PERFORMANCE.md) — two-hop throughput tuning and hop measurements
