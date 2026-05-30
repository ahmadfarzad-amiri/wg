import html

from client_panel.components.auth_card import auth_card


def body(msg=""):
    notice = f'<div class="notice" role="alert">{html.escape(msg)}</div>' if msg else ""
    form = f"""
{notice}
<form method="post" action="/login" class="form-stack">
  <label for="username">نام کاربری</label>
  <input id="username" name="username" autocomplete="username" required>
  <label for="password">رمز عبور</label>
  <input id="password" name="password" type="password" autocomplete="current-password" required>
  <button type="submit" class="btn-block">ورود به پنل</button>
</form>
"""
    return auth_card(
        "خوش آمدید",
        "برای مشاهده وضعیت VPN و مدیریت کانفیگ وارد شوید.",
        form,
        "/register",
        "ساخت حساب جدید",
    )
