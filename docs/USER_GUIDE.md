# User guide — client panel

This guide is for **VPN users**. It covers registration, connecting, downloading configs, and getting help.

> **Not a user?** Server setup → [Deployment](DEPLOYMENT.md). Day-2 ops → [Operations](OPERATIONS.md). Admin tasks → [Admin guide](ADMIN_GUIDE.md).

---

## What you need before starting

- The **client panel URL** from your provider (e.g. `https://vpn.example.com/login` or `http://SERVER_IP:8088/login`)
- The **WireGuard app** installed on your device — [wireguard.com/install](https://www.wireguard.com/install/)
- A username and password (you create these during registration)

---

## 1. Register

1. Open the panel URL and click **Register**.
2. Choose a username (letters and numbers only, no spaces).
3. Enter a password (minimum 6 characters) and confirm it.
4. Click **Register**.

Your account is now **pending**. An administrator must approve it before you can use the VPN.

---

## 2. Log in

1. Go to the panel URL and click **Login**.
2. Enter your username and password.
3. You land on the **Dashboard**.

> Use the **language switcher** in the header to switch between Persian and English.

---

## 3. Wait for approval

Your dashboard shows a **pending** badge until an admin approves your account.

While pending:
- You cannot download VPN configs.
- The Support page shows a "waiting" message rather than action buttons.

When approved, the dashboard updates automatically — setup steps appear.

---

## 4. Install WireGuard and import your config

After approval you have three options:

### Option A — Download ZIP (recommended for desktop)

1. Go to **Dashboard → Tools** and click **Download all configs**,  
   or go to **Settings** and click **Download configs**.
2. Unzip the downloaded file on your device.
3. In WireGuard: **Import tunnel from file** → select the `.conf` file.

### Option B — QR code (recommended for mobile)

1. On the **Dashboard**, find the QR code section (visible when your account is active).
2. In the WireGuard app on your phone: tap **Create from QR code** and scan.

### Option C — Subscription link (automatic updates)

Some WireGuard apps (e.g. WireGuard for Android, iOS) support a subscription URL that updates your config automatically.

1. Go to **Dashboard → Tools** and click **Subscription link**.
2. Copy the URL shown on the page.
3. In your WireGuard app, paste the URL when adding a new tunnel via subscription or import URL.

To get a new subscription URL (invalidates the old one):

1. Go to **Dashboard → Tools → Subscription link**.
2. Click **Rotate link** and copy the new URL.

> Keep the subscription URL private — anyone with it can download your VPN config.

---

## 5. Connect

1. In the WireGuard app, toggle the tunnel **on**.
2. Wait a few seconds for the handshake to complete.
3. Test your connection:
   ```bash
   curl -4 https://api.ipify.org
   ```
   - **Two-hop** mode (default): the IP shown is the **exit server** IP.
   - **Direct** mode: the IP shown is the **entry server** IP.

Your admin chooses the mode per account; it is set in the config file and cannot be changed from the panel.

---

## 6. Run a connection test

If something feels wrong, use the built-in test from the panel.

1. Open **Support** in the navigation.
2. Scroll to **Connection test** and click **Test connection**.

The panel checks three things server-side and shows results:

| Check | What it means |
|-------|---------------|
| WireGuard interface | The VPN server interface is running |
| Exit server ping | The tunnel to the exit server is reachable |
| DNS | The server can resolve domain names |

If any check fails, contact your admin with the results.

---

## 7. Support requests

Open **Support** from the navigation.

### Submit a request

Available when your account is **approved** and has a config assigned.

| Request type | When to use |
|--------------|-------------|
| **Renew** | Your subscription or data limit has expired |
| **Enable** | Your account was disabled and you want it re-enabled |

1. Click the request button.
2. Status starts as **pending** until an admin handles it.

### View request history

The table (or cards on mobile) lists your past requests with ID, type, status, and date.

| Status | Meaning |
|--------|---------|
| pending | Waiting for admin review |
| approved / done | Admin completed the action |
| rejected | Admin declined |

---

## 8. Settings

### Change your password

1. Open **Settings**.
2. Enter your **current password**, a **new password** (min 6 chars), and confirm it.
3. Click **Save**.

### Download configs again

Click **Download configs** in Settings anytime while approved. Use this when reinstalling WireGuard or setting up a second device.

---

## 9. Log out

Click **Log out** in the header. Your WireGuard tunnel stays active until you turn it off in the WireGuard app.

---

## Troubleshooting

| Problem | What to do |
|---------|------------|
| Stuck on "pending" for a long time | Contact your admin — the account has not been approved yet |
| Cannot download config | You must be **approved** and have a config assigned |
| Connected but no internet | Open **Support → Connection test**; share results with your admin |
| Forgot password | Ask your admin to reset it |
| Config expired or disabled | Submit a **Renew** or **Enable** request under **Support** |
| Subscription link stopped working | Go to Dashboard → Tools → Subscription link and get a new URL |

> **Security:** Do not share your `.conf` file, QR code, or subscription URL — anyone with them can use your VPN slot.

---

## Mobile tips

- Use the **bottom navigation bar** on small screens (Dashboard, Support, Settings).
- Tables switch to **cards** automatically on narrow screens — same information, card layout.
- Tap targets are sized for touch (44 px minimum).

---

## Related guides

- [Architecture](ARCHITECTURE.md) — how the two-hop VPN path works
- [Admin guide](ADMIN_GUIDE.md) — for whoever manages your account
