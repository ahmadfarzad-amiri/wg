import html

from client_panel.components.brand import brand_html
from client_panel.components.icons import nav_icon
from client_panel.components.modal import qr_modal_html
from client_panel.config import BRAND, VERSION


def head_assets():
    v = VERSION.replace(".", "")
    return (
        f'<link rel="stylesheet" href="/static/css/panel.css?v={v}">'
        f'<script src="/static/js/panel.js?v={v}" defer></script>'
    )


def page(title, body, user=None, active="dashboard", auth=False, extra_head=""):
    safe_title = html.escape(title)
    assets = head_assets() + extra_head

    if auth:
        return f"""<!doctype html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#0b1424">
<title>{safe_title} · {html.escape(BRAND)}</title>
{assets}
</head>
<body class="auth-page">
<a class="skip-link" href="#main">رفتن به محتوا</a>
{body}
</body>
</html>"""

    tabs = [
        ("/", "نمای کلی", "dashboard"),
        ("/support", "پشتیبانی", "support"),
        ("/settings", "تنظیمات", "settings"),
    ]

    def sidebar_nav():
        links = []
        for path, label, key in tabs:
            cls = "active" if active == key else ""
            links.append(
                f'<a class="{cls}" href="{path}" data-nav="{key}">'
                f'<span class="nav-icon">{nav_icon(key)}</span>{label}</a>'
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
                f'<span class="bottom-nav-label">{label}</span></a>'
            )
        return "\n  ".join(links)

    sidebar = f"""
<aside class="sidebar" id="sidebar">
  <div class="sidebar-top">
    <div class="brandmark" aria-hidden="true"></div>
    <div class="brandname">{brand_html()}</div>
    <div class="version">نسخه {html.escape(VERSION)}</div>
  </div>
  <nav class="nav nav-sidebar" id="sidebar-nav" aria-label="منوی کناری">
    {sidebar_nav()}
  </nav>
</aside>
"""

    return f"""<!doctype html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#172337">
<title>{safe_title} · {html.escape(BRAND)}</title>
{assets}
</head>
<body class="app-shell">
<a class="skip-link" href="#main">رفتن به محتوا</a>
<div class="layout">
{sidebar}
<main class="main" id="main">{body}</main>
</div>
<nav class="bottom-nav" aria-label="منوی پایین">
  {bottom_nav()}
</nav>
{qr_modal_html()}
</body>
</html>"""
