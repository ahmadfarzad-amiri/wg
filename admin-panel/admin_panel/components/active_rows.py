import html

from admin_panel.config import admin_url
from admin_panel.core.i18n import t


def active_list(clients):
    rows = ""
    cards = ""

    for c in clients:
        name = html.escape(c["name"])
        ip = html.escape(c["ip"])
        endpoint = html.escape(c["endpoint"])
        rx = html.escape(c["rx"])
        tx = html.escape(c["tx"])
        last = html.escape(c["last"])
        age = int(c.get("handshake_age") or 999999999)
        fresh = "1" if age <= 60 else "0"
        idle = "0" if age <= 60 else "1"
        sort_name = html.escape(c["name"].lower())
        sort_ip = html.escape(c["ip"])
        rx_bytes = int(c.get("rx_bytes") or 0)
        tx_bytes = int(c.get("tx_bytes") or 0)
        search_text = html.escape(
            " ".join([c["name"], c["ip"], c["endpoint"], c["rx"], c["tx"], c["last"]]).lower()
        )

        disconnect_confirm = html.escape(t("active.disconnect_confirm"), quote=True)
        action = f"""
<form class="inline-form" method="post" action="{admin_url("/active-action")}">
  <input type="hidden" name="action" value="disconnect">
  <input type="hidden" name="client" value="{name}">
  <button type="submit" class="bad btn-sm" data-confirm="{disconnect_confirm}">{html.escape(t("active.disconnect"))}</button>
</form>
"""

        item_attrs = (
            f'data-list-item data-list-primary data-status="active" data-fresh="{fresh}" data-idle="{idle}" '
            f'data-sort-name="{sort_name}" data-sort-ip="{sort_ip}" data-sort-last="{age}" '
            f'data-sort-rx="{rx_bytes}" data-sort-tx="{tx_bytes}" data-search="{search_text}"'
        )

        rows += f"""
<div class="active-item" {item_attrs}>
  <div class="active-field active-field-name" data-label="{html.escape(t("col.client"))}">{name}</div>
  <div class="active-field active-field-ip" data-label="{html.escape(t("col.ip"))}">{ip}</div>
  <div class="active-field active-field-endpoint" data-label="{html.escape(t("col.endpoint"))}">{endpoint}</div>
  <div class="active-field active-field-rx" data-label="{html.escape(t("col.rx"))}">{rx}</div>
  <div class="active-field active-field-tx" data-label="{html.escape(t("col.tx"))}">{tx}</div>
  <div class="active-field active-field-last" data-label="{html.escape(t("col.last"))}">{last}</div>
  <div class="active-field active-field-actions" data-label="{html.escape(t("col.actions"))}">{action}</div>
</div>
"""

        cards += f"""
<div class="rowcard" {item_attrs}>
  <div class="rowcard-title">{name}</div>
  <div class="rowline"><div class="rowlabel">{html.escape(t("col.ip"))}</div><div class="rowvalue">{ip}</div></div>
  <div class="rowline"><div class="rowlabel">{html.escape(t("col.endpoint"))}</div><div class="rowvalue">{endpoint}</div></div>
  <div class="rowline"><div class="rowlabel">{html.escape(t("col.rx"))}</div><div class="rowvalue">{rx}</div></div>
  <div class="rowline"><div class="rowlabel">{html.escape(t("col.tx"))}</div><div class="rowvalue">{tx}</div></div>
  <div class="rowline"><div class="rowlabel">{html.escape(t("col.last_handshake"))}</div><div class="rowvalue">{last}</div></div>
  <div class="rowactions">{action}</div>
</div>
"""

    if not rows:
        empty = html.escape(t("empty.no_online"))
        rows = f'<div class="active-list-empty" data-list-static-empty>{empty}</div>'
        cards = f'<div class="rowcard empty-card">{empty}</div>'

    return f"""
<div class="list-items-host" data-list-items data-list-kind="active">
  <div class="active-list desktop-table">
    <div class="active-list-head">
      <div>{html.escape(t("col.client"))}</div>
      <div>{html.escape(t("col.ip"))}</div>
      <div>{html.escape(t("col.endpoint"))}</div>
      <div>{html.escape(t("col.rx"))}</div>
      <div>{html.escape(t("col.tx"))}</div>
      <div>{html.escape(t("col.last"))}</div>
      <div>{html.escape(t("col.actions"))}</div>
    </div>
    <div class="active-list-body">
      {rows}
    </div>
  </div>
  <div class="mobile-cards">{cards}</div>
</div>
"""
