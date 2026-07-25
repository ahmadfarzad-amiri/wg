import html
import os
import shutil
import subprocess
import time

from admin_panel.config import admin_url
from admin_panel.core.i18n import t, tf
from admin_panel.core.labels import badge_request_status, badge_user_status, label_action_short, label_request_status_short
from admin_panel.core.statuses import UserStatus
from admin_panel.core.wireguard import human_bytes


def _wg_health_row():
    """Return a compact server health status row for the dashboard."""
    from admin_panel.config import WG_IF, DB_PATH

    rows = []

    # WireGuard interface
    if shutil.which("wg"):
        try:
            out = subprocess.check_output(
                ["wg", "show", WG_IF, "peers"],
                text=True, stderr=subprocess.DEVNULL, timeout=5,
            ).strip()
            peer_count = len(out.splitlines()) if out else 0
            rows.append(("ok", tf("dashboard.health.wg_up", n=peer_count)))
        except Exception:
            rows.append(("bad", t("dashboard.health.wg_down")))
    else:
        rows.append(("warn", t("dashboard.health.wg_missing")))

    # Database
    db_ok = os.path.isfile(DB_PATH)
    rows.append(("ok" if db_ok else "bad",
                 t("dashboard.health.db_ok") if db_ok else t("dashboard.health.db_missing")))

    # Xray (optional)
    if shutil.which("xray") or os.path.exists("/usr/local/bin/xray"):
        try:
            subprocess.check_output(
                ["systemctl", "is-active", "xray"],
                text=True, stderr=subprocess.DEVNULL, timeout=3,
            )
            rows.append(("ok", t("dashboard.health.xray_active")))
        except Exception:
            rows.append(("warn", t("dashboard.health.xray_inactive")))

    items = "".join(
        f'<div class="item"><span class="badge {cls}">{html.escape(label)}</span></div>'
        for cls, label in rows
    )
    return f'<div class="statrow health-statrow">{items}</div>'


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
        (UserStatus.APPROVED, users.get(UserStatus.APPROVED, 0)),
        (UserStatus.PENDING, users.get(UserStatus.PENDING, 0)),
        (UserStatus.DISABLED, users.get(UserStatus.DISABLED, 0)),
        (UserStatus.REJECTED, users.get(UserStatus.REJECTED, 0)),
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


def _attention_strip(k):
    chips = []
    pending_users = int(k.get("pending_users") or 0)
    pending_requests = int(k.get("pending_requests") or 0)
    if pending_users > 0:
        chips.append(
            f'<a class="attention-chip" href="{admin_url("/users")}">'
            f'{html.escape(tf("dashboard.attention.pending_users", n=pending_users))}</a>'
        )
    if pending_requests > 0:
        chips.append(
            f'<a class="attention-chip" href="{admin_url("/requests")}">'
            f'{html.escape(tf("dashboard.attention.open_requests", n=pending_requests))}</a>'
        )
    if not chips:
        return ""
    return f"""
<section class="attention-strip" aria-label="{html.escape(t("dashboard.attention.title"))}">
  <span class="attention-strip-label">{html.escape(t("dashboard.attention.title"))}</span>
  <div class="attention-chips">{"".join(chips)}</div>
</section>
"""


def _top_usage_table(top_usage):
    if not top_usage:
        return f'<p class="hint">{html.escape(t("empty.no_data"))}</p>'
    rows = ""
    cards = ""
    for c in top_usage:
        limit = (
            f"{c['used_bytes'] * 100 // c['limit_bytes']}%"
            if c["limit_bytes"] > 0
            else "—"
        )
        name = html.escape(c["name"])
        used = html.escape(human_bytes(c["used_bytes"]))
        limit_esc = html.escape(limit)
        last = html.escape(c["last"])
        rows += f"""
<tr>
  <td>{name}</td>
  <td>{used}</td>
  <td>{limit_esc}</td>
  <td>{last}</td>
</tr>
"""
        cards += f"""
<div class="rowcard">
  <div class="rowcard-title">{name}</div>
  <div class="rowline"><div class="rowlabel">{html.escape(t("col.usage"))}</div><div class="rowvalue">{used}</div></div>
  <div class="rowline"><div class="rowlabel">{html.escape(t("dashboard.top_usage.limit_pct"))}</div><div class="rowvalue">{limit_esc}</div></div>
  <div class="rowline"><div class="rowlabel">{html.escape(t("col.last_seen"))}</div><div class="rowvalue">{last}</div></div>
</div>
"""
    return f"""
<div class="list-items-host">
  <div class="table-scroll desktop-table">
    <table class="table">
      <thead><tr><th>{html.escape(t("col.client"))}</th><th>{html.escape(t("col.usage"))}</th><th>{html.escape(t("dashboard.top_usage.limit_pct"))}</th><th>{html.escape(t("col.last_seen"))}</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </div>
  <div class="mobile-cards">{cards}</div>
</div>
"""


def _recent_requests_table(recent, label_action, label_status):
    if not recent:
        return f'<p class="hint">{html.escape(t("empty.no_requests"))}</p>'

    rows = ""
    cards = ""
    for r in recent:
        badge = badge_request_status(r["status"])
        status_label = label_status(r["status"])
        action_label = label_action(r["action"])
        ts_date = time.strftime("%m/%d", time.localtime(int(r["created_at"])))
        ts_clock = time.strftime("%H:%M", time.localtime(int(r["created_at"])))
        username = html.escape(r["username"])
        action_esc = html.escape(action_label)
        status_esc = html.escape(status_label)
        rows += f"""
<tr>
  <td>#{r['id']}</td>
  <td class="col-user">{username}</td>
  <td>{action_esc}</td>
  <td><span class="badge {badge}">{status_esc}</span></td>
  <td class="col-time"><span class="time-stack"><span>{ts_date}</span><span>{ts_clock}</span></span></td>
</tr>
"""
        cards += f"""
<div class="rowcard">
  <div class="rowcard-title">{html.escape(tf("request.row_title", id=r['id']))}</div>
  <div class="rowline"><div class="rowlabel">{html.escape(t("col.user"))}</div><div class="rowvalue">{username}</div></div>
  <div class="rowline"><div class="rowlabel">{html.escape(t("col.request_type"))}</div><div class="rowvalue">{action_esc}</div></div>
  <div class="rowline"><div class="rowlabel">{html.escape(t("col.status"))}</div><div class="rowvalue"><span class="badge {badge}">{status_esc}</span></div></div>
  <div class="rowline"><div class="rowlabel">{html.escape(t("col.date"))}</div><div class="rowvalue">{ts_date} {ts_clock}</div></div>
</div>
"""

    return f"""
<div class="list-items-host">
  <div class="table-scroll recent-requests-wrap desktop-table">
    <table class="table table-recent">
      <thead><tr><th>{html.escape(t("col.id"))}</th><th class="col-user">{html.escape(t("col.user"))}</th><th>{html.escape(t("col.request_type"))}</th><th>{html.escape(t("col.status"))}</th><th>{html.escape(t("col.date"))}</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </div>
  <div class="mobile-cards">{cards}</div>
</div>
"""


def body(metrics):
    k = metrics["kpis"]
    traffic = metrics["traffic"]
    total_clients = k["total_clients"]

    return f"""
<h1>{html.escape(t("dashboard.title"))}</h1>
<p class="subtitle">{html.escape(t("dashboard.subtitle"))}</p>

<div class="page-stack">
{_attention_strip(k)}
<section class="card quick-access-card">
  <h3>{html.escape(t("dashboard.quick_access"))}</h3>
  <div class="quick-actions">
    <a class="btn" href="{admin_url('/clients')}">{html.escape(t("dashboard.manage_clients"))}</a>
    <a class="btn dark" href="{admin_url('/users')}">{html.escape(t("dashboard.approve_users"))}</a>
    <a class="btn dark" href="{admin_url('/requests')}">{html.escape(t("dashboard.review_requests"))}</a>
    <a class="btn dark" href="{admin_url('/tools')}">{html.escape(t("dashboard.tools"))}</a>
  </div>
  {_wg_health_row()}
</section>

<div class="grid kpi-grid">
  {_kpi(t("dashboard.kpi.total_clients"), k["total_clients"])}
  {_kpi(t("dashboard.kpi.online"), k["active"], hint=tf("dashboard.kpi.online_hint", pct=k["online_pct"]))}
  {_kpi(t("dashboard.kpi.registered_users"), k["total_users"], hint=tf("dashboard.kpi.pending_users_hint", n=k["pending_users"]))}
  {_kpi(t("dashboard.kpi.open_requests"), k["pending_requests"], hint=tf("dashboard.kpi.today_hint", n=k["requests_today"]))}
</div>

<details class="kpi-details card">
  <summary>{html.escape(t("dashboard.kpi.more_stats"))}</summary>
  <div class="grid kpi-grid kpi-grid-secondary">
    {_kpi(t("dashboard.kpi.disabled"), k["disabled"])}
    {_kpi(t("dashboard.kpi.expired"), k["expired"])}
    {_kpi(t("dashboard.kpi.over_limit"), k["over_limit"])}
    {_kpi(t("dashboard.kpi.expiring_soon"), k["expiring_soon"], hint=t("dashboard.kpi.expiring_hint"))}
  </div>
</details>

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
    <div class="actions card-footer-actions">
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
    <div class="label metric-spaced">{html.escape(tf("dashboard.traffic.avg_label", n=traffic['limited_count']))}</div>
    <div class="progress" role="progressbar" aria-valuenow="{traffic['avg_usage_pct']}" aria-valuemin="0" aria-valuemax="100">
      <div class="bar" style="width:{traffic['avg_usage_pct']}%"></div>
    </div>
    <div class="hint">{html.escape(tf("dashboard.traffic.avg_hint", pct=traffic['avg_usage_pct']))}</div>
  </section>

  <section class="card">
    <h3>{html.escape(t("dashboard.top_usage.title"))}</h3>
    {_top_usage_table(metrics["top_usage"])}
    <div class="actions card-footer-actions">
      <a class="btn dark btn-sm" href="{admin_url('/clients')}">{html.escape(t("dashboard.all_clients"))}</a>
      <a class="btn dark btn-sm" href="{admin_url('/active')}">{html.escape(tf("dashboard.online_link", n=k['active']))}</a>
    </div>
  </section>
</div>

<section class="card">
  <h3>{html.escape(t("dashboard.recent_requests.title"))}</h3>
  {_recent_requests_table(metrics["recent_requests"], label_action_short, label_request_status_short)}
  <div class="actions card-footer-actions">
    <a class="btn dark btn-sm" href="{admin_url('/requests')}">{html.escape(t("dashboard.all_requests"))}</a>
  </div>
</section>
</div>
"""
