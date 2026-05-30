"""Inline SVG navigation icons."""

_SVG = (
    'class="nav-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
    'aria-hidden="true"'
)

ICONS = {
    "dashboard": (
        f"<svg {_SVG}>"
        '<path d="M4 10.5 12 5l8 5.5V19a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1v-8.5Z"/>'
        '<path d="M10 19v-6h4v6"/>'
        "</svg>"
    ),
    "support": (
        f"<svg {_SVG}>"
        '<path d="M7 6h10a3 3 0 0 1 3 3v5a3 3 0 0 1-3 3H11l-4 3v-3a3 3 0 0 1-3-3V9a3 3 0 0 1 3-3Z"/>'
        "</svg>"
    ),
    "settings": (
        f"<svg {_SVG}>"
        '<path d="M4 8h16M4 12h16M4 16h16"/>'
        '<circle cx="8" cy="8" r="2.25" fill="currentColor" stroke="none"/>'
        '<circle cx="14" cy="12" r="2.25" fill="currentColor" stroke="none"/>'
        '<circle cx="10" cy="16" r="2.25" fill="currentColor" stroke="none"/>'
        "</svg>"
    ),
}


def nav_icon(key, *, bottom=False):
    svg = ICONS.get(key, ICONS["dashboard"])
    if not bottom:
        return svg
    return (
        svg.replace('class="nav-svg"', 'class="nav-svg bottom-svg"', 1).replace(
            'stroke-width="2"', 'stroke-width="2.25"', 1
        )
    )
