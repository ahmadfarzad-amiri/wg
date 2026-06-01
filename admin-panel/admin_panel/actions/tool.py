import os

from admin_panel.config import DEFAULT_DAYS, DEFAULT_LIMIT, WG_CLIENT
from admin_panel.core.audit import log_admin_action
from admin_panel.core.i18n import t
from admin_panel.core.shell import CLIENT_CMD_TIMEOUT, run, tail_message

DEPLOY_DIR = os.environ.get("WG_DEPLOY_DIR", "/opt/wg/deploy")


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
    elif action == "change-entry":
        new_ep = (data.get("new_endpoint") or "").strip()
        old_ip = (data.get("old_ip") or "").strip()
        if not new_ep:
            out = t("msg.entry_endpoint_required")
        else:
            cmd = ["bash", os.path.join(DEPLOY_DIR, "change-entry-server.sh"), "--new", new_ep]
            if old_ip:
                cmd = [
                    "bash",
                    os.path.join(DEPLOY_DIR, "change-entry-server.sh"),
                    "--old",
                    old_ip,
                    "--new",
                    new_ep,
                ]
            out = run(cmd, timeout=120)
    elif action == "change-exit":
        exit_ip = (data.get("exit_ip") or "").strip()
        exit_pub = (data.get("exit_tunnel_pub") or "").strip()
        exit_port = (data.get("exit_tunnel_port") or "51821").strip()
        if not exit_ip or not exit_pub:
            out = t("msg.exit_fields_required")
        else:
            out = run(
                [
                    "bash",
                    os.path.join(DEPLOY_DIR, "change-exit-server.sh"),
                    "--exit-ip",
                    exit_ip,
                    "--tunnel-pub",
                    exit_pub,
                    "--port",
                    exit_port,
                ],
                timeout=120,
            )
    else:
        out = t("msg.unknown_action")

    log_admin_action(f"tool_{action}", (out or "")[:500])
    handler.flash("/tools", tail_message(out))
