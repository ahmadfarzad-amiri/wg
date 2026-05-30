import html


def body(msg="", show_config_actions=False):
    notice = f'<div class="notice" role="alert">{html.escape(msg)}</div>' if msg else ""
    config_actions = ""
    if show_config_actions:
        config_actions = """
<section class="card card-spaced">
  <h3>کانفیگ جدید</h3>
  <p class="hint">کلیدهای VPN عوض شده — کانفیگ جدید را دانلود یا QR را اسکن کنید.</p>
  <div class="settings-actions">
    <a class="btn" href="/config">دانلود کانفیگ</a>
    <button type="button" class="btn dark" data-qr-open>نمایش QR</button>
  </div>
</section>
"""
    return f"""
<h1>تنظیمات</h1>
<p class="subtitle">مدیریت رمز عبور و خروج از پنل</p>

<section class="card">
  <h3>تغییر رمز عبور</h3>
  <p class="hint">تغییر رمز، کلیدهای WireGuard را هم عوض می‌کند — کانفیگ جدید را دانلود کنید.</p>
  {notice}
  <form method="post" action="/settings/password" class="form-stack">
    <label for="old_password">رمز فعلی</label>
    <input id="old_password" name="old_password" type="password" autocomplete="current-password" required>
    <label for="new_password">رمز جدید</label>
    <input id="new_password" name="new_password" type="password" autocomplete="new-password" required minlength="6">
    <label for="confirm_password">تکرار رمز جدید</label>
    <input id="confirm_password" name="confirm_password" type="password" autocomplete="new-password" required>
    <button type="submit">تغییر رمز و ساخت کانفیگ جدید</button>
  </form>
</section>

{config_actions}

<section class="card card-spaced">
  <h3>حساب کاربری</h3>
  <div class="settings-actions">
    <form method="post" action="/logout">
      <button type="submit" class="bad">خروج از حساب</button>
    </form>
  </div>
</section>
"""
