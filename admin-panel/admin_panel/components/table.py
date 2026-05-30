"""Responsive table + mobile card wrapper."""
import html

from admin_panel.core.i18n import t


def data_table(
    headers,
    rows_html,
    cards_html,
    *,
    empty=None,
    table_class="",
):
    empty = empty if empty is not None else t("empty.no_items")
    if not rows_html:
        cols = len(headers)
        rows_html = (
            f'<tr><td colspan="{cols}" class="empty">{html.escape(empty)}</td></tr>'
        )
        cards_html = f'<div class="rowcard empty-card">{html.escape(empty)}</div>'

    head = "".join(f"<th>{html.escape(h)}</th>" for h in headers)
    cls = html.escape(table_class.strip())
    table_attrs = f' class="table {cls}"' if cls else ' class="table"'
    return f"""
<div class="list-items-host" data-list-items data-list-kind="clients">
<div class="table-wrap desktop-table">
  <table{table_attrs}>
    <thead><tr>{head}</tr></thead>
    <tbody data-list-desktop>{rows_html}</tbody>
  </table>
</div>
<div class="mobile-cards" data-list-mobile>{cards_html}</div>
</div>
"""
