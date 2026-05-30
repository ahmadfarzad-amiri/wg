import html

from client_panel.components.forms import request_controls
from client_panel.core.labels import badge_request_status, label_action, label_request_status
from client_panel.core.wireguard import human_time


def body(user, rows, s=None):
    tr = ""
    for r in rows:
        tr += (
            f"<tr><td>TKT-{r['id']}</td>"
            f"<td>{html.escape(label_action(r['action']))}</td>"
            f"<td><span class=\"badge {badge_request_status(r['status'])}\">"
            f"{html.escape(label_request_status(r['status']))}</span></td>"
            f"<td>{human_time(r['created_at'])}</td></tr>"
        )
    if not tr:
        tr = '<tr><td colspan="4" class="empty">هنوز درخواستی ثبت نشده است.</td></tr>'

    controls = ""
    if user["status"] == "approved" and user["client_name"] and s:
        controls = request_controls(s, include_download=False)
    else:
        controls = '<div class="notice">حساب شما هنوز تایید یا به کانفیگ متصل نشده است.</div>'

    return f"""
<h1>پشتیبانی</h1>
<p class="subtitle">درخواست‌های تمدید و فعال‌سازی و تاریخچه تیکت‌ها</p>
<section class="card">
  {controls}
  <div class="table-wrap">
    <table class="table">
      <thead><tr><th>شناسه</th><th>موضوع</th><th>وضعیت</th><th>تاریخ</th></tr></thead>
      <tbody>{tr}</tbody>
    </table>
  </div>
</section>
"""
