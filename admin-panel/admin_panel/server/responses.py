"""HTTP response helpers."""
import mimetypes
import urllib.parse
from pathlib import Path

from admin_panel.config import BASE, STATIC_DIR, admin_url


def clean_path(handler):
    path = handler.path.split("?", 1)[0]
    path = path.rstrip("/") or "/"
    base = BASE.rstrip("/")
    if base and (path == base or path.startswith(base + "/")):
        path = path[len(base) :] or "/"
    return path


def post_data(handler):
    length = int(handler.headers.get("Content-Length", "0") or 0)
    raw = handler.rfile.read(length).decode("utf-8", errors="ignore")
    return {k: v[0] for k, v in urllib.parse.parse_qs(raw).items()}


def serve_static(handler):
    path = clean_path(handler)
    if not path.startswith("/static/"):
        handler.send_response(404)
        handler.end_headers()
        return True
    rel = path[len("/static/") :].lstrip("/")
    base = Path(STATIC_DIR).resolve()
    target = (base / rel).resolve()

    if (
        not str(target).startswith(str(base))
        or not target.exists()
        or not target.is_file()
    ):
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
    handler.send_header("Cache-Control", "public, max-age=3600, must-revalidate")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)
    return True


def send_html(handler, content, code=200):
    raw = content.encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Content-Length", str(len(raw)))
    handler.end_headers()
    handler.wfile.write(raw)


def redirect(handler, path):
    handler.send_response(302)
    handler.send_header("Location", admin_url(path))
    handler.end_headers()


def send_config_file(handler, client_name, raw):
    handler.send_response(200)
    handler.send_header("Content-Type", "text/plain; charset=utf-8")
    handler.send_header(
        "Content-Disposition", f'attachment; filename="{client_name}.conf"'
    )
    handler.send_header("Content-Length", str(len(raw)))
    handler.end_headers()
    handler.wfile.write(raw)
