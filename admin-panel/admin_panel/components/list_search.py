import html


CLIENT_FILTERS = [
    ("", "همه وضعیت‌ها"),
    ("active", "آنلاین"),
    ("offline", "آفلاین"),
    ("disabled", "غیرفعال"),
    ("expired", "منقضی"),
    ("over_limit", "اتمام حجم"),
    ("unassigned", "اختصاص نیافته"),
]

CLIENT_SORTS = [
    ("name-asc", "نام (الف-ی)"),
    ("name-desc", "نام (ی-الف)"),
    ("ip-asc", "IP"),
    ("status-asc", "وضعیت"),
]

USER_FILTERS = [
    ("", "همه وضعیت‌ها"),
    ("pending", "در انتظار تایید"),
    ("approved", "تایید شده"),
    ("disabled", "غیرفعال"),
    ("rejected", "رد شده"),
]

USER_SORTS = [
    ("id-desc", "جدیدترین"),
    ("id-asc", "قدیمی‌ترین"),
    ("name-asc", "نام کاربری (الف-ی)"),
    ("name-desc", "نام کاربری (ی-الف)"),
    ("client-asc", "کلاینت (الف-ی)"),
    ("status-asc", "وضعیت"),
]

REQUEST_FILTERS = [
    ("", "همه وضعیت‌ها"),
    ("pending", "در انتظار بررسی"),
    ("approved", "تایید شده"),
    ("rejected", "رد شده"),
]

REQUEST_SORTS = [
    ("id-desc", "جدیدترین"),
    ("id-asc", "قدیمی‌ترین"),
    ("name-asc", "کاربر (الف-ی)"),
    ("name-desc", "کاربر (ی-الف)"),
    ("client-asc", "کلاینت (الف-ی)"),
    ("action-asc", "موضوع"),
    ("status-asc", "وضعیت"),
    ("created-desc", "تاریخ (جدید)"),
    ("created-asc", "تاریخ (قدیم)"),
]

ACTIVE_FILTERS = [
    ("", "همه آنلاین"),
    ("fresh", "اتصال تازه (زیر ۱ دقیقه)"),
    ("idle", "بیش از ۱ دقیقه"),
]

ACTIVE_SORTS = [
    ("name-asc", "نام (الف-ی)"),
    ("name-desc", "نام (ی-الف)"),
    ("ip-asc", "IP"),
    ("last-asc", "تازه‌ترین اتصال"),
    ("last-desc", "قدیمی‌ترین اتصال"),
    ("rx-desc", "بیشترین دریافت"),
    ("tx-desc", "بیشترین ارسال"),
]


def list_controls(*, search_placeholder="جستجو...", filters=None, sorts=None):
    filters = filters or [("", "همه")]
    sorts = sorts or [("default", "پیش‌فرض")]

    search_ph = html.escape(search_placeholder)
    filter_opts = "".join(
        f'<option value="{html.escape(value)}">{html.escape(label)}</option>'
        for value, label in filters
    )
    sort_opts = "".join(
        f'<option value="{html.escape(value)}">{html.escape(label)}</option>'
        for value, label in sorts
    )

    return f"""
<div class="list-controls">
  <div class="list-search">
    <input type="search" class="list-search-input" data-list-search placeholder="{search_ph}" aria-label="{search_ph}" autocomplete="off">
  </div>
  <label class="list-control">
    <span class="list-control-label">فیلتر</span>
    <select class="list-control-select" data-list-filter aria-label="فیلتر">
      {filter_opts}
    </select>
  </label>
  <label class="list-control">
    <span class="list-control-label">مرتب‌سازی</span>
    <select class="list-control-select" data-list-sort aria-label="مرتب‌سازی">
      {sort_opts}
    </select>
  </label>
  <span class="list-search-meta" data-list-search-meta hidden></span>
</div>
"""


def list_search(placeholder="جستجو..."):
    return list_controls(search_placeholder=placeholder)
