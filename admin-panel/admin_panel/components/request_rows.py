import html
import time

from admin_panel.config import admin_url
from admin_panel.core.labels import badge_request_status, label_action, label_request_status


def _human_time(epoch):
    try:
        epoch = int(epoch)
    except (TypeError, ValueError):
        return "—"
    if epoch <= 0:
        return "—"
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(epoch))


def _request_actions(r, attr):
    return f"""
<div class="request-action-buttons">
  <form class="inline-form" method="post" action="{admin_url("/request-action")}">
    <input type="hidden" name="action" value="approve">
    <input type="hidden" name="id" value="{r['id']}">
    <button type="submit" class="btn-sm" {attr}>تایید</button>
  </form>
  <form class="inline-form" method="post" action="{admin_url("/request-action")}">
    <input type="hidden" name="action" value="reject">
    <input type="hidden" name="id" value="{r['id']}">
    <button type="submit" class="bad btn-sm" {attr}>رد</button>
  </form>
</div>
"""


def request_list(items):
    rows = ""
    cards = ""

    for r in items:
        can_process = r["status"] == "pending"
        attr = "" if can_process else 'disabled title="این درخواست قبلاً پردازش شده"'
        badge = badge_request_status(r["status"])
        action_label = html.escape(label_action(r["action"]))
        status_label = html.escape(label_request_status(r["status"]))
        username = html.escape(r["username"])
        client_name = html.escape(r["client_name"] or "—")
        client_name_raw = r["client_name"] or ""
        created = _human_time(r["created_at"])
        created_at = int(r["created_at"] or 0)
        actions = _request_actions(r, attr)
        sort_name = html.escape(r["username"].lower())
        sort_client = html.escape(client_name_raw.lower())
        sort_status = html.escape(r["status"])
        sort_action = html.escape(r["action"])
        search_text = html.escape(
            " ".join(
                [
                    str(r["id"]),
                    r["username"],
                    client_name_raw,
                    r["action"],
                    label_action(r["action"]),
                    r["status"],
                    label_request_status(r["status"]),
                    created,
                ]
            ).lower()
        )
        item_attrs = (
            f'data-list-item data-list-primary data-status="{sort_status}" data-sort-action="{sort_action}" '
            f'data-sort-id="{r["id"]}" data-sort-name="{sort_name}" data-sort-client="{sort_client}" '
            f'data-sort-created="{created_at}" data-search="{search_text}"'
        )

        rows += f"""
<div class="request-item" {item_attrs}>
  <div class="request-field request-field-id" data-label="شناسه">#{r['id']}</div>
  <div class="request-field request-field-user" data-label="کاربر">{username}</div>
  <div class="request-field request-field-client" data-label="کلاینت">{client_name}</div>
  <div class="request-field request-field-action" data-label="موضوع">{action_label}</div>
  <div class="request-field request-field-status" data-label="وضعیت"><span class="badge {badge}">{status_label}</span></div>
  <div class="request-field request-field-date" data-label="تاریخ">{created}</div>
  <div class="request-field request-field-actions" data-label="عملیات">{actions}</div>
</div>
"""

        cards += f"""
<div class="rowcard" {item_attrs}>
  <div class="rowcard-title">درخواست #{r['id']}</div>
  <div class="rowline"><div class="rowlabel">کاربر</div><div class="rowvalue">{username}</div></div>
  <div class="rowline"><div class="rowlabel">کلاینت</div><div class="rowvalue">{client_name}</div></div>
  <div class="rowline"><div class="rowlabel">موضوع</div><div class="rowvalue">{action_label}</div></div>
  <div class="rowline"><div class="rowlabel">وضعیت</div><div class="rowvalue"><span class="badge {badge}">{status_label}</span></div></div>
  <div class="rowline"><div class="rowlabel">تاریخ</div><div class="rowvalue">{created}</div></div>
  <div class="rowactions">{actions}</div>
</div>
"""

    if not rows:
        rows = '<div class="request-list-empty" data-list-static-empty>درخواستی ثبت نشده</div>'
        cards = '<div class="rowcard empty-card">درخواستی ثبت نشده</div>'

    return f"""
<div class="list-items-host" data-list-items data-list-kind="requests">
  <div class="request-list desktop-table">
    <div class="request-list-head">
      <div>شناسه</div>
      <div>کاربر</div>
      <div>کلاینت</div>
      <div>موضوع</div>
      <div>وضعیت</div>
      <div>تاریخ</div>
      <div>عملیات</div>
    </div>
    <div class="request-list-body">
      {rows}
    </div>
  </div>
  <div class="mobile-cards">{cards}</div>
</div>
"""
