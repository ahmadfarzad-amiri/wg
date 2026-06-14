"""Subscription link generation and token management."""
import secrets

from client_panel.db.connection import db


def _generate_token():
    return secrets.token_urlsafe(32)


def get_or_create_sub_token(user_id):
    """Return existing sub_token for user, or create one."""
    con = db()
    row = con.execute(
        "SELECT sub_token FROM users WHERE id=?", (user_id,)
    ).fetchone()
    token = row["sub_token"] if row else None
    if not token:
        token = _generate_token()
        con.execute(
            "UPDATE users SET sub_token=? WHERE id=?", (token, user_id)
        )
        con.commit()
    con.close()
    return token


def rotate_sub_token(user_id):
    """Issue a new subscription token, invalidating the old one."""
    token = _generate_token()
    con = db()
    con.execute("UPDATE users SET sub_token=? WHERE id=?", (token, user_id))
    con.commit()
    con.close()
    return token


def user_by_sub_token(token):
    """Return the user row for a given subscription token, or None."""
    if not token or len(token) < 16:
        return None
    con = db()
    row = con.execute(
        "SELECT id, username, status, client_name, sub_token FROM users WHERE sub_token=?",
        (token,),
    ).fetchone()
    con.close()
    return dict(row) if row else None
