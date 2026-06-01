import html

from client_panel.components.brand import brand_html


def auth_card(title, subtitle, form_body, footer_link_href, footer_link_label):
    return f"""
<div class="authwrap">
  <div class="auth" id="main">
    <div class="brandmark" aria-hidden="true"></div>
    <div class="brandname">{brand_html()}</div>
    <h2>{html.escape(title)}</h2>
    <p class="subtitle auth-subtitle">{html.escape(subtitle)}</p>
    {form_body}
    <hr class="auth-divider" aria-hidden="true">
    <a class="btn dark btn-block" href="{footer_link_href}">{html.escape(footer_link_label)}</a>
  </div>
</div>
"""
