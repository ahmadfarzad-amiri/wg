import html
import time

from client_panel.components.layout import page
from client_panel.core.wireguard import can_request_for_user
from client_panel.db import db


def handle_request(handler, user, data):
    action = data.get("action", "")
    if action not in ["renew", "enable"]:
        handler.send_html(page("خطا", "<h1>درخواست نامعتبر</h1>", user), 400)
        return
    allowed, reason = can_request_for_user(user, action)
    if not allowed:
        handler.send_html(
            page(
                "مجاز نیست",
                f"<h1>درخواست مجاز نیست</h1><div class='notice'>{html.escape(reason)}</div>"
                "<a class='btn' href='/support'>بازگشت به پشتیبانی</a>",
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
