from admin_panel.config import DEFAULT_DAYS, DEFAULT_LIMIT, WG_CLIENT
from admin_panel.core.audit import log_admin_action
from admin_panel.core.i18n import t
from admin_panel.core.shell import CLIENT_CMD_TIMEOUT, run, tail_message


def handle(handler, data):
    action = data.get("action", "")

    if action == "enforce":
        out = run([WG_CLIENT, "enforce"], timeout=CLIENT_CMD_TIMEOUT)
    elif action == "restart-panel":
        out = run(["systemctl", "restart", "wg-panel"])
    elif action == "import-existing":
        out = run(
            [
                "bash",
                "-lc",
                f"DAYS={DEFAULT_DAYS} LIMIT={DEFAULT_LIMIT} SINGLE_MODE=ip wg-client-import-existing",
            ],
            timeout=CLIENT_CMD_TIMEOUT,
        )
    else:
        out = t("msg.unknown_action")

    log_admin_action(f"tool_{action}", out or "")
    handler.flash("/tools", tail_message(out))
