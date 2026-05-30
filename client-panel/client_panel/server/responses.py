import mimetypes
import os
import subprocess
import urllib.parse
from pathlib import Path

from client_panel.config import CLIENT_DIR, STATE_DIR, STATIC_DIR
from client_panel.core.wireguard import parse_meta


def post_data(handler):
    length = int(handler.headers.get("Content-Length", "0") or 0)
    raw = handler.rfile.read(length).decode("utf-8", errors="ignore")
    return {k: v[0] for k, v in urllib.parse.parse_qs(raw).items()}


def serve_static(handler):
    raw_path = handler.path.split("?", 1)[0]
    rel = raw_path.replace("/static/", "", 1).lstrip("/")
    base = Path(STATIC_DIR).resolve()
    target = (base / rel).resolve()

    if not str(target).startswith(str(base)) or not target.exists() or not target.is_file():
        handler.send_response(404)
        handler.end_headers()
        return True

    data = target.read_bytes()
    ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
    if str(target).endswith(".woff2"):
        ctype = "font/woff2"
    elif str(target).endswith(".ttf"):
        ctype = "font/ttf"
    elif str(target).endswith(".css"):
        ctype = "text/css; charset=utf-8"
    elif str(target).endswith(".js"):
        ctype = "text/javascript; charset=utf-8"

    handler.send_response(200)
    handler.send_header("Content-Type", ctype)
    handler.send_header("Cache-Control", "public, max-age=31536000, immutable")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)
    return True


def send_plain(handler, content, filename=None):
    raw = content.encode("utf-8")
    handler.send_response(200)
    handler.send_header("Content-Type", "text/plain; charset=utf-8")
    if filename:
        handler.send_header("Content-Disposition", f'attachment; filename="{filename}"')
    handler.send_header("Content-Length", str(len(raw)))
    handler.end_headers()
    handler.wfile.write(raw)


def send_html(handler, content, code=200):
    from client_panel.server import security

    raw = content.encode("utf-8")
    token = security.get_csrf_token(handler)
    handler.send_response(code)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    security.apply_security_headers(handler)
    security.set_csrf_cookie(handler, token)
    handler.send_header("Content-Length", str(len(raw)))
    handler.end_headers()
    handler.wfile.write(raw)


def send_svg(handler, content, code=200):
    raw = content.encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "image/svg+xml; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(raw)))
    handler.end_headers()
    handler.wfile.write(raw)


def redirect(handler, path):
    handler.send_response(302)
    handler.send_header("Location", path)
    handler.end_headers()


def _conf_public_key(conf_path):
    with open(conf_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if line.startswith("PrivateKey"):
                priv = line.split("=", 1)[1].strip()
                if not priv:
                    return ""
                try:
                    return subprocess.check_output(
                        ["wg", "pubkey"],
                        input=priv,
                        text=True,
                        stderr=subprocess.DEVNULL,
                    ).strip()
                except Exception:
                    return ""
    return ""


def _ensure_valid_client_config(client_name):
    """Raise ValueError when client config is missing or out of sync with meta."""
    meta = parse_meta(client_name)
    if not meta.get("PUBLIC_KEY"):
        raise ValueError("متادیتای کلاینت پیدا نشد.")

    conf_path = os.path.join(CLIENT_DIR, f"{client_name}.conf")
    if not os.path.isfile(conf_path):
        raise ValueError("فایل کانفیگ پیدا نشد.")

    conf_pub = _conf_public_key(conf_path)
    meta_pub = meta.get("PUBLIC_KEY", "")
    if conf_pub and meta_pub and conf_pub != meta_pub:
        raise ValueError("کانفیگ با کلید فعلی سرور هماهنگ نیست. رمز را تغییر دهید یا از پشتیبانی بخواهید.")


def get_user_config_text(user):
    if not user:
        return None, "ابتدا وارد شوید."
    if user["status"] != "approved" or not user["client_name"]:
        return None, "کانفیگ اختصاص داده نشده است."
    try:
        _ensure_valid_client_config(user["client_name"])
    except ValueError as exc:
        return None, str(exc)
    conf_path = os.path.join(CLIENT_DIR, f"{user['client_name']}.conf")
    with open(conf_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read(), None


def build_qr_svg(user):
    config_text, err = get_user_config_text(user)
    if err:
        return None, err
    try:
        qr = subprocess.check_output(
            ["qrencode", "-t", "SVG", "-o", "-"],
            input=config_text,
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return None, "qrencode روی سرور نصب نیست یا خطا داده است."
    return qr, None
