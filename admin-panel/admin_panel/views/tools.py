from admin_panel.components.notice import notice
from admin_panel.config import admin_url


def body(msg=""):
    return f"""
<h1>ابزارها</h1>
<p class="subtitle">عملیات نگهداری سیستم</p>
{notice(msg, role="alert")}

<section class="card">
  <h3>نگهداری</h3>
  <div class="actions">
    <form class="inline-form" method="post" action="{admin_url("/tool-action")}">
      <input type="hidden" name="action" value="enforce">
      <button type="submit">اجرای wg-client enforce</button>
    </form>
    <form class="inline-form" method="post" action="{admin_url("/tool-action")}">
      <input type="hidden" name="action" value="restart-panel">
      <button type="submit" class="dark">راه‌اندازی مجدد پنل کاربر</button>
    </form>
    <form class="inline-form" method="post" action="{admin_url("/tool-action")}">
      <input type="hidden" name="action" value="import-existing">
      <button type="submit" class="dark">وارد کردن کانفیگ‌های موجود</button>
    </form>
  </div>
</section>
"""
