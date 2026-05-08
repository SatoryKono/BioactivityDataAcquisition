______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-05-08'

______________________________________________________________________

# Grafana Dashboard Variable Reference

Дата сверки: **2026-05-08**  
Источник истины: `grafana/dashboards/*.json`

Этот документ фиксирует канонический contract для dashboard variables:

- purpose and scope
- selection mode
- default / fail-closed behavior
- datasource/query family
- cross-dashboard propagation rules

Machine-readable selector SSOT:
`docs/03-guides/dashboards/contracts/selector-contracts.yaml`

## Core rules

- Все variables MUST иметь `description` в shipped JSON.
- Pipeline-scoped operator dashboards используют single-select `$pipeline`,
  кроме `bioetl-overview-v2`, где intentional landing default = `All`.
- `$run_type` always uses include-all fallback. Missing context is represented as
  `All`, not `unknown`.
- Explorer-only forensic variables (`$run_id`, `$payload_hash`) MUST NOT leak
  into Prometheus dashboards or dashboard-to-dashboard links.
- Hidden context variables are allowed only when they preserve return-path or
  detail-only scope, например `$pipeline_context` и `$adapter`.
- Variable behavior is standardized by role, not by one universal default.

## Common variables

| Variable | Dashboards | Datasource / query family | Selection mode | Default / fallback | Notes |
| --- | --- | --- | --- | --- | --- |
| `$pipeline` | `bioetl-overview-v2`, `bioetl-control-plane-v1`, `bioetl-runtime`, `bioetl-dq-v2`, `bioetl-silver-reject-explorer` | Prometheus `label_values(...)`; Runtime uses `bioetl_runtime_pipeline_run_type_universe`; Explorer uses concrete pipeline scope for Quarantine API | Single-select | `All` only on `bioetl-overview-v2`; otherwise fail-closed `unknown` | Canonical pipeline scope. Explorer requires one concrete pipeline. |
| `$run_type` | `bioetl-overview-v2`, `bioetl-control-plane-v1`, `bioetl-runtime`, `bioetl-dq-v2`, `bioetl-silver-reject-explorer` | Prometheus `label_values(..., run_type)` or runtime/control-plane universe metrics | Multi-select with Include All | `All` / `$__all` | Cross-dashboard links MUST NOT pass `run_type=unknown`. |
| `$stage` | `bioetl-runtime`, `bioetl-dq-v2` | Runtime: `bioetl_pipeline_stage_expected`; DQ: `bioetl_records_processed_total` | Multi-select with Include All | Dynamic Grafana selection | Bounded stage breakdown filter, not a forensic identifier. |

## Dashboard-specific variables

| Variable | Dashboard | Selection mode | Default / fallback | Notes |
| --- | --- | --- | --- | --- |
| `$provider` | `bioetl-provider-health-v2` | Single-select | `unknown` | Fail-closed provider scope for provider triage. |
| `$pipeline_context` | `bioetl-provider-health-v2` | Hidden context var | `unknown` | Preserves source pipeline for return handoff; not a first-class provider filter. |
| `$adapter` | `bioetl-provider-health-v2` | Multi-select with Include All | Dynamic Grafana selection | Detail-only provider breakdown; links may omit it and let target fall back to all adapters. |
| `$reason_code` | `bioetl-silver-reject-explorer` | Multi-select with Include All | `All` / `$__all` | Explorer-only forensic narrowing for bounded reject causes. |
| `$field` | `bioetl-silver-reject-explorer` | Multi-select with Include All | `All` / `$__all` | Explorer-only forensic narrowing for rejected fields. |
| `$run_id` | `bioetl-silver-reject-explorer` | Single-select | Empty until selected | Explorer-only forensic selector; MUST NOT appear in Prometheus queries or cross-dashboard links. |
| `$payload_hash` | `bioetl-silver-reject-explorer` | Visible textbox | Empty string | Forensic exact-record selector; visible only in the explorer and MUST NOT propagate into other dashboards. |
| `$workflow` | `bioetl-workflow-overview` | Multi-select with Include All | `All` / `$__all` | Workflow-level selected-range scope, not pipeline scope. |
| `$status` | `bioetl-workflow-overview` | Multi-select with Include All | `All` / `$__all` | Workflow run-status filter. |
| `$step_status` | `bioetl-workflow-overview` | Multi-select with Include All | `All` / `$__all` | Workflow step-status filter for step evidence panels. |
| `$step_kind` | `bioetl-workflow-overview` | Multi-select with Include All | `All` / `$__all` | Bounded step-kind filter, e.g. `pipeline`, `transform`. |

## Dependency chains

- `bioetl-runtime`
  - `$run_type` depends on `$pipeline`
  - `$stage` depends on runtime-selected scope and expected-stage metric family
- `bioetl-dq-v2`
  - `$run_type` depends on `$pipeline`
  - `$stage` depends on `$pipeline` and `$run_type`
- `bioetl-provider-health-v2`
  - `$pipeline_context` is preserved from source dashboard links
  - `$adapter` is optional detail scope, not required on handoff
- `bioetl-silver-reject-explorer`
  - `$pipeline` is required before Quarantine Explorer reads are trustworthy
  - `$reason_code`, `$field`, `$run_id`, `$payload_hash` are explorer-only narrowing filters
- `bioetl-workflow-overview`
  - `$workflow`, `$status`, `$step_status`, `$step_kind` are local to workflow evidence
  - these variables MUST NOT be propagated into non-workflow dashboards

## Role-specific defaults

### L0 / pipeline-scoped dashboards

- `bioetl-overview-v2` intentionally defaults to `Pipeline=All`, `Run Type=All`
  so the landing page answers the L0 question immediately.
- `bioetl-control-plane-v1`, `bioetl-runtime`, `bioetl-dq-v2`, and
  `bioetl-silver-reject-explorer` fail-close to `pipeline=unknown` when source
  context is absent.

### Provider triage

- `bioetl-provider-health-v2` defaults to `provider=unknown`.
- `$pipeline_context` remains hidden and preserves return-path context only.

### Workflow evidence

- `bioetl-workflow-overview` does not use `$pipeline` / `$run_type`.
- It intentionally uses `$workflow`, `$status`, `$step_status`, and
  `$step_kind` because the dashboard is selected-range workflow evidence rather
  than pipeline runtime current-state triage.

### Explorer forensics

- `bioetl-silver-reject-explorer` requires single-select `$pipeline`.
- `$run_id` and `$payload_hash` remain local forensic selectors and do not
  participate in Prometheus label filtering.

## Validation checklist

- [ ] Every variable in `templating.list` has a non-empty `description`
- [ ] `pipeline` / `provider` fail-closed dashboards remain single-select
- [ ] `run_type` defaults to `All`, not `unknown`
- [ ] Hidden variables are justified by return-path or detail-only scope
- [ ] Workflow and Explorer variables do not leak into non-target dashboards

## Related references

- `docs/03-guides/dashboards/dashboard-v2-usage.md`
- `docs/03-guides/dashboards/design-system.md`
- `grafana/README.md`
- `tests/integration/test_grafana_dashboard_links.py`
