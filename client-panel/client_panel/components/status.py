import html

from client_panel.components.forms import request_controls


def client_status_section(s):
    state = s.get("state", "")

    if state == "فعال":
        box_class, title, desc = "ok", "اتصال فعال است", "اشتراک شما فعال است. در حال حاضر نیازی به تمدید یا فعال‌سازی نیست."
        renew_enabled, enable_enabled = False, False
    elif state == "منقضی":
        box_class, title, desc = "warn", "اشتراک منقضی شده", "مدت اشتراک به پایان رسیده. برای ادامه، درخواست تمدید ثبت کنید."
        renew_enabled, enable_enabled = True, False
    elif state == "اتمام حجم":
        box_class, title, desc = "warn", "حجم اشتراک تمام شده", "حجم مصرفی تمام شده. برای دریافت حجم جدید، درخواست تمدید ثبت کنید."
        renew_enabled, enable_enabled = True, False
    elif state == "غیرفعال":
        box_class, title, desc = "bad", "کانفیگ غیرفعال است", "کانفیگ غیرفعال شده. برای فعال‌سازی، درخواست فعال‌سازی ثبت کنید."
        renew_enabled, enable_enabled = False, True
    else:
        box_class, title, desc = "warn", "وضعیت نیازمند بررسی", "وضعیت کانفیگ مشخص نیست. با پشتیبانی تماس بگیرید."
        renew_enabled, enable_enabled = False, False

    renew_disabled = "" if renew_enabled else "disabled"
    enable_disabled = "" if enable_enabled else "disabled"
    renew_title = "" if renew_enabled else 'title="تمدید فقط وقتی اشتراک منقضی یا حجم تمام شده باشد."'
    enable_title = "" if enable_enabled else 'title="فعال‌سازی فقط وقتی کانفیگ غیرفعال باشد."'

    return f"""
<section class="statusbox {box_class}">
  <h3>{html.escape(title)}</h3>
  <p>{html.escape(desc)}</p>
  <div class="actions actions-center">
    <form method="post" action="/request">
      <input type="hidden" name="action" value="renew">
      <button type="submit" {renew_disabled} {renew_title}>درخواست تمدید</button>
    </form>
    <form method="post" action="/request">
      <input type="hidden" name="action" value="enable">
      <button type="submit" class="dark" {enable_disabled} {enable_title}>درخواست فعال‌سازی</button>
    </form>
  </div>
</section>

<div class="downloadbox">
  <div class="config-actions">
    <a class="btn" href="/config">دانلود کانفیگ</a>
    <button type="button" class="btn dark" data-qr-open>نمایش QR</button>
    <button type="button" class="btn dark" data-copy-config>کپی متن کانفیگ</button>
  </div>
  <span id="copy-config-msg" class="copymsg" role="status"></span>
  <span class="downloadhint">پس از تمدید یا تغییر رمز، کانفیگ جدید را دانلود و در WireGuard وارد کنید.</span>
</div>
"""
