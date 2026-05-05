______________________________________________________________________

Version: 1.1.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-05-03'

______________________________________________________________________

# Variables Guide (Grafana Dashboards)

Дата сверки: **2026-05-03**  
Источник истины: `grafana/dashboards/*.json`

## Нормативный источник

Единственный нормативный источник для переменных и time handoff: `docs/03-guides/dashboards/contracts/navigation-links.yaml`.

Используйте YAML-секции:
- `required_link_vars_by_target_uid`
- `allowed_dashboard_link_vars`
- `forbidden_dashboard_link_vars_by_target_uid`
- `time_handoff_requirements`
- `default_time_refresh_policy` / `default_time_refresh_policy_exceptions`

Этот guide оставлен как explanatory reference (контекст и примеры), без повторного нормирования MUST/SHOULD правил.

## Test coverage expectations

- Links contract: `tests/integration/test_grafana_dashboard_links.py`
- Variable contract checks: `tests/integration/test_grafana_config.py` + `tests/integration/_grafana_test_support.py`
- Forensic isolation checks: `run_id`/`payload_hash` запрещены вне reject explorer.

## UID → Variables (inventory parity reference)

| Dashboard UID | Variables |
|---|---|
| `bioetl-control-plane-v1` | `$pipeline`, `$run_type` |
| `bioetl-dq-v2` | `$pipeline`, `$run_type`, `$stage` |
| `bioetl-overview-v2` | `$pipeline`, `$run_type` |
| `bioetl-provider-health-v2` | `$adapter`, `$pipeline_context`, `$provider` |
| `bioetl-runtime` | `$pipeline`, `$run_type`, `$stage` |
| `bioetl-silver-reject-explorer` | `$field`, `$payload_hash`, `$pipeline`, `$reason_code`, `$run_id`, `$run_type` |
| `bioetl-workflow-overview` | `$status`, `$step_kind`, `$step_status`, `$workflow` |
