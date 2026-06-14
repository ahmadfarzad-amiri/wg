"""Handle POST to /xray-action."""
import logging

from admin_panel.core.audit import log_admin_action
from admin_panel.core.i18n import t, tf

log = logging.getLogger(__name__)


def _audit(handler, action, detail=""):
    from admin_panel.server import security, session
    log_admin_action(action, detail, actor=session.admin_actor(), ip=security.client_ip(handler))


def handle(handler, data):
    from admin_panel.core import xray as xcore

    action = (data.get("action") or "").strip()

    if action == "add-client":
        name = (data.get("name") or "").strip()
        if not name:
            handler.flash("/xray", t("xray.name_required"))
            return
        safe = xcore._safe_name(name)
        ok, result = xcore.add_client(safe)
        if ok:
            _audit(handler, "xray_add_client", safe)
            handler.flash("/xray", tf("xray.added_ok", name=safe))
        else:
            log.error("Failed to add Xray client %s: %s", safe, result)
            handler.flash("/xray", f"{t('xray.add_failed')}: {result}")

    elif action == "delete-client":
        name = (data.get("name") or "").strip()
        safe = xcore._safe_name(name) if name else ""
        if not safe:
            handler.flash("/xray", t("xray.name_required"))
            return
        ok = xcore.delete_client(safe)
        if ok:
            _audit(handler, "xray_delete_client", safe)
            handler.flash("/xray", tf("xray.deleted_ok", name=safe))
        else:
            handler.flash("/xray", t("xray.delete_failed"))

    else:
        handler.flash("/xray", t("msg.unknown_action"))
