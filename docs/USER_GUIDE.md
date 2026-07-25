# User guide — client panel

This guide is for **VPN users**. It covers registration, connecting, downloading configs, and getting help.

> **Not a user?** Server setup → [Deployment](DEPLOYMENT.md). Day-2 ops → [Operations](OPERATIONS.md). Admin tasks → [Admin guide](ADMIN_GUIDE.md).

---

## What you need before starting

- The **client panel URL** from your provider (e.g. `https://PANEL_DOMAIN/login` or `http://ENTRY_IP:8088/login`)
- The **WireGuard app** installed on your device — [wireguard.com/install](https://www.wireguard.com/install/)
- A username and password (you create these during registration)

---

## 1. Register

1. Open the panel URL and click **Register**.
2. Choose a username (letters and numbers only, no spaces).
3. Enter a password (minimum 6 characters).
4. Click **Register**.

Your account is now **pending**. An administrator must approve it before you can use the VPN.

---

## 2. Log in

1. Go to the panel URL and click **Login**.
2. Enter your username and password.
3. You land on the **Dashboard**.

> Use the **language switcher** on the login screen or in the header to switch between Persian and English.

---

## 3. Wait for approval

Your dashboard shows a clear **pending** message until an admin approves your account. You can open **Support** while you wait.

While pending:
- You cannot download VPN configs.
- The Support page shows a "waiting" message rather than action buttons.

When approved, the dashboard updates — **connect** steps appear first (download / QR / copy).

---

## 4. Install WireGuard and import your config

After approval, start on the **Dashboard** connect card:

### Option A — Download config (desktop)

1. Tap **Download config** on the Dashboard (or **Settings**).
2. In WireGuard: **Import tunnel from file** → select the `.conf` file.
3. If you have multiple configs, use **Download all configs** (ZIP) from the Import link section.

### Option B — QR code (mobile)

1. On the **Dashboard**, tap **Show QR**.
2. In the WireGuard app: **Create from QR code** and scan.

### Option C — Import link (subscription URL)

Some apps support a URL that imports your WireGuard config.

1. On the Dashboard, open **Import link** / **Subscription link**.
2. Copy the URL and paste it in a compatible app.
3. Use **Rotate link** if the old URL should stop working.

> Keep the import URL private — anyone with it can download your VPN config.

### Optional — Alternative protocols (Xray)

If your admin enabled Xray and your account has links, the Dashboard shows **Alternative protocols** (VLESS+Reality, WebSocket, Shadowsocks). Copy those into Hiddify / v2rayNG — not the WireGuard app. WireGuard setup steps in **Settings** are only for the WireGuard app.

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

## 6. Check server status

If something feels wrong, check **server** health from the panel (this does **not** test whether your phone is online).

1. Open **Support** in the navigation.
2. Scroll to **Server status** and click **Check server status**.

| Check | What it means |
|-------|---------------|
| WireGuard interface | The VPN server interface is running |
| Exit server ping | The tunnel to the exit server is reachable |
| DNS | The server can resolve domain names |

If any check fails, contact your admin with the results. If the server looks healthy but your device still cannot browse, re-import the config or ask Support for help.

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

Open **Settings** and click **Log out**. Your WireGuard tunnel stays active until you turn it off in the WireGuard app.

---

## Troubleshooting

| Problem | What to do |
|---------|------------|
| Stuck on "pending" for a long time | Contact your admin — the account has not been approved yet |
| Cannot download config | You must be **approved** and have a config assigned |
| Connected but no internet | Open **Support → Server status**; share results with your admin |
| Forgot password | Ask your admin to reset it |
| Config expired or disabled | Submit a **Renew** or **Enable** request under **Support** |
| Subscription link stopped working | Dashboard → **Import link** and rotate or copy a fresh URL |

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
