from admin_panel.components.notice import notice
from admin_panel.config import admin_url


def body(msg=""):
    from admin_panel.core.audit import recent_audit
    import html
    import time

    audit_rows = recent_audit(10)
    audit_html = ""
    if audit_rows:
        items = []
        for action, detail, created_at in audit_rows:
            when = time.strftime("%Y-%m-%d %H:%M", time.localtime(created_at))
            items.append(
                f"<li><code>{html.escape(action)}</code> — {html.escape(detail or '')} "
                f"<span class='muted'>({when})</span></li>"
            )
        audit_html = f"""
<section class="card card-spaced">
  <h3>گزارش اخیر</h3>
  <ul class="audit-list">{''.join(items)}</ul>
</section>
"""
    return f"""
<h1>ابزارها</h1>
<p class="subtitle">عملیات نگهداری سیستم</p>
{notice(msg, role="alert")}

<section class="card">
  <h3>نگهداری</h3>
  <div class="actions">
    <form class="inline-form" method="post" action="{admin_url("/tool-action")}">
      <input type="hidden" name="action" value="enforce">
      <button type="submit" data-confirm="اجرای enforce ممکن است کلاینت‌های منقضی را غیرفعال کند. ادامه؟">اجرای wg-client enforce</button>
    </form>
    <form class="inline-form" method="post" action="{admin_url("/tool-action")}">
      <input type="hidden" name="action" value="restart-panel">
      <button type="submit" class="dark" data-confirm="پنل کاربر راه‌اندازی مجدد شود؟">راه‌اندازی مجدد پنل کاربر</button>
    </form>
    <form class="inline-form" method="post" action="{admin_url("/tool-action")}">
      <input type="hidden" name="action" value="import-existing">
      <button type="submit" class="dark" data-confirm="کانفیگ‌های موجود از دیسک وارد شوند؟">وارد کردن کانفیگ‌های موجود</button>
    </form>
  </div>
</section>
{audit_html}
"""
