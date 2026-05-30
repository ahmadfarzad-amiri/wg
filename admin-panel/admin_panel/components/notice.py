import html


def notice(msg="", role="status"):
    if not msg:
        return ""
    return f'<div class="notice" role="{role}">{html.escape(msg)}</div>'


def notice_html(html_body="", role="status", css_class="notice"):
    if not html_body:
        return ""
    return f'<div class="{css_class}" role="{role}">{html_body}</div>'
