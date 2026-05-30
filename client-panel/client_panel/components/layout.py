import html

from client_panel.components.brand import brand_html
from client_panel.components.icons import nav_icon
from client_panel.components.modal import qr_modal_html
from client_panel.config import BRAND, VERSION
from client_panel.core.i18n import html_dir, html_lang, js_i18n_script, lang_toggle_html, t


def head_assets():
    v = VERSION.replace(".", "")
    return (
        f'<link rel="stylesheet" href="/static/css/panel.css?v={v}">'
        f"{js_i18n_script()}"
        f'<script src="/static/js/panel.js?v={v}" defer></script>'
    )


def page(title, body, user=None, active="dashboard", auth=False, extra_head="", next_path="/"):
    safe_title = html.escape(title)
    assets = head_assets() + extra_head
    lang = html_lang()
    direction = html_dir()
    shell_class = "app-shell" if not auth else "auth-page"
    if direction == "ltr":
        shell_class += " ltr"

    if auth:
        return f"""<!doctype html>
<html lang="{lang}" dir="{direction}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#0b1424">
<title>{safe_title} · {html.escape(BRAND)}</title>
{assets}
</head>
<body class="{shell_class}">
<a class="skip-link" href="#main">{html.escape(t("skip_link"))}</a>
<div class="lang-bar">{lang_toggle_html(next_path)}</div>
{body}
</body>
</html>"""

    tabs = [
        ("/", t("nav.dashboard"), "dashboard"),
        ("/support", t("nav.support"), "support"),
        ("/settings", t("nav.settings"), "settings"),
    ]

    def sidebar_nav():
        links = []
        for path, label, key in tabs:
            cls = "active" if active == key else ""
            links.append(
                f'<a class="{cls}" href="{path}" data-nav="{key}">'
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
                f'<a class="{cls}" href="{path}" data-nav="{key}">'
                f'<span class="bottom-nav-icon">{nav_icon(key, bottom=True)}</span>'
                f'<span class="bottom-nav-label">{html.escape(label)}</span></a>'
            )
        return "\n  ".join(links)

    sidebar = f"""
<aside class="sidebar" id="sidebar">
  <div class="sidebar-top">
    <div class="brandmark" aria-hidden="true"></div>
    <div class="brandname">{brand_html()}</div>
    <div class="version">{html.escape(t("version"))} {html.escape(VERSION)}</div>
    {lang_toggle_html(next_path)}
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
<title>{safe_title} · {html.escape(BRAND)}</title>
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
{qr_modal_html()}
</body>
</html>"""
