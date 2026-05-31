import html
import time

from client_panel.components.layout import page
from client_panel.components.notice import notice
from client_panel.core.i18n import t
from client_panel.core.wireguard import can_request_for_user
from client_panel.db import db


def handle_request(handler, user, data):
    action = data.get("action", "")
    if action not in ["renew", "enable"]:
        handler.send_html(
            page(
                t("page.error"),
                f"<h1>{html.escape(t('request.invalid_title'))}</h1>",
                user,
            ),
            400,
        )
        return
    allowed, reason = can_request_for_user(user, action)
    if not allowed:
        handler.send_html(
            page(
                t("page.forbidden"),
                f"<h1>{html.escape(t('request.forbidden_title'))}</h1>"
                f"{notice(reason, variant='error')}"
                f"<a class='btn' href='/support'>{html.escape(t('support.back'))}</a>",
                user,
            ),
            403,
        )
        return
    con = db()
    con.execute(
        "INSERT INTO requests(user_id,action,status,created_at) VALUES(?,?,?,?)",
        (user["id"], action, "pending", int(time.time())),
    )
    con.commit()
    con.close()
    handler.redirect("/support")
