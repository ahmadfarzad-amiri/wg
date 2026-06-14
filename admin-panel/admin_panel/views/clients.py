import html

from admin_panel.components.client_rows import add_client_form, bulk_add_client_form, client_list
from admin_panel.components.list_search import client_filters, client_sorts, list_controls
from admin_panel.components.notice import notice
from admin_panel.core.i18n import t
from admin_panel.db.panel_queries import assigned_client_names, users_by_client


def body(clients, msg=""):
    table = client_list(clients, assigned_client_names(), users_by_client())
    return f"""
<h1>{html.escape(t("clients.title"))}</h1>
<p class="subtitle">{html.escape(t("clients.subtitle"))}</p>
<p class="hint page-glossary">{html.escape(t("glossary.clients"))}</p>
{notice(msg, role="alert")}

<div class="page-stack">
<section class="card card-clients list-filterable">
  <div class="list-section-head">
    <h3>{html.escape(t("clients.all_title"))}</h3>
    {list_controls(
        search_placeholder=t("list.search_clients"),
        filters=client_filters(),
        sorts=client_sorts(),
    )}
  </div>
  {table}
  <p class="list-search-empty" data-list-search-empty hidden>{html.escape(t("empty.no_results"))}</p>
</section>

<details class="add-client-details card">
  <summary><h3>{html.escape(t("clients.add_title"))}</h3></summary>
  <p class="hint add-client-intro">{html.escape(t("clients.add_intro"))}</p>
  {add_client_form()}
</details>

<details class="add-client-details card">
  <summary><h3>{html.escape(t("clients.bulk_add_title"))}</h3></summary>
  <p class="hint">{html.escape(t("clients.bulk_add_intro"))}</p>
  {bulk_add_client_form()}
</details>
</div>
"""
