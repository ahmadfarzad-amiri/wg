from admin_panel.core.audit import log_admin_action
from admin_panel.core.i18n import t
from admin_panel.core.shell import safe_name
from admin_panel.core.wireguard import live_disconnect_client


def handle(handler, data):
    action = data.get("action", "")
    client = safe_name(data.get("client", ""))

    if not client:
        handler.flash("/active", t("msg.client_name_required"), variant="error")
        return

    if action == "disconnect":
        msg = live_disconnect_client(client)
        log_admin_action("disconnect_client", client)
        handler.flash("/active", msg, variant="warn")
        return

    handler.flash("/active", t("msg.unknown_action"), variant="error")
