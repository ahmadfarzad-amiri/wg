# User guide (client panel)

This guide is for people who **use the VPN**, not for server administrators.

## Before you start

You need:

- A **username** and **password** (you create these when registering), or credentials from your provider
- The **client panel URL** (often `http://YOUR_SERVER_IP:8088/login` or your provider's domain)
- The **WireGuard app** on your phone or computer ([wireguard.com/install](https://www.wireguard.com/install/))

Your VPN connects to the **entry server** address shown in the config — not a separate "exit" address.

---

## Step 1 — Open the client panel

1. Open the panel URL in your browser.
2. Choose **Persian** or **English** from the language switcher if needed.

---

## Step 2 — Register (new users)

1. Click **Register** (or go to `/register`).
2. Enter a **username** (letters, numbers; no spaces).
3. Enter a **password** (minimum 6 characters) and confirm it.
4. Submit the form.
5. You will see that your account is **pending** until an administrator approves it.

You cannot download a VPN config until approval.

---

## Step 3 — Log in

1. Go to **Login** (`/login`).
2. Enter your username and password.
3. After login you land on the **Dashboard**.

If login fails, check username/password or contact your administrator.

---

## Step 4 — Wait for approval

On the dashboard, status shows **pending** until an admin approves your account and assigns a VPN config.

While pending:

- You **cannot** download WireGuard configs.
- **Support** shows a waiting message instead of action buttons.

When approved, the dashboard updates to **approved** / active setup steps.

---

## Step 5 — Install WireGuard and import your config

After approval:

### Option A — Download from Settings (recommended)

1. Open **Settings** in the sidebar or bottom navigation.
2. Click **Download configs** (or similar) to get a **ZIP** with all configs assigned to you.
3. Unzip on your device.
4. In the WireGuard app: **Import tunnel from file** and select the `.conf` file.

### Option B — QR code (mobile)

1. On the **Dashboard**, when your account is active, use the **QR code** section.
2. In WireGuard on your phone: **Create from QR code** and scan.

### Option C — Copy config page

If your provider linked a setup page, follow the numbered steps shown there.

---

## Step 6 — Connect

1. In WireGuard, turn the tunnel **On**.
2. Wait a few seconds for the handshake.
3. Test internet access (open a website or run `curl -4 https://api.ipify.org` on the device).

**Expected behavior:** With default **two-hop** mode, websites see the **exit server** IP, not your home IP. **Direct** mode uses the entry server IP instead (your admin chooses this per client).

---

## Dashboard overview

| Element | Meaning |
|---------|---------|
| Status badge | `pending`, `approved`, `disabled`, etc. |
| Account info | Username, registration date |
| Setup steps | Install app → import config → connect (when approved) |

Technical details (internal IPs, keys) are hidden when your connection is active to keep the page simple.

---

## Support — requests and history

Open **Support** from the navigation.

### Submit a request (approved users only)

When your account is **approved** and you have an assigned config, you may see buttons such as:

| Request type | Typical use |
|--------------|-------------|
| Renew | Ask to extend subscription / data limit |
| Enable | Ask to re-enable after disable |
| Other | Provider-specific options |

1. Choose the request type.
2. Submit the form.
3. Status starts as **pending** until an admin handles it in the admin panel **Requests** tab.

### Request history

The table (or cards on mobile) lists your past requests with **ID**, **type**, **status**, and **date**.

Statuses:

| Status | Meaning |
|--------|---------|
| pending | Waiting for admin |
| approved / done | Admin completed the action |
| rejected | Admin declined |

---

## Settings

### Change password

1. Open **Settings**.
2. Enter **current password**, **new password** (min 6 chars), and confirmation.
3. Submit.

### Download configs again

Use the download button anytime while **approved** and configs are assigned. Useful after reinstalling WireGuard or adding a second device.

---

## Log out

Use **Log out** in the header menu. Your WireGuard tunnel stays active until you turn it off in the WireGuard app.

---

## Troubleshooting

| Problem | What to try |
|---------|-------------|
| "Pending" forever | Contact admin — account not approved yet |
| Cannot download config | Must be **approved**; admin must assign a client |
| Connected but no internet | Contact admin — server routing issue |
| Wrong password | Use **Settings → change password** if you remember the old one; otherwise ask admin |
| Config expired / disabled | Submit a **Renew** or **Enable** request under **Support** |

Do **not** share your `.conf` file or QR code — anyone with it can use your VPN slot.

---

## Mobile tips

- Use the bottom navigation on small screens (Dashboard, Support, Settings).
- Tables switch to **cards** automatically on narrow viewports.
- Tap targets are sized for touch (44px minimum).

---

## Related docs

- [Architecture](ARCHITECTURE.md) — how the VPN path works
- [Admin guide](ADMIN_GUIDE.md) — for whoever manages your account
- [Operations](OPERATIONS.md) — for server owners
