import html

from admin_panel.components.brand import brand_html


def auth_card(title, subtitle, form_body):
    return f"""
<div class="authwrap">
  <div class="auth" id="main">
    <div class="brandmark" aria-hidden="true"></div>
    <div class="brandname">{brand_html()}</div>
    <p class="admin-badge">پنل مدیریت</p>
    <h2>{html.escape(title)}</h2>
    <p class="subtitle">{html.escape(subtitle)}</p>
    {form_body}
  </div>
</div>
"""
