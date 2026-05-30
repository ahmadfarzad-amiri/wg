from admin_panel.components.layout import page
from admin_panel.core.client_ops import ensure_client, run_client_action
from admin_panel.core.shell import safe_name, tail_message
from admin_panel.core.wireguard import find_client_status
from admin_panel.db import panel_db
from admin_panel.views import users


def _fetch_users():
    try:
        con = panel_db()
        rows = con.execute(
            """
            SELECT id, username, status, COALESCE(client_name, '') AS client_name, created_at
            FROM users ORDER BY id DESC
            """
        ).fetchall()
        con.close()
        return rows
    except Exception:
        return []


def _friendly_error(output, client=""):
    text = (output or "").strip()
    if "Client state not found" in text:
        return (
            f"کلاینت «{client}» پیدا نشد. "
            "از صفحه کلاینت‌ها یک کانفیگ با همین نام بسازید، یا دسترسی ساخت کلاینت را بررسی کنید."
        )
    if "Run as root" in text:
        return f"ساخت کلاینت «{client}» نیاز به root دارد (sudo wg-client add {client} ...)."
    if "not found" in text.lower() and "wg" in text.lower():
        return "فایل‌های WireGuard در /etc/wireguard پیدا نشد."
    return tail_message(text)


def _approve_user(username, client, *, reassigned=False):
    ok, created, create_out = ensure_client(client)
    if not ok:
        return _friendly_error(create_out, client)

    try:
        con = panel_db()
        other = con.execute(
            "SELECT username FROM users WHERE client_name=? AND username!=? LIMIT 1",
            (client, username),
        ).fetchone()
        if other:
            con.close()
            return f"کلاینت «{client}» قبلاً به کاربر «{other['username']}» اختصاص داده شده است."

        cur = con.execute(
            "UPDATE users SET status='approved', client_name=? WHERE username=?",
            (client, username),
        )
        con.commit()
        con.close()
        if cur.rowcount == 0:
            return "کاربر پیدا نشد"
    except Exception as e:
        return f"خطا در تایید کاربر: {e}"

    if reassigned:
        if created:
            return (
                f"کلاینت «{client}» ساخته شد و به کاربر «{username}» اختصاص داده شد. "
                "کاربر فعال شد."
            )
        return f"کلاینت «{client}» به کاربر «{username}» اختصاص داده شد و کاربر فعال شد."

    if created:
        return f"کاربر «{username}» تایید شد. کلاینت «{client}» ساخته و اختصاص داده شد."
    return f"کاربر «{username}» تایید شد و به کلاینت «{client}» متصل شد."


def _reject_user(username):
    try:
        con = panel_db()
        cur = con.execute(
            "UPDATE users SET status='rejected' WHERE username=?",
            (username,),
        )
        con.commit()
        con.close()
        if cur.rowcount == 0:
            return "کاربر پیدا نشد"
    except Exception as e:
        return f"خطا در رد کاربر: {e}"
    return f"کاربر «{username}» رد شد."


def _disable_user(username):
    try:
        con = panel_db()
        cur = con.execute(
            "UPDATE users SET status='disabled' WHERE username=?",
            (username,),
        )
        con.commit()
        con.close()
        if cur.rowcount == 0:
            return "کاربر پیدا نشد"
    except Exception as e:
        return f"خطا در غیرفعال‌سازی کاربر: {e}"
    return f"کاربر «{username}» غیرفعال شد."


def _enable_user(username):
    client = ""
    try:
        con = panel_db()
        row = con.execute(
            "SELECT COALESCE(client_name, '') AS client_name FROM users WHERE username=?",
            (username,),
        ).fetchone()
        if not row:
            con.close()
            return "کاربر پیدا نشد"
        client = row["client_name"]
        cur = con.execute(
            "UPDATE users SET status='approved' WHERE username=?",
            (username,),
        )
        con.commit()
        con.close()
        if cur.rowcount == 0:
            return "کاربر پیدا نشد"
    except Exception as e:
        return f"خطا در فعال‌سازی کاربر: {e}"

    msg = f"کاربر «{username}» فعال شد."
    if client:
        status = find_client_status(client)
        if status and status.get("disabled"):
            out = run_client_action("enable", client)
            if out.strip() and "ERROR" not in out:
                msg += f" کلاینت «{client}» هم فعال شد."
    return msg


def _change_password(username, new_password):
    new_password = (new_password or "").strip()
    if len(new_password) < 6:
        return "رمز عبور باید حداقل ۶ کاراکتر باشد"

    from admin_panel.core.user_auth import hash_password

    password_hash, salt = hash_password(new_password)
    try:
        con = panel_db()
        cur = con.execute(
            "UPDATE users SET password_hash=?, salt=? WHERE username=?",
            (password_hash, salt, username),
        )
        con.commit()
        con.close()
        if cur.rowcount == 0:
            return "کاربر پیدا نشد"
    except Exception as e:
        return f"خطا در تغییر رمز: {e}"
    return f"رمز کاربر «{username}» تغییر کرد."


def handle(handler, data):
    action = data.get("action", "")
    username = safe_name(data.get("username", ""))
    client = safe_name(data.get("client", ""))

    if not username:
        handler.send_html(page("کاربران", users.body(_fetch_users(), "نام کاربری الزامی است"), "users"))
        return

    try:
        con = panel_db()
        row = con.execute(
            "SELECT status, COALESCE(client_name, '') AS client_name FROM users WHERE username=?",
            (username,),
        ).fetchone()
        con.close()
    except Exception:
        row = None

    if not row:
        handler.send_html(page("کاربران", users.body(_fetch_users(), "کاربر پیدا نشد"), "users"))
        return

    status = row["status"]
    assigned = row["client_name"]

    if action == "approve":
        if status == "pending":
            if not client:
                client = assigned
            if not client:
                handler.send_html(
                    page("کاربران", users.body(_fetch_users(), "برای تایید، نام کلاینت الزامی است"), "users")
                )
                return
            out = _approve_user(username, client)
        elif status == "disabled" and not assigned:
            if not client:
                handler.send_html(
                    page(
                        "کاربران",
                        users.body(_fetch_users(), "برای اختصاص کلاینت، نام کلاینت الزامی است"),
                        "users",
                    )
                )
                return
            out = _approve_user(username, client, reassigned=True)
        elif status == "rejected":
            if not client:
                client = assigned
            if not client:
                handler.send_html(
                    page("کاربران", users.body(_fetch_users(), "برای تایید، نام کلاینت الزامی است"), "users")
                )
                return
            out = _approve_user(username, client)
        elif status == "approved":
            handler.send_html(
                page("کاربران", users.body(_fetch_users(), "کاربر از قبل تایید شده"), "users")
            )
            return
        elif status == "disabled":
            handler.send_html(
                page(
                    "کاربران",
                    users.body(_fetch_users(), "برای فعال‌سازی از دکمه فعال‌سازی استفاده کنید"),
                    "users",
                )
            )
            return
        else:
            handler.send_html(
                page("کاربران", users.body(_fetch_users(), "این عملیات برای این کاربر مجاز نیست"), "users")
            )
            return

    elif action == "reject":
        if status != "pending":
            handler.send_html(
                page("کاربران", users.body(_fetch_users(), "فقط کاربران در انتظار قابل رد هستند"), "users")
            )
            return
        out = _reject_user(username)

    elif action == "disable":
        if status != "approved":
            handler.send_html(
                page("کاربران", users.body(_fetch_users(), "فقط کاربران تایید شده قابل غیرفعال‌سازی"), "users")
            )
            return
        out = _disable_user(username)

    elif action == "enable":
        if status != "disabled":
            handler.send_html(
                page("کاربران", users.body(_fetch_users(), "فقط کاربران غیرفعال قابل فعال‌سازی"), "users")
            )
            return
        if not assigned:
            handler.send_html(
                page(
                    "کاربران",
                    users.body(_fetch_users(), "ابتدا کلاینت جدید اختصاص دهید"),
                    "users",
                )
            )
            return
        out = _enable_user(username)

    elif action == "change-password":
        out = _change_password(username, data.get("new_password", ""))

    else:
        out = "عملیات ناشناخته"

    handler.send_html(page("کاربران", users.body(_fetch_users(), tail_message(out)), "users"))
