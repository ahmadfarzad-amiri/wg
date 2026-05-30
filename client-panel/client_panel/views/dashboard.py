import html

from client_panel.components.status import client_status_section


def body(user, s):
    expiry_bar = 0 if s["days_left"] == "نامحدود" else s.get("expiry_percent", 0)
    return f"""
<h1>نمای کلی</h1>
<p class="subtitle">وضعیت اشتراک و اتصال VPN</p>

<div class="grid">
  <section class="card">
    <h3>مصرف حجم <span class="badge {s['badge']}">{html.escape(s['state'])}</span></h3>
    <div class="label">درصد مصرف</div>
    <div class="progress" role="progressbar" aria-valuenow="{s['percent']}" aria-valuemin="0" aria-valuemax="100">
      <div class="bar" style="width:{s['percent']}%"></div>
    </div>
    <div class="statrow">
      <div class="item"><div class="label">باقی‌مانده</div><div class="value">{html.escape(s['remaining'])}</div></div>
      <div class="item"><div class="label">مصرف‌شده</div><div class="value">{html.escape(s['used'])}</div></div>
      <div class="item"><div class="label">سقف حجم</div><div class="value">{html.escape(s['limit'])}</div></div>
    </div>
  </section>

  <section class="card">
    <h3>مدت اشتراک <span class="badge {s['badge']}">{html.escape(s['state'])}</span></h3>
    <div class="label">زمان باقی‌مانده</div>
    <div class="progress" role="progressbar" aria-valuenow="{expiry_bar}" aria-valuemin="0" aria-valuemax="100">
      <div class="bar bar-cyan" style="width:{expiry_bar}%"></div>
    </div>
    <div class="statrow">
      <div class="item"><div class="label">تاریخ انقضا</div><div class="value">{html.escape(s['expires'])}</div></div>
      <div class="item"><div class="label">روز باقی‌مانده</div><div class="value">{html.escape(s['days_left'])}</div></div>
      <div class="item"><div class="label">وضعیت</div><div class="value">{html.escape(s['state'])}</div></div>
    </div>
  </section>
</div>

<section class="card card-spaced">
  <h3>جزئیات اتصال</h3>
  <div class="grid">
    <div class="item"><div class="label">نام کانفیگ</div><div class="value">{html.escape(user['client_name'])}</div></div>
    <div class="item"><div class="label">آدرس VPN</div><div class="value">{html.escape(s['ip'])}</div></div>
    <div class="item"><div class="label">آخرین handshake</div><div class="value">{html.escape(s['handshake'])}</div></div>
    <div class="item"><div class="label">نقطه اتصال</div><div class="value">{html.escape(s['endpoint'])}</div></div>
    <div class="item item-wide"><div class="label">محدودیت دستگاه</div><div class="value">{html.escape(s['single_text'])}</div></div>
    <div class="item"><div class="label">دلیل غیرفعال</div><div class="value">{html.escape(s['disabled_reason'])}</div></div>
  </div>
</section>

{client_status_section(s)}
"""


def body_pending():
    return """
<h1>نمای کلی</h1>
<p class="subtitle">پس از تایید ادمین، وضعیت کانفیگ اینجا نمایش داده می‌شود.</p>
<div class="notice">حساب شما در انتظار تایید ادمین است.</div>
"""


def body_inactive():
    return "<h1>نمای کلی</h1><div class='notice'>حساب شما فعال نیست.</div>"


def body_no_config():
    return "<h1>نمای کلی</h1><div class='notice'>کانفیگ اختصاص داده شده پیدا نشد.</div>"
