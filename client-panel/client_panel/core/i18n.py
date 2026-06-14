"""Lightweight fa/en translations."""
import html
import json
import os
import threading
import urllib.parse
from http.cookies import SimpleCookie

_local = threading.local()   # per-thread language state — safe in ThreadingHTTPServer
_DEFAULT = "fa"
_SUPPORTED = frozenset({"fa", "en"})


def _lang():
    """Return the language for the current request thread."""
    return getattr(_local, "lang", _DEFAULT)

_STRINGS = {
    "fa": {
        "skip_link": "رفتن به محتوا",
        "version": "نسخه",
        "lang_toggle": "English",
        "lang_toggle_label": "زبان",
        "nav.dashboard": "نمای کلی",
        "nav.support": "پشتیبانی",
        "nav.settings": "تنظیمات",
        "nav.sidebar": "منوی کناری",
        "nav.bottom": "منوی پایین",
        "auth.welcome": "خوش آمدید",
        "auth.login_sub": "برای مشاهده وضعیت VPN و مدیریت کانفیگ وارد شوید.",
        "auth.username": "نام کاربری",
        "auth.password": "رمز عبور",
        "auth.login_btn": "ورود به پنل",
        "auth.register_link": "ساخت حساب جدید",
        "auth.register_title": "ثبت نام",
        "auth.register_sub": "پس از ثبت نام، ادمین حساب شما را بررسی می‌کند.",
        "auth.register_btn": "ثبت نام",
        "auth.login_link": "ورود",
        "auth.register_hint": "حداقل ۳ کاراکتر برای نام کاربری و ۶ کاراکتر برای رمز.",
        "auth.register_invalid": "نام کاربری حداقل ۳ و رمز حداقل ۶ کاراکتر باشد.",
        "auth.username_taken": "این نام کاربری قبلا ثبت شده است.",
        "auth.register_success": "حساب ساخته شد. منتظر تایید ادمین باشید.",
        "auth.invalid_credentials": "نام کاربری یا رمز عبور اشتباه است.",
        "page.dashboard": "نمای کلی",
        "page.support": "پشتیبانی",
        "page.settings": "تنظیمات",
        "page.pending": "در انتظار تایید",
        "page.inactive": "غیرفعال",
        "page.no_config": "بدون کانفیگ",
        "page.copy_config": "کپی کانفیگ",
        "page.not_found": "صفحه پیدا نشد",
        "page.error": "خطا",
        "page.forbidden": "مجاز نیست",
        "dashboard.subtitle": "وضعیت اشتراک و اتصال VPN",
        "dashboard.pending": "حساب شما در انتظار تایید ادمین است.",
        "dashboard.pending_sub": "پس از تایید ادمین، وضعیت کانفیگ اینجا نمایش داده می‌شود.",
        "dashboard.inactive": "حساب شما فعال نیست.",
        "dashboard.no_config": "کانفیگ اختصاص داده شده پیدا نشد.",
        "dashboard.usage_pct": "درصد مصرف",
        "dashboard.remaining": "باقی‌مانده",
        "dashboard.used": "مصرف‌شده",
        "dashboard.limit": "سقف حجم",
        "dashboard.expiry_date": "تاریخ انقضا",
        "dashboard.days_left": "روز باقی‌مانده",
        "dashboard.status": "وضعیت",
        "dashboard.connection_details": "جزئیات اتصال",
        "dashboard.config_name": "نام کانفیگ",
        "dashboard.vpn_address": "آدرس VPN",
        "dashboard.last_handshake": "آخرین handshake",
        "dashboard.endpoint": "نقطه اتصال",
        "dashboard.device_limit": "محدودیت دستگاه",
        "dashboard.disable_reason": "دلیل غیرفعال",
        "dashboard.vpn_mode": "مسیر VPN",
        "dashboard.your_configs": "کانفیگ‌های شما",
        "dashboard.your_configs_hint": "می‌توانید هر کانفیگ را جداگانه دانلود کنید یا همه را یکجا از تنظیمات.",
        "dashboard.primary_config": "کانفیگ اصلی",
        "dashboard.download_one": "دانلود",
        "dashboard.data_usage": "مصرف حجم",
        "dashboard.subscription_period": "مدت اشتراک",
        "dashboard.time_remaining": "زمان باقی‌مانده",
        "settings.title": "تنظیمات",
        "settings.subtitle": "مدیریت رمز عبور و خروج از پنل",
        "settings.change_password": "تغییر رمز عبور",
        "settings.change_hint": "تغییر رمز، کلیدهای WireGuard را هم عوض می‌کند — کانفیگ جدید را دانلود کنید.",
        "settings.old_password": "رمز فعلی",
        "settings.new_password": "رمز جدید",
        "settings.confirm_password": "تکرار رمز جدید",
        "dashboard.account_info": "اطلاعات VPN",
        "dashboard.pending_hint": "پس از تایید ادمین، وضعیت اشتراک و دانلود کانفیگ اینجا نمایش داده می‌شود.",
        "dashboard.inactive_sub": "حساب شما غیرفعال است",
        "dashboard.no_config_sub": "هنوز کانفیگ VPN به شما اختصاص داده نشده",
        "settings.submit": "ذخیره رمز جدید",
        "settings.submit_hint": "تغییر رمز، کلید VPN را هم عوض می‌کند — بعداً کانفیگ جدید دانلود کنید.",
        "settings.vpn_config": "دریافت کانفیگ VPN",
        "settings.vpn_config_hint": "فایل کانفیگ را دانلود کنید یا QR را در اپ WireGuard اسکن کنید.",
        "status.install_title": "نصب VPN",
        "status.install_hint": "برای اتصال، کانفیگ را در اپ WireGuard وارد کنید:",
        "status.install_step1": "اپ WireGuard را روی گوشی یا کامپیوتر نصب کنید",
        "status.install_step2": "دکمه «نمایش QR» را بزنید و اسکن کنید، یا فایل را دانلود کنید",
        "status.install_step3": "اتصال را روشن کنید",
        "status.go_support": "رفتن به پشتیبانی برای درخواست تمدید",
        "support.subtitle": "درخواست تمدید یا فعال‌سازی و مشاهده تاریخچه",
        "support.col.subject": "نوع درخواست",
        "support.waiting_approval": "حساب شما در انتظار تایید ادمین است. پس از تایید می‌توانید درخواست ثبت کنید.",
        "support.status_legend": "در انتظار = ادمین هنوز بررسی نکرده · تایید شده = انجام شد · رد شده = رد شد",
        "copy.steps_title": "راهنمای نصب",
        "copy.step1": "متن زیر را کپی کنید",
        "copy.step2": "در WireGuard → Add tunnel → Import from clipboard",
        "copy.step3": "اتصال را فعال کنید",
        "settings.account": "حساب کاربری",
        "settings.logout": "خروج از حساب",
        "settings.logout_hint": "برای ورود مجدد به پنل باید دوباره وارد شوید.",
        "settings.new_config": "کانفیگ جدید",
        "settings.new_config_hint": "کلیدهای VPN عوض شده — کانفیگ جدید را دانلود یا QR را اسکن کنید.",
        "settings.download": "دانلود کانفیگ",
        "settings.download_all_zip": "دانلود همه کانفیگ‌ها (ZIP)",
        "settings.show_qr": "نمایش QR",
        "vpn.twohop": "دو مرحله‌ای (خروجی از سرور exit)",
        "vpn.direct": "مستقیم (خروجی از سرور ورودی)",
        "password.wrong_old": "رمز فعلی اشتباه است.",
        "password.too_short": "رمز جدید باید حداقل ۶ کاراکتر باشد.",
        "password.mismatch": "تکرار رمز جدید درست نیست.",
        "password.not_ready": "برای تغییر کلید کانفیگ، ابتدا حساب باید تایید و کانفیگ اختصاص داده شود.",
        "password.rotate_failed": "خطا در تغییر کلید VPN. رمز تغییر نکرد. {detail}",
        "password.success": "رمز تغییر کرد و کلیدهای VPN عوض شد.",
        "status.active.title": "اتصال فعال است",
        "status.active.desc": "اشتراک شما فعال است. در حال حاضر نیازی به تمدید یا فعال‌سازی نیست.",
        "status.expired.title": "اشتراک منقضی شده",
        "status.expired.desc": "مدت اشتراک به پایان رسیده. برای ادامه، درخواست تمدید ثبت کنید.",
        "status.over_limit.title": "حجم اشتراک تمام شده",
        "status.over_limit.desc": "حجم مصرفی تمام شده. برای دریافت حجم جدید، درخواست تمدید ثبت کنید.",
        "status.disabled.title": "کانفیگ غیرفعال است",
        "status.disabled.desc": "کانفیگ غیرفعال شده. برای فعال‌سازی، درخواست فعال‌سازی ثبت کنید.",
        "status.unknown.title": "وضعیت نیازمند بررسی",
        "status.unknown.desc": "وضعیت کانفیگ مشخص نیست. با پشتیبانی تماس بگیرید.",
        "status.request_renew": "درخواست تمدید",
        "status.request_enable": "درخواست فعال‌سازی",
        "status.download": "دانلود کانفیگ",
        "status.copy": "کپی متن کانفیگ",
        "status.download_hint": "پس از تمدید یا تغییر رمز، کانفیگ جدید را دانلود و در WireGuard وارد کنید.",
        "support.subtitle": "درخواست‌های تمدید و فعال‌سازی و تاریخچه تیکت‌ها",
        "support.empty": "هنوز درخواستی ثبت نشده است.",
        "support.actions_title": "درخواست جدید",
        "support.history_title": "تاریخچه درخواست‌ها",
        "support.col.id": "شناسه",
        "support.col.subject": "موضوع",
        "support.col.status": "وضعیت",
        "support.col.date": "تاریخ",
        "support.back": "بازگشت به پشتیبانی",
        "copy.subtitle": "متن را کپی کنید یا فایل را دانلود کنید.",
        "copy.hint_select": "برای کپی دستی، متن زیر را انتخاب کنید یا دکمه کپی را بزنید.",
        "btn.download": "دانلود",
        "btn.back": "بازگشت",
        "forms.download_file": "دانلود فایل کانفیگ",
        "modal.close": "بستن",
        "modal.qr_title": "QR کانفیگ",
        "modal.qr_subtitle": "این کد را با اپ WireGuard اسکن کنید.",
        "modal.qr_loading": "در حال ساخت QR…",
        "request.invalid_title": "درخواست نامعتبر",
        "request.forbidden_title": "درخواست مجاز نیست",
        "state.active": "فعال",
        "state.expired": "منقضی",
        "state.over_limit": "اتمام حجم",
        "state.disabled": "غیرفعال",
        "action.renew": "تمدید اشتراک",
        "action.enable": "فعال‌سازی",
        "request.pending": "در انتظار بررسی",
        "request.approved": "تایید شده",
        "request.rejected": "رد شده",
        "request.done": "انجام شده",
        "request.processed": "پردازش شده",
        "single.ip": "محدود به یک آدرس اینترنتی؛ اولین IP ثبت می‌شود و اتصال از IP دیگر مجاز نیست.",
        "single.endpoint": "محدودیت سخت‌گیرانه؛ اتصال فقط از همان IP و پورت اولیه مجاز است.",
        "single.off": "بدون محدودیت دستگاه؛ قابل استفاده از چند دستگاه یا شبکه.",
        "duration.unknown": "نامشخص",
        "duration.seconds_ago": "{n} ثانیه قبل",
        "duration.minutes_ago": "{n} دقیقه قبل",
        "duration.hours_minutes_ago": "{hours} ساعت و {minutes} دقیقه قبل",
        "duration.hours_ago": "{n} ساعت قبل",
        "duration.days_hours_ago": "{days} روز و {hours} ساعت قبل",
        "duration.days_ago": "{n} روز قبل",
        "duration.months_days_ago": "{months} ماه و {days} روز قبل",
        "duration.months_ago": "{n} ماه قبل",
        "duration.years_months_ago": "{years} سال و {months} ماه قبل",
        "duration.years_ago": "{n} سال قبل",
        "disabled_reason.none": "ندارد",
        "unlimited": "نامحدود",
        "never": "هرگز",
        "none": "هیچ‌کدام",
        "csrf_error": "درخواست نامعتبر (CSRF)",
        "error.sign_in_first": "ابتدا وارد شوید.",
        "error.not_approved": "حساب شما هنوز تایید یا به کانفیگ متصل نشده است.",
        "error.config_not_found": "کانفیگ پیدا نشد.",
        "error.config_not_assigned": "کانفیگ اختصاص داده نشده است.",
        "error.enable_not_needed": "کانفیگ شما غیرفعال نیست؛ درخواست فعال‌سازی لازم نیست.",
        "error.renew_not_needed": "اشتراک هنوز منقضی نشده و حجم تمام نشده؛ درخواست تمدید فعال نیست.",
        "error.invalid_request": "درخواست نامعتبر است.",
        "error.meta_not_found": "متادیتای کلاینت پیدا نشد.",
        "error.conf_not_found": "فایل کانفیگ پیدا نشد.",
        "error.conf_key_mismatch": "کانفیگ با کلید فعلی سرور هماهنگ نیست. رمز را تغییر دهید یا از پشتیبانی بخواهید.",
        "error.qrencode": "qrencode روی سرور نصب نیست یا خطا داده است.",
        "security.rate_limit": "تلاش‌های زیاد. {wait} ثانیه صبر کنید.",
        "js.please_wait": "لطفاً صبر کنید…",
        "js.confirm_default": "ادامه می‌دهید؟",
        "js.copy_ok": "متن کانفیگ کپی شد.",
        "js.copy_fail_redirect": "کپی انجام نشد. از صفحه «کپی کانفیگ» استفاده کنید.",
        "js.copy_fail_manual": "کپی انجام نشد — متن را دستی انتخاب کنید.",
        "js.qr_error": "خطا در ساخت QR",
        "js.qr_error_full": "خطا در ساخت QR کد",
        "js.toast_dismiss": "بستن",
        "setup.title": "راهنمای نصب",
        "setup.ios_apps": "اپ‌های iOS: Hiddify، Streisand، Shadowrocket، WireGuard (App Store)",
        "setup.ios_steps": "اپ WireGuard را از App Store نصب کنید|در پنل، «دانلود کانفیگ» را بزنید|فایل را در WireGuard باز کنید|اتصال را روشن کنید",
        "setup.android_apps": "اپ‌های Android: Hiddify، v2rayNG، WireGuard (Google Play)",
        "setup.android_steps": "اپ WireGuard را از Google Play نصب کنید|کانفیگ را دانلود کنید|در WireGuard → Add → از فایل وارد کنید|اتصال را فعال کنید",
        "setup.windows_apps": "ویندوز: Hiddify، WireGuard (wireguard.com)، v2rayN",
        "setup.windows_steps": "WireGuard را از wireguard.com دانلود و نصب کنید|کانفیگ را از پنل دانلود کنید|در WireGuard → Import tunnel(s) from file|اتصال را فعال کنید",
        "setup.macos_apps": "مک: Hiddify، WireGuard (App Store)، V2Box",
        "setup.macos_steps": "WireGuard را از App Store نصب کنید|کانفیگ را دانلود کنید|فایل را روی اپ WireGuard بکشید|اتصال را روشن کنید",
        "setup.linux_apps": "لینوکس: WireGuard (بسته‌های سیستم)، Hiddify، v2rayA",
        "setup.linux_steps": "sudo apt install wireguard|کانفیگ را در /etc/wireguard/wg0.conf ذخیره کنید|sudo wg-quick up wg0|برای اتصال دائم: sudo systemctl enable wg-quick@wg0",
    },
    "en": {
        "skip_link": "Skip to content",
        "version": "Version",
        "lang_toggle": "فارسی",
        "lang_toggle_label": "Language",
        "nav.dashboard": "Overview",
        "nav.support": "Support",
        "nav.settings": "Settings",
        "nav.sidebar": "Sidebar navigation",
        "nav.bottom": "Bottom navigation",
        "auth.welcome": "Welcome",
        "auth.login_sub": "Sign in to view VPN status and manage your config.",
        "auth.username": "Username",
        "auth.password": "Password",
        "auth.login_btn": "Sign in",
        "auth.register_link": "Create account",
        "auth.register_title": "Register",
        "auth.register_sub": "After registration, an admin will review your account.",
        "auth.register_btn": "Register",
        "auth.login_link": "Sign in",
        "auth.register_hint": "Username min 3 chars, password min 6 chars.",
        "auth.register_invalid": "Username must be at least 3 characters and password at least 6.",
        "auth.username_taken": "This username is already taken.",
        "auth.register_success": "Account created. Wait for admin approval.",
        "auth.invalid_credentials": "Invalid username or password.",
        "page.dashboard": "Overview",
        "page.support": "Support",
        "page.settings": "Settings",
        "page.pending": "Pending approval",
        "page.inactive": "Inactive",
        "page.no_config": "No config",
        "page.copy_config": "Copy config",
        "page.not_found": "Page not found",
        "page.error": "Error",
        "page.forbidden": "Not allowed",
        "dashboard.subtitle": "Subscription and VPN connection status",
        "dashboard.pending": "Your account is waiting for admin approval.",
        "dashboard.pending_sub": "After approval, your config status will appear here.",
        "dashboard.inactive": "Your account is not active.",
        "dashboard.no_config": "No assigned config was found.",
        "dashboard.usage_pct": "Usage %",
        "dashboard.remaining": "Remaining",
        "dashboard.used": "Used",
        "dashboard.limit": "Limit",
        "dashboard.expiry_date": "Expiry date",
        "dashboard.days_left": "Days left",
        "dashboard.status": "Status",
        "dashboard.connection_details": "Connection details",
        "dashboard.config_name": "Config name",
        "dashboard.vpn_address": "VPN address",
        "dashboard.last_handshake": "Last handshake",
        "dashboard.endpoint": "Endpoint",
        "dashboard.device_limit": "Device limit",
        "dashboard.disable_reason": "Disable reason",
        "dashboard.vpn_mode": "VPN path",
        "dashboard.your_configs": "Your configs",
        "dashboard.your_configs_hint": "Download each config separately or get all of them as a ZIP from Settings.",
        "dashboard.primary_config": "Primary config",
        "dashboard.download_one": "Download",
        "dashboard.data_usage": "Data usage",
        "dashboard.subscription_period": "Subscription period",
        "dashboard.time_remaining": "Time remaining",
        "settings.title": "Settings",
        "settings.subtitle": "Manage password and sign out",
        "settings.change_password": "Change password",
        "settings.change_hint": "Changing your password also rotates VPN keys — download the new config.",
        "settings.old_password": "Current password",
        "settings.new_password": "New password",
        "settings.confirm_password": "Confirm new password",
        "settings.submit": "Save new password",
        "settings.submit_hint": "Changing your password also resets VPN keys — download the new config afterward.",
        "settings.vpn_config": "Get VPN config",
        "settings.vpn_config_hint": "Download the config file or scan the QR code in the WireGuard app.",
        "dashboard.account_info": "VPN info",
        "dashboard.pending_hint": "After admin approval, your subscription status and config download will appear here.",
        "dashboard.inactive_sub": "Your account is disabled",
        "dashboard.no_config_sub": "No VPN config has been assigned to you yet",
        "status.install_title": "Install VPN",
        "status.install_hint": "To connect, add the config to the WireGuard app:",
        "status.install_step1": "Install WireGuard on your phone or computer",
        "status.install_step2": "Tap “Show QR” and scan it, or download the file",
        "status.install_step3": "Turn the connection on",
        "status.go_support": "Go to Support to request renewal",
        "support.subtitle": "Request renewal or re-enable, and view history",
        "support.col.subject": "Request type",
        "support.waiting_approval": "Your account is waiting for admin approval. You can submit requests after approval.",
        "support.status_legend": "Pending = admin has not reviewed yet · Approved = done · Rejected = declined",
        "copy.steps_title": "Setup guide",
        "copy.step1": "Copy the text below",
        "copy.step2": "In WireGuard → Add tunnel → Import from clipboard",
        "copy.step3": "Activate the connection",
        "settings.account": "Account",
        "settings.logout": "Sign out",
        "settings.logout_hint": "You will need to sign in again to access the panel.",
        "settings.new_config": "New config",
        "settings.new_config_hint": "VPN keys were rotated — download the new config or scan the QR code.",
        "settings.download": "Download config",
        "settings.download_all_zip": "Download all configs (ZIP)",
        "vpn.twohop": "Two-hop (exit server egress)",
        "vpn.direct": "Direct (entry server egress)",
        "settings.show_qr": "Show QR",
        "password.wrong_old": "Current password is incorrect.",
        "password.too_short": "New password must be at least 6 characters.",
        "password.mismatch": "New passwords do not match.",
        "password.not_ready": "To rotate VPN keys, your account must be approved and assigned a config first.",
        "password.rotate_failed": "Failed to rotate VPN keys. Password was not changed. {detail}",
        "password.success": "Password changed and VPN keys were rotated.",
        "status.active.title": "Connection active",
        "status.active.desc": "Your subscription is active. No renewal or enable request is needed right now.",
        "status.expired.title": "Subscription expired",
        "status.expired.desc": "Your subscription period has ended. Submit a renewal request to continue.",
        "status.over_limit.title": "Data limit reached",
        "status.over_limit.desc": "Your data allowance is used up. Submit a renewal request for more data.",
        "status.disabled.title": "Config disabled",
        "status.disabled.desc": "Your config is disabled. Submit an enable request to restore access.",
        "status.unknown.title": "Status needs review",
        "status.unknown.desc": "Config status is unclear. Contact support.",
        "status.request_renew": "Request renewal",
        "status.request_enable": "Request enable",
        "status.download": "Download config",
        "status.copy": "Copy config text",
        "status.download_hint": "After renewal or password change, download the new config and import it in WireGuard.",
        "support.subtitle": "Renewal and enable requests and ticket history",
        "support.empty": "No requests submitted yet.",
        "support.actions_title": "New request",
        "support.history_title": "Request history",
        "support.col.id": "ID",
        "support.col.subject": "Subject",
        "support.col.status": "Status",
        "support.col.date": "Date",
        "support.back": "Back to support",
        "copy.subtitle": "Copy the text or download the file.",
        "copy.hint_select": "Select the text below to copy manually, or use the copy button.",
        "btn.download": "Download",
        "btn.back": "Back",
        "forms.download_file": "Download config file",
        "modal.close": "Close",
        "modal.qr_title": "Config QR",
        "modal.qr_subtitle": "Scan this code with the WireGuard app.",
        "modal.qr_loading": "Generating QR…",
        "request.invalid_title": "Invalid request",
        "request.forbidden_title": "Request not allowed",
        "state.active": "Active",
        "state.expired": "Expired",
        "state.over_limit": "Over limit",
        "state.disabled": "Disabled",
        "action.renew": "Renew subscription",
        "action.enable": "Enable",
        "request.pending": "Pending review",
        "request.approved": "Approved",
        "request.rejected": "Rejected",
        "request.done": "Done",
        "request.processed": "Processed",
        "single.ip": "Locked to one IP address; the first IP is recorded and connections from other IPs are not allowed.",
        "single.endpoint": "Strict lock; only the original IP and port may connect.",
        "single.off": "No device restriction; usable from multiple devices or networks.",
        "duration.unknown": "Unknown",
        "duration.seconds_ago": "{n} seconds ago",
        "duration.minutes_ago": "{n} minutes ago",
        "duration.hours_minutes_ago": "{hours} h {minutes} min ago",
        "duration.hours_ago": "{n} hours ago",
        "duration.days_hours_ago": "{days} d {hours} h ago",
        "duration.days_ago": "{n} days ago",
        "duration.months_days_ago": "{months} mo {days} d ago",
        "duration.months_ago": "{n} months ago",
        "duration.years_months_ago": "{years} y {months} mo ago",
        "duration.years_ago": "{n} years ago",
        "disabled_reason.none": "None",
        "unlimited": "Unlimited",
        "never": "Never",
        "none": "None",
        "csrf_error": "Invalid request (CSRF)",
        "error.sign_in_first": "Sign in first.",
        "error.not_approved": "Your account is not yet approved or linked to a config.",
        "error.config_not_found": "Config not found.",
        "error.config_not_assigned": "No config assigned.",
        "error.enable_not_needed": "Your config is not disabled; an enable request is not needed.",
        "error.renew_not_needed": "Your subscription is still active; renewal is not available yet.",
        "error.invalid_request": "Invalid request.",
        "error.meta_not_found": "Client metadata not found.",
        "error.conf_not_found": "Config file not found.",
        "error.conf_key_mismatch": "Config is out of sync with the server. Change your password or contact support.",
        "error.qrencode": "qrencode is not installed or failed on the server.",
        "security.rate_limit": "Too many attempts. Wait {wait} seconds.",
        "js.please_wait": "Please wait…",
        "js.confirm_default": "Continue?",
        "js.copy_ok": "Config text copied.",
        "js.copy_fail_redirect": "Copy failed. Use the Copy config page.",
        "js.copy_fail_manual": "Copy failed — select the text manually.",
        "js.qr_error": "Failed to generate QR",
        "js.qr_error_full": "Failed to generate QR code",
        "js.toast_dismiss": "Dismiss",
        "setup.title": "Setup guide",
        "setup.ios_apps": "iOS apps: Hiddify, Streisand, Shadowrocket, WireGuard (App Store)",
        "setup.ios_steps": "Install WireGuard from the App Store|Tap Download config in the panel|Open the file with WireGuard|Toggle the connection on",
        "setup.android_apps": "Android apps: Hiddify, v2rayNG, WireGuard (Google Play)",
        "setup.android_steps": "Install WireGuard from Google Play|Download the config from the panel|In WireGuard → Add → Import from file|Enable the connection",
        "setup.windows_apps": "Windows: Hiddify, WireGuard (wireguard.com), v2rayN",
        "setup.windows_steps": "Download and install WireGuard from wireguard.com|Download the config file from the panel|In WireGuard → Import tunnel(s) from file|Toggle the connection on",
        "setup.macos_apps": "macOS: Hiddify, WireGuard (App Store), V2Box",
        "setup.macos_steps": "Install WireGuard from the App Store|Download the config file|Drag the file onto the WireGuard app|Toggle the connection on",
        "setup.linux_apps": "Linux: WireGuard (system packages), Hiddify, v2rayA",
        "setup.linux_steps": "sudo apt install wireguard|Save the config to /etc/wireguard/wg0.conf|sudo wg-quick up wg0|For auto-start: sudo systemctl enable wg-quick@wg0",
    },
}


def begin_request(handler):
    cookie = SimpleCookie(handler.headers.get("Cookie", ""))
    token = cookie.get("wg_lang")
    lang = token.value if token and token.value in _SUPPORTED else _DEFAULT
    _local.lang = lang


def current_lang():
    return _lang()


def html_lang():
    return _lang()


def html_dir():
    return "rtl" if _lang() == "fa" else "ltr"


def t(key, default=None):
    table = _STRINGS.get(_lang(), _STRINGS[_DEFAULT])
    if key in table:
        return table[key]
    fallback = _STRINGS[_DEFAULT]
    return fallback.get(key, default if default is not None else key)


def tf(key, default=None, **kwargs):
    template = t(key, default)
    if not kwargs:
        return template
    try:
        return template.format(**kwargs)
    except (KeyError, ValueError):
        return template


def js_i18n_script():
    data = {
        "confirmDefault": t("js.confirm_default"),
        "pleaseWait": t("js.please_wait"),
        "copyOk": t("js.copy_ok"),
        "copyFailRedirect": t("js.copy_fail_redirect"),
        "copyFailManual": t("js.copy_fail_manual"),
        "qrError": t("js.qr_error"),
        "qrErrorFull": t("js.qr_error_full"),
        "qrLoading": t("modal.qr_loading"),
        "toastDismiss": t("js.toast_dismiss"),
        "locale": _lang(),
    }
    return f"<script>window.__I18N={json.dumps(data, ensure_ascii=False)};</script>"


def secure_cookie_attrs():
    if os.environ.get("WG_HTTPS", "").strip() in ("1", "true", "yes"):
        return "; Secure"
    return ""


def lang_set_href(lang, next_path="/"):
    q = urllib.parse.urlencode({"lang": lang, "next": next_path})
    return f"/set-lang?{q}"


def lang_toggle_href(next_path="/"):
    other = "en" if _lang() == "fa" else "fa"
    return lang_set_href(other, next_path)


def lang_toggle_html(next_path="/"):
    label = html.escape(t("lang_toggle_label"))
    parts = []
    for code, text in (("fa", "FA"), ("en", "EN")):
        if _lang() == code:
            parts.append(
                f'<span class="lang-toggle-option active" aria-current="true">{text}</span>'
            )
        else:
            href = html.escape(lang_set_href(code, next_path))
            parts.append(
                f'<a class="lang-toggle-option" href="{href}" '
                f'hreflang="{code}" lang="{code}">{text}</a>'
            )
    inner = "".join(parts)
    return f'<div class="lang-toggle" role="group" aria-label="{label}">{inner}</div>'


def set_lang_cookie(handler, lang):
    attrs = f"Path=/; Max-Age=31536000; SameSite=Lax{secure_cookie_attrs()}"
    handler.send_header("Set-Cookie", f"wg_lang={lang}; {attrs}")
