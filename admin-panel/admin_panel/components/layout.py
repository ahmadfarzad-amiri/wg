import html

from admin_panel.components.brand import brand_html
from admin_panel.components.icons import nav_icon
from admin_panel.config import VERSION, admin_url
from admin_panel.core.i18n import html_dir, html_lang, js_i18n_script, lang_toggle_html, t


def head_assets():
    v = VERSION.replace(".", "")
    return (
        f'<link rel="stylesheet" href="{admin_url(f"/static/css/admin.css?v={v}")}">'
        f"{js_i18n_script()}"
        f'<script src="{admin_url(f"/static/js/admin.js?v={v}")}" defer></script>'
    )


def page(title, body, active="dashboard", auth=False, extra_head="", next_path="/"):
    safe_title = html.escape(title)
    assets = head_assets() + extra_head
    lang = html_lang()
    direction = html_dir()
    shell_class = "app-shell admin-shell" if not auth else "auth-page"
    if direction == "ltr":
        shell_class += " ltr"
    next_admin = admin_url(next_path)

    if auth:
        return f"""<!doctype html>
<html lang="{lang}" dir="{direction}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#0b1424">
<title>{safe_title} · {html.escape(t("admin_label"))}</title>
{assets}
</head>
<body class="{shell_class}">
<a class="skip-link" href="#main">{html.escape(t("skip_link"))}</a>
<div class="lang-bar">{lang_toggle_html(next_admin)}</div>
{body}
</body>
</html>"""

    tabs = [
        ("/", t("nav.dashboard"), "dashboard"),
        ("/clients", t("nav.clients"), "clients"),
        ("/users", t("nav.users"), "users"),
        ("/requests", t("nav.requests"), "requests"),
        ("/active", t("nav.active"), "active"),
        ("/tools", t("nav.tools"), "tools"),
        ("/settings", t("nav.settings"), "settings"),
    ]

    def sidebar_nav():
        links = []
        for path, label, key in tabs:
            cls = "active" if active == key else ""
            links.append(
                f'<a class="{cls}" href="{admin_url(path)}" data-nav="{key}">'
                f'<span class="nav-icon">{nav_icon(key)}</span>{html.escape(label)}</a>'
            )
        return "\n    ".join(links)

    def bottom_nav():
        links = []
        for path, label, key in tabs:
            cls = "bottom-nav-item"
            if active == key:
                cls += " active"
            links.append(
                f'<a class="{cls}" href="{admin_url(path)}" data-nav="{key}">'
                f'<span class="bottom-nav-icon">{nav_icon(key, bottom=True)}</span>'
                f'<span class="bottom-nav-label">{html.escape(label)}</span></a>'
            )
        return "\n  ".join(links)

    sidebar = f"""
<aside class="sidebar" id="sidebar">
  <div class="sidebar-top">
    <div class="brandmark" aria-hidden="true"></div>
    <div class="brandname">{brand_html()}</div>
    <div class="version">{html.escape(t("admin_label"))} · {html.escape(t("version"))} {html.escape(VERSION)}</div>
    {lang_toggle_html(next_admin)}
  </div>
  <nav class="nav nav-sidebar" id="sidebar-nav" aria-label="{html.escape(t("nav.sidebar"))}">
    {sidebar_nav()}
  </nav>
</aside>
"""

    return f"""<!doctype html>
<html lang="{lang}" dir="{direction}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#172337">
<title>{safe_title} · {html.escape(t("admin_label"))}</title>
{assets}
</head>
<body class="{shell_class}">
<a class="skip-link" href="#main">{html.escape(t("skip_link"))}</a>
<div class="layout">
{sidebar}
<main class="main" id="main">{body}</main>
</div>
<nav class="bottom-nav" aria-label="{html.escape(t("nav.bottom"))}">
  {bottom_nav()}
</nav>
</body>
</html>"""
