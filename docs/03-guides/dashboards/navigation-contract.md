# Grafana Navigation Contract

Канонический контракт навигации для shipped dashboard UIDs в `grafana/dashboards/*.json`.

Machine-readable SSOT: `docs/03-guides/dashboards/contracts/navigation-links.yaml`.

YAML также фиксирует time handoff policy в `time_handoff_requirements`:
- `dashboard_links.required_tokens`: `${__url_time_range}`
- `explore_links.required_tokens`: `from=${__from}`, `to=${__to}`

## Нормативный источник

Единственный нормативный источник link/vars/time semantics: `docs/03-guides/dashboards/contracts/navigation-links.yaml`.

- Минимальный narrative закреплён в YAML: `normative_source.narrative_minimal`.
- Нормативные ключи для проверок: `required_top_level_links_by_uid`, `required_link_vars_by_target_uid`, `allowed_dashboard_link_vars`, `forbidden_dashboard_link_vars_by_target_uid`, `time_handoff_requirements`, `default_time_refresh_policy`, `navigation_transition_contract`.
- Этот Markdown — explanatory mirror: допускаются примеры и навигация, но не дублирование нормативных MUST-правил.

## Примеры URL (нормализованный формат)

- Dashboard: `/d/bioetl-runtime/bioetl-runtime?var-pipeline=$pipeline&var-run_type=$run_type&${__url_time_range}`
- Dashboard: `/d/bioetl-dq-v2/bioetl-dq-v2?var-pipeline=$pipeline&var-run_type=$run_type&var-stage=$stage&${__url_time_range}`
- Dashboard: `/d/bioetl-overview-v2/bioetl-overview-v2?var-pipeline=All&var-run_type=All&${__url_time_range}`

## Справка

Детальные обязательные блоки, forbidden patterns, priority/semantics и First Action contract поддерживаются только в YAML-контракте (`navigation-links.yaml`).





