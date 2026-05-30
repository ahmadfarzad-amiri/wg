import html
import time

from admin_panel.config import admin_url
from admin_panel.core.i18n import t, tf
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
        items = f'<div class="hint">{html.escape(t("empty.no_users"))}</div>'
    return f'<div class="statrow">{items}</div>'


def _top_usage_table(top_usage):
    if not top_usage:
        return f'<p class="hint">{html.escape(t("empty.no_data"))}</p>'
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
  <thead><tr><th>{html.escape(t("col.client"))}</th><th>{html.escape(t("col.usage"))}</th><th>{html.escape(t("dashboard.top_usage.limit_pct"))}</th><th>{html.escape(t("col.last_connection"))}</th></tr></thead>
  <tbody>{rows}</tbody>
</table>
"""


def _recent_requests_table(recent, label_action, label_status):
    if not recent:
        return f'<p class="hint">{html.escape(t("empty.no_requests"))}</p>'

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
  <thead><tr><th>{html.escape(t("col.id"))}</th><th class="col-user">{html.escape(t("col.user"))}</th><th>{html.escape(t("col.subject"))}</th><th>{html.escape(t("col.status"))}</th><th>{html.escape(t("col.date"))}</th></tr></thead>
  <tbody>{rows}</tbody>
</table>
"""


def body(metrics):
    k = metrics["kpis"]
    traffic = metrics["traffic"]
    total_clients = k["total_clients"]

    return f"""
<h1>{html.escape(t("dashboard.title"))}</h1>
<p class="subtitle">{html.escape(t("dashboard.subtitle"))}</p>

<section class="card quick-access-card">
  <h3>{html.escape(t("dashboard.quick_access"))}</h3>
  <div class="quick-actions">
    <a class="btn" href="{admin_url('/clients')}">{html.escape(t("dashboard.manage_clients"))}</a>
    <a class="btn dark" href="{admin_url('/users')}">{html.escape(t("dashboard.approve_users"))}</a>
    <a class="btn dark" href="{admin_url('/requests')}">{html.escape(t("dashboard.review_requests"))}</a>
    <a class="btn dark" href="{admin_url('/tools')}">{html.escape(t("dashboard.tools"))}</a>
  </div>
</section>

<div class="grid kpi-grid">
  {_kpi(t("dashboard.kpi.total_clients"), k["total_clients"])}
  {_kpi(t("dashboard.kpi.online"), k["active"], hint=tf("dashboard.kpi.online_hint", pct=k["online_pct"]))}
  {_kpi(t("dashboard.kpi.registered_users"), k["total_users"], hint=tf("dashboard.kpi.pending_users_hint", n=k["pending_users"]))}
  {_kpi(t("dashboard.kpi.open_requests"), k["pending_requests"], hint=tf("dashboard.kpi.today_hint", n=k["requests_today"]))}
</div>

<div class="grid kpi-grid kpi-grid-secondary">
  {_kpi(t("dashboard.kpi.disabled"), k["disabled"])}
  {_kpi(t("dashboard.kpi.expired"), k["expired"])}
  {_kpi(t("dashboard.kpi.over_limit"), k["over_limit"])}
  {_kpi(t("dashboard.kpi.expiring_soon"), k["expiring_soon"], hint=t("dashboard.kpi.expiring_hint"))}
</div>

<div class="dashboard-grid">
  <section class="card">
    <h3>{html.escape(t("dashboard.health.title"))}</h3>
    <p class="hint">{html.escape(tf("dashboard.health.hint", n=total_clients))}</p>
    {_health_bars(metrics["health"], total_clients)}
  </section>

  <section class="card">
    <h3>{html.escape(t("dashboard.users.title"))}</h3>
    <p class="hint">{html.escape(tf("dashboard.users.hint", users=k["total_users"], requests=k["requests_week"]))}</p>
    {_user_breakdown(metrics["users"], metrics["label_user_status"])}
    <div class="actions">
      <a class="btn btn-sm" href="{admin_url('/users')}">{html.escape(t("dashboard.users.manage"))}</a>
    </div>
  </section>

  <section class="card">
    <h3>{html.escape(t("dashboard.traffic.title"))}</h3>
    <p class="hint">{html.escape(t("dashboard.traffic.hint"))}</p>
    <div class="statrow">
      <div class="item"><div class="label">{html.escape(t("dashboard.traffic.total"))}</div><div class="value">{html.escape(traffic['used'])}</div></div>
      <div class="item"><div class="label">{html.escape(t("dashboard.traffic.rx"))}</div><div class="value">{html.escape(traffic['rx'])}</div></div>
      <div class="item"><div class="label">{html.escape(t("dashboard.traffic.tx"))}</div><div class="value">{html.escape(traffic['tx'])}</div></div>
    </div>
    <div class="label" style="margin-top:18px">{html.escape(tf("dashboard.traffic.avg_label", n=traffic['limited_count']))}</div>
    <div class="progress" role="progressbar" aria-valuenow="{traffic['avg_usage_pct']}" aria-valuemin="0" aria-valuemax="100">
      <div class="bar" style="width:{traffic['avg_usage_pct']}%"></div>
    </div>
    <div class="hint">{html.escape(tf("dashboard.traffic.avg_hint", pct=traffic['avg_usage_pct']))}</div>
  </section>

  <section class="card">
    <h3>{html.escape(t("dashboard.top_usage.title"))}</h3>
    <div class="table-wrap">{_top_usage_table(metrics["top_usage"])}</div>
    <div class="actions">
      <a class="btn dark btn-sm" href="{admin_url('/clients')}">{html.escape(t("dashboard.all_clients"))}</a>
      <a class="btn dark btn-sm" href="{admin_url('/active')}">{html.escape(tf("dashboard.online_link", n=k['active']))}</a>
    </div>
  </section>
</div>

<section class="card card-spaced">
  <h3>{html.escape(t("dashboard.recent_requests.title"))}</h3>
  <div class="table-wrap recent-requests-wrap">{_recent_requests_table(metrics["recent_requests"], label_action_short, label_request_status_short)}</div>
  <div class="actions" style="margin-top:12px">
    <a class="btn dark btn-sm" href="{admin_url('/requests')}">{html.escape(t("dashboard.all_requests"))}</a>
  </div>
</section>
"""
