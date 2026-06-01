from admin_panel.components.list_search import list_controls, user_filters, user_sorts
from admin_panel.components.notice import notice
from admin_panel.components.user_rows import user_rows
from admin_panel.core.i18n import t


def body(users, msg=""):
    listing = user_rows(users)
    return f"""
<h1>{t("users.title")}</h1>
<p class="subtitle">{t("users.subtitle")}</p>
<p class="hint page-glossary">{t("glossary.users")}</p>
{notice(msg, role="alert")}

<div class="page-stack">
<section class="card card-users list-filterable">
  <div class="list-section-head">
    <h3>{t("users.list_title")}</h3>
    {list_controls(
        search_placeholder=t("list.search_users"),
        filters=user_filters(),
        sorts=user_sorts(),
    )}
  </div>
  {listing}
  <p class="list-search-empty" data-list-search-empty hidden>{t("empty.no_results")}</p>
</section>
</div>
"""
