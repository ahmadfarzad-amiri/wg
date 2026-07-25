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


_TAB_PATHS = {
    "dashboard": "/",
    "clients": "/clients",
    "users": "/users",
    "requests": "/requests",
    "active": "/active",
    "tools": "/tools",
    "xray": "/xray",
    "settings": "/settings",
}

_PRIMARY_TABS = [
    ("/", "nav.dashboard", "dashboard"),
    ("/clients", "nav.clients", "clients"),
    ("/users", "nav.users", "users"),
    ("/requests", "nav.requests", "requests"),
    ("/active", "nav.active", "active"),
]

_MORE_TABS = [
    ("/tools", "nav.tools", "tools"),
    ("/xray", "nav.xray", "xray"),
    ("/settings", "nav.settings", "settings"),
]


def _nav_link(path, label, key, active, *, bottom=False):
    if bottom:
        cls = "bottom-nav-item"
        if active == key:
            cls += " active"
        return (
            f'<a class="{cls}" href="{admin_url(path)}" data-nav="{key}">'
            f'<span class="bottom-nav-icon">{nav_icon(key, bottom=True)}</span>'
            f'<span class="bottom-nav-label">{html.escape(label)}</span></a>'
        )
    cls = "active" if active == key else ""
    return (
        f'<a class="{cls}" href="{admin_url(path)}" data-nav="{key}">'
        f'<span class="nav-icon">{nav_icon(key)}</span>{html.escape(label)}</a>'
    )


def page(title, body, active="dashboard", auth=False, extra_head="", next_path="/"):
    safe_title = html.escape(title)
    assets = head_assets() + extra_head
    lang = html_lang()
    direction = html_dir()
    shell_class = "app-shell admin-shell" if not auth else "auth-page"
    if direction == "ltr":
        shell_class += " ltr"
    if auth:
        lang_next = next_path or "/login"
    elif next_path and next_path not in ("/", "") and next_path != _TAB_PATHS.get(active):
        lang_next = next_path
    else:
        lang_next = _TAB_PATHS.get(active, next_path or "/")
    more_active = active in {k for _, _, k in _MORE_TABS}

    if auth:
        return f"""<!doctype html>
<html lang="{lang}" dir="{direction}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#0b1424">
<meta name="color-scheme" content="dark">
<title>{safe_title} · {html.escape(t("admin_label"))}</title>
{assets}
</head>
<body class="{shell_class}">
<a class="skip-link" href="#main">{html.escape(t("skip_link"))}</a>
<div class="shell-header-bar">
  <div class="shell-header-lang" dir="ltr">{lang_toggle_html(lang_next)}</div>
</div>
{body}
<div id="toast-root" class="toast-root" aria-live="polite"></div>
</body>
</html>"""

    primary_sidebar = "\n    ".join(
        _nav_link(path, t(label_key), key, active)
        for path, label_key, key in _PRIMARY_TABS
    )
    more_sidebar = "\n    ".join(
        _nav_link(path, t(label_key), key, active)
        for path, label_key, key in _MORE_TABS
    )

    bottom_primary = "\n  ".join(
        _nav_link(path, t(label_key), key, active, bottom=True)
        for path, label_key, key in _PRIMARY_TABS
    )
    more_cls = "bottom-nav-item bottom-nav-more"
    if more_active:
        more_cls += " active"
    more_sheet_links = "\n    ".join(
        _nav_link(path, t(label_key), key, active)
        for path, label_key, key in _MORE_TABS
    )

    sidebar = f"""
<aside class="sidebar" id="sidebar">
  <div class="sidebar-top">
    <div class="brandmark" aria-hidden="true"></div>
    <div class="brandname">{brand_html()}</div>
  </div>
  <nav class="nav nav-sidebar" id="sidebar-nav" aria-label="{html.escape(t("nav.sidebar"))}">
    {primary_sidebar}
    <div class="nav-section-label">{html.escape(t("nav.more"))}</div>
    {more_sidebar}
  </nav>
  <div class="sidebar-footer">
    <div class="sidebar-lang" dir="ltr">{lang_toggle_html(lang_next)}</div>
  </div>
</aside>
"""

    return f"""<!doctype html>
<html lang="{lang}" dir="{direction}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#172337">
<meta name="color-scheme" content="dark">
<title>{safe_title} · {html.escape(t("admin_label"))}</title>
{assets}
</head>
<body class="{shell_class}">
<a class="skip-link" href="#main">{html.escape(t("skip_link"))}</a>
<div class="layout">
{sidebar}
<main class="main" id="main">
<div class="shell-header-bar shell-header-bar--desktop-hide">
  <div class="shell-header-lang" dir="ltr">{lang_toggle_html(lang_next)}</div>
</div>
{body}
</main>
</div>
<nav class="bottom-nav" aria-label="{html.escape(t("nav.bottom"))}">
  {bottom_primary}
  <button type="button" class="{more_cls}" id="more-nav-btn" aria-expanded="false" aria-controls="more-sheet">
    <span class="bottom-nav-icon">{nav_icon("more", bottom=True)}</span>
    <span class="bottom-nav-label">{html.escape(t("nav.more"))}</span>
  </button>
</nav>
<div class="more-sheet" id="more-sheet" hidden>
  <div class="more-sheet-backdrop" data-more-close></div>
  <div class="more-sheet-panel" role="dialog" aria-modal="true" aria-labelledby="more-sheet-title">
    <div class="more-sheet-head">
      <div class="more-sheet-title" id="more-sheet-title">{html.escape(t("nav.more"))}</div>
      <button type="button" class="btn-icon more-sheet-close" data-more-close aria-label="{html.escape(t("modal.close"))}">&times;</button>
    </div>
    <nav class="more-sheet-nav">{more_sheet_links}</nav>
  </div>
</div>
<div id="toast-root" class="toast-root" aria-live="polite"></div>
</body>
</html>"""
