import html

from admin_panel.components.auth_card import auth_card
from admin_panel.components.notice import notice
from admin_panel.config import admin_url


def body(msg=""):
    form = f"""
{notice(msg, role="alert")}
<form method="post" action="{admin_url("/login")}" class="form-stack">
  <label for="username">نام کاربری</label>
  <input id="username" name="username" autocomplete="username" required>
  <label for="password">رمز عبور</label>
  <input id="password" name="password" type="password" autocomplete="current-password" required>
  <button type="submit" class="btn-block">ورود به پنل مدیریت</button>
</form>
"""
    return auth_card(
        "ورود مدیر",
        "برای مدیریت کلاینت‌ها، کاربران و درخواست‌ها وارد شوید.",
        form,
    )
