import html

from admin_panel.config import BRAND


def brand_html():
    parts = BRAND.split(None, 1)
    if len(parts) == 2:
        return f"{html.escape(parts[0])} <span>{html.escape(parts[1])}</span>"
    return html.escape(BRAND)
