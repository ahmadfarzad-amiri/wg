from admin_panel.core.audit import log_admin_action
from admin_panel.core.shell import run, tail_message


def handle(handler, data):
    action = data.get("action", "")

    if action == "enforce":
        out = run([WG_CLIENT, "enforce"])
    elif action == "restart-panel":
        out = run(["systemctl", "restart", "wg-panel"])
    elif action == "import-existing":
        out = run(
            [
                "bash",
                "-lc",
                f"DAYS={DEFAULT_DAYS} LIMIT={DEFAULT_LIMIT} SINGLE_MODE=ip wg-client-import-existing",
            ]
        )
    else:
        out = "عملیات ناشناخته"

    log_admin_action(f"tool_{action}", out or "")
    handler.flash("/tools", tail_message(out))
