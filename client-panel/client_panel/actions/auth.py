import re
import sqlite3
import time

from client_panel.core.auth import hash_password, verify_password
from client_panel.db import db


def handle_register(handler, data):
    username = re.sub(r"[^A-Za-z0-9_.-]", "_", data.get("username", "").strip())
    password = data.get("password", "")
    if len(username) < 3 or len(password) < 6:
        handler.render_register("نام کاربری حداقل ۳ و رمز حداقل ۶ کاراکتر باشد.")
        return
    ph, salt = hash_password(password)
    con = db()
    try:
        con.execute(
            "INSERT INTO users(username,password_hash,salt,status,created_at) VALUES(?,?,?,?,?)",
            (username, ph, salt, "pending", int(time.time())),
        )
        con.commit()
    except sqlite3.IntegrityError:
        con.close()
        handler.render_register("این نام کاربری قبلا ثبت شده است.")
        return
    con.close()
    handler.render_login("حساب ساخته شد. منتظر تایید ادمین باشید.")


def handle_login(handler, data):
    con = db()
    user = con.execute(
        "SELECT * FROM users WHERE username=?",
        (data.get("username", "").strip(),),
    ).fetchone()
    con.close()
    if not user or not verify_password(
        data.get("password", ""), user["password_hash"], user["salt"]
    ):
        handler.render_login("نام کاربری یا رمز عبور اشتباه است.")
        return
    handler.set_session(user["id"])


def handle_logout(handler):
    from http.cookies import SimpleCookie

    cookie = SimpleCookie(handler.headers.get("Cookie", ""))
    token = cookie.get("session")
    if token:
        con = db()
        con.execute("DELETE FROM sessions WHERE token=?", (token.value,))
        con.commit()
        con.close()
    handler.send_response(302)
    handler.send_header("Location", "/login")
    handler.send_header("Set-Cookie", "session=deleted; HttpOnly; SameSite=Strict; Path=/; Max-Age=0")
    handler.end_headers()
