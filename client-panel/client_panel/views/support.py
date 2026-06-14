import html

from client_panel.components.forms import request_controls
from client_panel.core.i18n import t
from client_panel.core.statuses import ClientState, UserStatus
from client_panel.core.labels import badge_request_status, label_action, label_request_status
from client_panel.core.wireguard import human_time, primary_client_for_user


def body(user, rows, s=None):
    tr = ""
    cards = ""
    for r in rows:
        action_label = html.escape(label_action(r["action"]))
        status_label = html.escape(label_request_status(r["status"]))
        badge = badge_request_status(r["status"])
        date = human_time(r["created_at"])
        tr += (
            f"<tr><td>#{r['id']}</td>"
            f"<td>{action_label}</td>"
            f"<td><span class=\"badge {badge}\">{status_label}</span></td>"
            f"<td class=\"col-date\">{date}</td></tr>"
        )
        cards += f"""
<div class="rowcard support-card">
  <div class="rowcard-title">#{r['id']} · {action_label}</div>
  <div class="rowline"><div class="rowlabel">{html.escape(t("support.col.status"))}</div><div class="rowvalue"><span class="badge {badge}">{status_label}</span></div></div>
  <div class="rowline"><div class="rowlabel">{html.escape(t("support.col.date"))}</div><div class="rowvalue">{date}</div></div>
</div>
"""
    if not tr:
        tr = f'<tr><td colspan="4" class="empty">{html.escape(t("support.empty"))}</td></tr>'
        cards = f'<div class="rowcard empty-card">{html.escape(t("support.empty"))}</div>'

    if user["status"] == UserStatus.APPROVED and primary_client_for_user(user) and s:
        controls = request_controls(s, include_download=False)
    elif user["status"] == UserStatus.PENDING:
        controls = f'<div class="notice notice-wait">{html.escape(t("support.waiting_approval"))}</div>'
    else:
        controls = f'<div class="notice">{html.escape(t("error.not_approved"))}</div>'

    return f"""
<h1>{html.escape(t("page.support"))}</h1>
<p class="subtitle">{html.escape(t("support.subtitle"))}</p>
<div class="page-stack">
<section class="card support-panel">
  <div class="support-actions-block">
    <h3>{html.escape(t("support.actions_title"))}</h3>
    {controls}
  </div>
  <div class="support-requests">
    <h3>{html.escape(t("support.history_title"))}</h3>
    <p class="hint support-legend">{html.escape(t("support.status_legend"))}</p>
    <div class="responsive-list">
      <div class="table-scroll desktop-only-table">
        <table class="table table-support">
          <thead><tr>
            <th>{html.escape(t("support.col.id"))}</th>
            <th>{html.escape(t("support.col.subject"))}</th>
            <th>{html.escape(t("support.col.status"))}</th>
            <th class="col-date">{html.escape(t("support.col.date"))}</th>
          </tr></thead>
          <tbody>{tr}</tbody>
        </table>
      </div>
      <div class="mobile-cards">{cards}</div>
    </div>
  </div>
</section>

<section class="card">
  <h3>{html.escape(t("support.conn_test_title"))}</h3>
  <p class="hint">{html.escape(t("support.conn_test_hint"))}</p>
  <div id="conn-test-results" class="statrow" hidden></div>
  <button type="button" class="btn btn-sm dark" id="conn-test-btn"
    data-test-url="/connection-test">{html.escape(t("support.conn_test_btn"))}</button>
</section>
</div>
"""
