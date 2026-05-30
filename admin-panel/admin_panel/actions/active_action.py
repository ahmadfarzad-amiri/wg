from admin_panel.components.layout import page
from admin_panel.core.shell import safe_name
from admin_panel.core.wireguard import (
    active_list_hint,
    all_client_status,
    live_disconnect_client,
)
from admin_panel.views import active


def handle(handler, data):
    action = data.get("action", "")
    client = safe_name(data.get("client", ""))

    if not client:
        handler.send_html(
            page("آنلاین", active.body([], "نام کلاینت الزامی است"), "active"), 400
        )
        return

    if action == "disconnect":
        msg = live_disconnect_client(client)
    else:
        msg = "عملیات ناشناخته"

    online = [c for c in all_client_status() if c["active"]]
    handler.send_html(
        page(
            "آنلاین",
            active.body(online, msg, wg_hint=active_list_hint()),
            "active",
        )
    )
