from admin_panel.components.layout import page
from admin_panel.config import DEFAULT_DAYS, DEFAULT_LIMIT, WG_CLIENT
from admin_panel.core.shell import run, tail_message
from admin_panel.views import tools


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

    handler.send_html(page("ابزارها", tools.body(tail_message(out)), "tools"))
