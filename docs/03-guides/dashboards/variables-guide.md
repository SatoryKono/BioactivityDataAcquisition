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
- Exact-id isolation checks: primary `run_id` is preserved only between
  primary dashboards as HTTP identity context; Silver `quarantine_run_id` and
  `payload_hash` запрещены в Prometheus label filtering and generic
  cross-dashboard links. `bioetl-overview-v2` exposes control-plane-backed
  `run_id=-` for its local `ID` panel.
- Provider Health is provider-first even though it exposes the shared
  `$workflow/$pipeline/$run_type/$run_id` shell. `$run_id` remains HTTP identity
  context for shared `ID`/`Processed Records` surfaces only; Provider Health
  PromQL must not add a `run_id` label. The 12h UNKNOWN-vs-OK contract uses
  provider telemetry: `bioetl_provider_current_status` plus
  `bioetl_provider_range_operational_ok` in the active Grafana range.
- `$stage` defaults to **All** on Pipeline Diagnostics (`bioetl-runtime`) and
  Data Quality (`bioetl-dq-v2`). Cross-dashboard handoffs pass
  `var-stage=$__all` instead of forcing `unknown`.
- `$provider` on Provider Health and Incident Workspace is **derived**: first
  name segment of `$pipeline` when pipeline is set (same heuristic as runtime
  `$provider_hint`); else first segment of `$workflow` when workflow is set;
  else fail-closed `unknown` when neither is set.

## UID → Variables (inventory parity reference)

| Dashboard UID | Variables |
|---|---|
| `bioetl-control-plane-v1` | `$pipeline`, `$run_id`, `$run_type`, `$workflow` |
| `bioetl-dq-v2` | `$pipeline`, `$run_id`, `$run_type`, `$stage`, `$workflow` |
| `bioetl-incident-v1` | `$pipeline`, `$provider`, `$run_id`, `$run_type`, `$workflow` |
| `bioetl-overview-v2` | `$pipeline`, `$run_id`, `$run_type`, `$workflow` |
| `bioetl-provider-health-v2` | `$adapter`, `$pipeline`, `$pipeline_context`, `$provider`, `$run_id`, `$run_type`, `$workflow` |
| `bioetl-run-explorer-v1` | `$pipeline`, `$run_id`, `$run_type`, `$workflow` |
| `bioetl-runtime` | `$pipeline`, `$provider_hint`, `$run_id`, `$run_type`, `$stage`, `$workflow` |
| `bioetl-silver-reject-explorer` (retired) | `$field`, `$payload_hash`, `$pipeline`, `$quarantine_run_id`, `$reason_code`, `$run_type` |
| `bioetl-workflow-overview` (retired) | `$pipeline`, `$pipeline_context`, `$pipeline_context_exact`, `$provider_context`, `$provider_context_exact`, `$run_id`, `$run_type`, `$run_type_context`, `$run_type_context_exact`, `$status`, `$step_kind`, `$step_status`, `$workflow`, `$workflow_context` |
| `bioetl-alerts-slo` (retired) | `$pipeline`, `$run_type`, `$workflow` |
