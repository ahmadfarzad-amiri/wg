import io
import mimetypes
import os
import subprocess
import urllib.parse
import zipfile
from pathlib import Path

from client_panel.config import CLIENT_DIR, STATE_DIR, STATIC_DIR
from client_panel.core.i18n import t
from client_panel.core.wireguard import assigned_client_names_for_user, parse_meta, primary_client_for_user


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


def send_zip(handler, data, filename):
    handler.send_response(200)
    handler.send_header("Content-Type", "application/zip")
    handler.send_header("Content-Disposition", f'attachment; filename="{filename}"')
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


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
        raise ValueError(t("error.meta_not_found"))

    conf_path = os.path.join(CLIENT_DIR, f"{client_name}.conf")
    if not os.path.isfile(conf_path):
        raise ValueError(t("error.conf_not_found"))

    conf_pub = _conf_public_key(conf_path)
    meta_pub = meta.get("PUBLIC_KEY", "")
    if conf_pub and meta_pub and conf_pub != meta_pub:
        raise ValueError(t("error.conf_key_mismatch"))


def _zip_entry_name(client_name, label=""):
    label = (label or "").strip()
    if label:
        safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in label)
        return f"{safe}.conf"
    return f"{client_name}.conf"


def get_user_config_entries(user):
    if not user:
        return None, t("error.sign_in_first")
    if user["status"] != "approved":
        return None, t("error.config_not_assigned")

    from client_panel.db.user_configs import configs_for_user

    entries = []
    configs = configs_for_user(user["id"])
    if configs:
        for row in configs:
            name = row["client_name"]
            try:
                _ensure_valid_client_config(name)
            except ValueError as exc:
                return None, str(exc)
            conf_path = os.path.join(CLIENT_DIR, f"{name}.conf")
            with open(conf_path, "r", encoding="utf-8", errors="ignore") as f:
                entries.append((_zip_entry_name(name, row.get("label")), f.read(), name))
        return entries, None

    primary = primary_client_for_user(user)
    if not primary:
        return None, t("error.config_not_assigned")
    try:
        _ensure_valid_client_config(primary)
    except ValueError as exc:
        return None, str(exc)
    conf_path = os.path.join(CLIENT_DIR, f"{primary}.conf")
    with open(conf_path, "r", encoding="utf-8", errors="ignore") as f:
        return [(_zip_entry_name(primary), f.read(), primary)], None


def get_user_config_text(user, client_name=None):
    if not user:
        return None, t("error.sign_in_first")
    if user["status"] != "approved":
        return None, t("error.config_not_assigned")

    name = (client_name or "").strip() or primary_client_for_user(user)
    if not name:
        return None, t("error.config_not_assigned")

    allowed = assigned_client_names_for_user(user)
    if name not in allowed:
        return None, t("error.config_not_assigned")

    try:
        _ensure_valid_client_config(name)
    except ValueError as exc:
        return None, str(exc)
    conf_path = os.path.join(CLIENT_DIR, f"{name}.conf")
    with open(conf_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read(), None


def build_configs_zip(user):
    entries, err = get_user_config_entries(user)
    if err:
        return None, err
    if not entries:
        return None, t("error.config_not_assigned")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename, content, _ in entries:
            zf.writestr(filename, content)
    return buf.getvalue(), None


def build_qr_svg(user, client_name=None):
    config_text, err = get_user_config_text(user, client_name=client_name)
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
        return None, t("error.qrencode")
    return qr, None
