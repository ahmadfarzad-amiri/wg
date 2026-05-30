import html

from admin_panel.components.notice import notice
from admin_panel.config import admin_url
from admin_panel.core.auth import admin_username


def body(msg=""):
    username = admin_username()
    return f"""
<h1>تنظیمات</h1>
<p class="subtitle">حساب مدیر و خروج از پنل</p>

<div class="settings-grid">
  <section class="card">
    <h3>تغییر رمز عبور</h3>
    {notice(msg, role="alert")}
    <form method="post" action="{admin_url("/settings/password")}" class="form-stack">
      <label>نام کاربری مدیر</label>
      <input value="{html.escape(username)}" disabled>
      <label for="old_password">رمز فعلی</label>
      <input id="old_password" name="old_password" type="password" autocomplete="current-password" required>
      <label for="new_password">رمز جدید</label>
      <input id="new_password" name="new_password" type="password" autocomplete="new-password" required minlength="8">
      <label for="confirm_password">تکرار رمز جدید</label>
      <input id="confirm_password" name="confirm_password" type="password" autocomplete="new-password" required>
      <button type="submit">تغییر رمز عبور</button>
    </form>
  </section>

  <section class="card">
    <h3>نشست</h3>
    <p class="hint">خروج از پنل مدیریت</p>
    <form method="post" action="{admin_url("/logout")}" class="form-stack">
      <button type="submit" class="bad">خروج از حساب</button>
    </form>
  </section>
</div>
"""
