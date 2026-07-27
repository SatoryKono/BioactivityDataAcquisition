# Grafana Navigation Contract

Канонический контракт навигации для shipped dashboard UIDs в `grafana/dashboards/*.json`.

Machine-readable SSOT: `docs/03-guides/dashboards/contracts/navigation-links.yaml`.

The visual contract is one identical, theme-safe composition on all **seven**
shipped dashboards: numbered bus `0. Control Plane` through `6. Alerts & SLO`.
Adjunct Explore handoffs for Loki/Tempo and the Silver Reject Explorer dashboard
were **removed 2026-07-23** (see
[monitoring-surface-reduction](../../05-operations/runbooks/monitoring-surface-reduction-2026-07-23.md)).
The current surface remains visible but disabled. Links use solid
contrast-safe colors and wrap at `1024px`; horizontal clipping and
light-theme white-on-white states are defects.

YAML также фиксирует time handoff policy в `time_handoff_requirements`:
- `dashboard_links.required_tokens`: `${__url_time_range}`

## Нормативный источник

Единственный нормативный источник link/vars/time semantics: `docs/03-guides/dashboards/contracts/navigation-links.yaml`.

- Минимальный narrative закреплён в YAML: `normative_source.narrative_minimal`.
- Нормативные ключи для проверок: `required_top_level_links_by_uid`, `required_link_vars_by_target_uid`, `allowed_dashboard_link_vars`, `forbidden_dashboard_link_vars_by_target_uid`, `time_handoff_requirements`, `default_time_refresh_policy`, `navigation_transition_contract`.
- Этот Markdown — explanatory mirror: допускаются примеры и навигация, но не дублирование нормативных MUST-правил.

## Примеры URL (нормализованный формат)

- Dashboard: `/d/bioetl-runtime/bioetl-runtime?var-pipeline=$pipeline&var-run_type=$run_type&${__url_time_range}`
- Dashboard: `/d/bioetl-dq-v2/bioetl-dq-v2?var-pipeline=$pipeline&var-run_type=$run_type&var-stage=$stage&${__url_time_range}`
- Dashboard: `/d/bioetl-overview-v2/bioetl-overview-v2?var-pipeline=unknown&var-run_type=All&${__url_time_range}`
- Provider context mapping (fail-closed): `/d/bioetl-provider-health-v2/bioetl-provider-health-v2?var-provider=unknown&var-pipeline_context=$pipeline&${__url_time_range}`
- Alerts/SLO: `/d/bioetl-alerts-slo/bioetl-alerts-slo?var-workflow=$workflow&var-pipeline=$pipeline&var-run_type=$run_type&${__url_time_range}`

## Справка

Детальные обязательные блоки, forbidden patterns, priority/semantics и First Action contract поддерживаются только в YAML-контракте (`navigation-links.yaml`).

## Required inbound paths (discoverable first-screen CTA)

L1-target dashboards MUST be discoverable from first-screen status/KPI area on `bioetl-overview-v2` via panel `First Action` (id `215`), located on the frozen Overview v3 first-screen layout after the provenance header panel matched by regex `^Provenance$`.

| Target UID | Source UID | Source panel id | Source panel title | First-screen row matcher |
| --- | --- | ---: | --- | --- |
| `bioetl-runtime` | `bioetl-overview-v2` | `215` | `First Action` | `^Provenance$` |
| `bioetl-control-plane-v1` | `bioetl-overview-v2` | `215` | `First Action` | `^Provenance$` |
| `bioetl-provider-health-v2` | `bioetl-overview-v2` | `215` | `First Action` | `^Provenance$` |
| `bioetl-dq-v2` | `bioetl-overview-v2` | `215` | `First Action` | `^Provenance$` |
