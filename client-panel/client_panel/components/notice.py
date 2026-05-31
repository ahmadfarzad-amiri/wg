import html


def notice(msg="", role="status", variant="info"):
    """Flash/action feedback rendered as a toast (not an inline box)."""
    if not msg:
        return ""
    safe_variant = html.escape(variant, quote=True)
    return (
        f'<template class="toast-payload" data-variant="{safe_variant}">'
        f"{html.escape(msg)}</template>"
    )


def notice_html(html_body="", role="status", css_class="notice"):
    """Persistent inline informational blocks (hints, empty states)."""
    if not html_body:
        return ""
    return f'<div class="{css_class}" role="{role}">{html_body}</div>'
