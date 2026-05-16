______________________________________________________________________

Version: 1.1.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-05-16'

______________________________________________________________________

# Variables Guide (Grafana Dashboards)

Дата сверки: **2026-05-16**
Источник истины: `grafana/dashboards/*.json`

## Нормативный источник

Нормативные источники:

- переменные, selector taxonomy, hidden-hand-off classes:
  `docs/03-guides/dashboards/contracts/selector-contracts.yaml`
- dashboard-link vars и time handoff:
  `docs/03-guides/dashboards/contracts/navigation-links.yaml`

Используйте YAML-секции из `navigation-links.yaml`:
- `required_link_vars_by_target_uid`
- `allowed_dashboard_link_vars`
- `forbidden_dashboard_link_vars_by_target_uid`
- `time_handoff_requirements`
- `default_time_refresh_policy` / `default_time_refresh_policy_exceptions`

Используйте YAML-секции из `selector-contracts.yaml`:
- `selector_taxonomy`
- `dashboard_families`
- `shipped_selector_registry`
- `ship_now_selector_contract_by_uid`
- `hidden_handoff_contract`

Этот guide оставлен как explanatory reference (контекст и примеры), без повторного нормирования MUST/SHOULD правил.

## Test coverage expectations

- Links contract: `tests/integration/test_grafana_dashboard_links.py`
- Variable contract checks: `tests/integration/test_grafana_config.py` + `tests/integration/_grafana_test_support.py`
- Selector taxonomy / registry checks: `tests/integration/test_grafana_selector_contract.py`
- Variable reference mirror checks: `tests/integration/test_grafana_variable_reference.py`
- Exact-id isolation checks: primary `run_id`, Silver `quarantine_run_id`, and
  `payload_hash` запрещены в Prometheus label filtering and generic
  cross-dashboard links; `bioetl-overview-v2` exposes control-plane-backed
  `run_id=-` for its local `ID` panel.

## UID → Variables (inventory parity reference)

| Dashboard UID | Variables |
|---|---|
| `bioetl-control-plane-v1` | `$pipeline`, `$run_id`, `$run_type`, `$workflow` |
| `bioetl-dq-v2` | `$pipeline`, `$run_id`, `$run_type`, `$stage`, `$workflow` |
| `bioetl-overview-v2` | `$pipeline`, `$run_id`, `$run_type`, `$workflow` |
| `bioetl-overview-v3` | `$pipeline`, `$run_id`, `$run_type`, `$workflow` |
| `bioetl-provider-health-v2` | `$adapter`, `$pipeline`, `$pipeline_context`, `$provider`, `$run_id`, `$run_type`, `$workflow` |
| `bioetl-runtime` | `$pipeline`, `$run_id`, `$run_type`, `$stage`, `$workflow` |
| `bioetl-silver-reject-explorer` | `$field`, `$payload_hash`, `$pipeline`, `$quarantine_run_id`, `$reason_code`, `$run_type` |
| `bioetl-workflow-overview` | `$pipeline`, `$pipeline_context`, `$provider_context`, `$run_id`, `$run_type`, `$run_type_context`, `$status`, `$step_kind`, `$step_status`, `$workflow` |
