import html

from client_panel.components.auth_card import auth_card


def body(msg=""):
    notice = f'<div class="notice" role="alert">{html.escape(msg)}</div>' if msg else ""
    form = f"""
{notice}
<form method="post" action="/register" class="form-stack">
  <label for="reg-username">نام کاربری</label>
  <input id="reg-username" name="username" autocomplete="username" required minlength="3">
  <label for="reg-password">رمز عبور</label>
  <input id="reg-password" name="password" type="password" autocomplete="new-password" required minlength="6">
  <p class="hint">حداقل ۳ کاراکتر برای نام کاربری و ۶ کاراکتر برای رمز.</p>
  <button type="submit" class="btn-block">ثبت نام</button>
</form>
"""
    return auth_card(
        "ثبت نام",
        "پس از ثبت نام، ادمین حساب شما را تایید و کانفیگ اختصاص می‌دهد.",
        form,
        "/login",
        "ورود به حساب موجود",
    )
