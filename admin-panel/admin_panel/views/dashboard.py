import html
import time

from admin_panel.config import admin_url
from admin_panel.core.labels import badge_request_status, badge_user_status, label_action_short, label_request_status_short
from admin_panel.core.wireguard import human_bytes


def _kpi(label, value, *, hint=""):
    hint_html = f'<div class="kpi-hint">{html.escape(hint)}</div>' if hint else ""
    return f"""
<div class="card kpi">
  <div class="label">{html.escape(label)}</div>
  <div class="num">{html.escape(str(value))}</div>
  {hint_html}
</div>
"""


def _health_bars(health, total):
    rows = ""
    for _key, label, count, badge in health:
        pct = round(count * 100 / total) if total else 0
        rows += f"""
<div class="metric-row">
  <div class="metric-head">
    <span>{html.escape(label)}</span>
    <span class="badge {badge}">{count} ({pct}%)</span>
  </div>
  <div class="progress" role="progressbar" aria-valuenow="{pct}" aria-valuemin="0" aria-valuemax="100">
    <div class="bar bar-cyan" style="width:{pct}%"></div>
  </div>
</div>
"""
    return rows


def _user_breakdown(users, label_fn):
    items = ""
    for status, count in (
        ("approved", users.get("approved", 0)),
        ("pending", users.get("pending", 0)),
        ("disabled", users.get("disabled", 0)),
        ("rejected", users.get("rejected", 0)),
    ):
        if count <= 0:
            continue
        badge = badge_user_status(status)
        items += f"""
<div class="item">
  <div class="label">{html.escape(label_fn(status))}</div>
  <div class="value"><span class="badge {badge}">{count}</span></div>
</div>
"""
    if not items:
        items = '<div class="hint">کاربری ثبت نشده</div>'
    return f'<div class="statrow">{items}</div>'


def _top_usage_table(top_usage):
    if not top_usage:
        return '<p class="hint">داده‌ای موجود نیست</p>'
    rows = ""
    for c in top_usage:
        limit = (
            f"{c['used_bytes'] * 100 // c['limit_bytes']}%"
            if c["limit_bytes"] > 0
            else "—"
        )
        rows += f"""
<tr>
  <td>{html.escape(c['name'])}</td>
  <td>{html.escape(human_bytes(c['used_bytes']))}</td>
  <td>{html.escape(limit)}</td>
  <td>{html.escape(c['last'])}</td>
</tr>
"""
    return f"""
<table class="table">
  <thead><tr><th>کلاینت</th><th>مصرف</th><th>درصد سقف</th><th>آخرین اتصال</th></tr></thead>
  <tbody>{rows}</tbody>
</table>
"""


def _recent_requests_table(recent, label_action, label_status):
    if not recent:
        return '<p class="hint">درخواستی ثبت نشده</p>'

    rows = ""
    for r in recent:
        badge = badge_request_status(r["status"])
        status_label = label_status(r["status"])
        action_label = label_action(r["action"])
        ts_date = time.strftime("%m/%d", time.localtime(int(r["created_at"])))
        ts_clock = time.strftime("%H:%M", time.localtime(int(r["created_at"])))
        rows += f"""
<tr>
  <td>#{r['id']}</td>
  <td class="col-user">{html.escape(r['username'])}</td>
  <td>{html.escape(action_label)}</td>
  <td><span class="badge {badge}">{html.escape(status_label)}</span></td>
  <td class="col-time"><span class="time-stack"><span>{ts_date}</span><span>{ts_clock}</span></span></td>
</tr>
"""

    return f"""
<table class="table table-recent">
  <thead><tr><th>شناسه</th><th class="col-user">کاربر</th><th>موضوع</th><th>وضعیت</th><th>زمان</th></tr></thead>
  <tbody>{rows}</tbody>
</table>
"""


def body(metrics):
    k = metrics["kpis"]
    t = metrics["traffic"]
    total_clients = k["total_clients"]

    return f"""
<h1>داشبورد</h1>
<p class="subtitle">آمار و تحلیل کلی سیستم WireGuard</p>

<section class="card quick-access-card">
  <h3>دسترسی سریع</h3>
  <div class="quick-actions">
    <a class="btn" href="{admin_url('/clients')}">مدیریت کلاینت‌ها</a>
    <a class="btn dark" href="{admin_url('/users')}">تایید کاربران</a>
    <a class="btn dark" href="{admin_url('/requests')}">بررسی درخواست‌ها</a>
    <a class="btn dark" href="{admin_url('/tools')}">ابزارها</a>
  </div>
</section>

<div class="grid kpi-grid">
  {_kpi("کل کلاینت‌ها", k["total_clients"])}
  {_kpi("آنلاین", k["active"], hint=f"{k['online_pct']}% از کل")}
  {_kpi("کاربران ثبت‌شده", k["total_users"], hint=f"{k['pending_users']} در انتظار تایید")}
  {_kpi("درخواست باز", k["pending_requests"], hint=f"{k['requests_today']} امروز")}
</div>

<div class="grid kpi-grid kpi-grid-secondary">
  {_kpi("غیرفعال", k["disabled"])}
  {_kpi("منقضی", k["expired"])}
  {_kpi("اتمام حجم", k["over_limit"])}
  {_kpi("انقضای نزدیک", k["expiring_soon"], hint="کمتر از ۷ روز")}
</div>

<div class="dashboard-grid">
  <section class="card">
    <h3>وضعیت کلاینت‌ها</h3>
    <p class="hint">توزیع وضعیت {total_clients} کانفیگ</p>
    {_health_bars(metrics["health"], total_clients)}
  </section>

  <section class="card">
    <h3>کاربران پنل</h3>
    <p class="hint">مجموع {k['total_users']} حساب · {k['requests_week']} درخواست در ۷ روز اخیر</p>
    {_user_breakdown(metrics["users"], metrics["label_user_status"])}
    <div class="actions">
      <a class="btn btn-sm" href="{admin_url('/users')}">مدیریت کاربران</a>
    </div>
  </section>

  <section class="card">
    <h3>مصرف پهنای باند</h3>
    <p class="hint">جمع ترافیک live از رابط WireGuard</p>
    <div class="statrow">
      <div class="item"><div class="label">کل مصرف</div><div class="value">{html.escape(t['used'])}</div></div>
      <div class="item"><div class="label">دریافت (RX)</div><div class="value">{html.escape(t['rx'])}</div></div>
      <div class="item"><div class="label">ارسال (TX)</div><div class="value">{html.escape(t['tx'])}</div></div>
    </div>
    <div class="label" style="margin-top:18px">میانگین مصرف نسبت به سقف ({t['limited_count']} کلاینت محدود)</div>
    <div class="progress" role="progressbar" aria-valuenow="{t['avg_usage_pct']}" aria-valuemin="0" aria-valuemax="100">
      <div class="bar" style="width:{t['avg_usage_pct']}%"></div>
    </div>
    <div class="hint">{t['avg_usage_pct']}% میانگین استفاده از سقف حجم</div>
  </section>

  <section class="card">
    <h3>پرمصرف‌ترین کلاینت‌ها</h3>
    <div class="table-wrap">{_top_usage_table(metrics["top_usage"])}</div>
    <div class="actions">
      <a class="btn dark btn-sm" href="{admin_url('/clients')}">همه کلاینت‌ها</a>
      <a class="btn dark btn-sm" href="{admin_url('/active')}">آنلاین ({k['active']})</a>
    </div>
  </section>
</div>

<section class="card card-spaced">
  <h3>آخرین درخواست‌ها</h3>
  <div class="table-wrap recent-requests-wrap">{_recent_requests_table(metrics["recent_requests"], label_action_short, label_request_status_short)}</div>
  <div class="actions" style="margin-top:12px">
    <a class="btn dark btn-sm" href="{admin_url('/requests')}">همه درخواست‌ها</a>
  </div>
</section>
"""
