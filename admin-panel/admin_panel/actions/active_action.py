from admin_panel.core.audit import log_admin_action
from admin_panel.core.shell import safe_name
from admin_panel.core.wireguard import live_disconnect_client


def handle(handler, data):
    action = data.get("action", "")
    client = safe_name(data.get("client", ""))

    if not client:
        handler.flash("/active", "نام کلاینت الزامی است")
        return

    if action == "disconnect":
        msg = live_disconnect_client(client)
        log_admin_action("disconnect_client", client)
    else:
        msg = "عملیات ناشناخته"

    handler.flash("/active", msg)
