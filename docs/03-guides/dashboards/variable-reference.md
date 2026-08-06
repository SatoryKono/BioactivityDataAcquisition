______________________________________________________________________

Version: 1.1.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-08-05'

______________________________________________________________________

# Grafana Dashboard Variable Reference

Дата сверки: **2026-08-05**
Источник истины: `grafana/dashboards/*.json`

Этот документ фиксирует канонический contract для dashboard variables на
**shipped** дашбордах (7 JSON, bus `0..6`).

Machine-readable selector SSOT:
`docs/03-guides/dashboards/contracts/selector-contracts.yaml`

Human family guide: [selector-architecture.md](selector-architecture.md)

## Core rules

- Все variables MUST иметь `description` в shipped JSON.
- Primary operator dashboards expose the shared context shell:
  `$workflow`, `$pipeline`, `$run_type`, `$run_id`.
- Role-specific extensions: `$stage` (Runtime, DQ), `$provider` (Provider Health,
  Incident), hidden `$pipeline_context` / `$adapter` (Provider Health),
  hidden `$provider_hint` (Runtime).
- `$workflow` is context/evidence unless a dashboard explicitly documents a
  truthful current-status intersection.
- `$workflow` is Single-select with Include All. It remains single-select with Include All across primary dashboards.
- `$pipeline` is single-select; Overview landing default is `All`; other boards
  fail-close to `unknown`.
- `$run_type` uses Include All. Overview landing default is `All`. Non-Overview
  primary boards default to `backfill`.
- `$run_id` is HTTP-backed control-plane identity context for Ops HTTP `ID` /
  Processed Records tables. It is preserved between primary dashboards and
  MUST NOT become a Prometheus label.
- `$stage` defaults to **All** (`$__all`) on Runtime and DQ.
- `$provider` defaults to `unknown` and is derived from pipeline/workflow when
  set (see Provider Health / Incident JSON).

## Common variables (shipped)

| Variable | Dashboards | Datasource / query family | Selection | Default | Notes |
| --- | --- | --- | --- | --- | --- |
| `$workflow` | all 7 shipped | Prometheus `label_values(bioetl_workflow_universe, workflow)` | Single + Include All | `All` / `$__all` | Shared shell context |
| `$pipeline` | all 7 shipped | Universe per board (see `selector-contracts.yaml#pipeline_universe_contract`) | Single | Overview: `All`; else `unknown` | Canonical pipeline scope |
| `$run_type` | all 7 shipped | Same universe as `$pipeline` | Multi + Include All | Overview: `All`; else `backfill` | Never hand off `run_type=unknown` |
| `$run_id` | all 7 shipped | BioETL Ops HTTP filter-options | Single, no Include All | `-` | Identity only; not PromQL |
| `$stage` | `bioetl-runtime`, `bioetl-dq-v2` | Runtime expected-stage / DQ processed totals | Multi + Include All | `All` / `$__all` | Bounded stage filter |

## Dashboard-specific variables (shipped)

| Variable | Dashboard | Selection | Default | Notes |
| --- | --- | --- | --- | --- |
| `$provider` | `bioetl-provider-health-v2`, `bioetl-incident-v1` | Single | `unknown` | Derived from pipeline/workflow when set |
| `$pipeline_context` | `bioetl-provider-health-v2` | Hidden | `unknown` | Return-path only |
| `$adapter` | `bioetl-provider-health-v2` | Hidden detail | dynamic | Detail-only breakdown |
| `$provider_hint` | `bioetl-runtime` | Hidden | first pipeline segment | Provider-scoped alert panels only |

## Dependency chains (shipped)

- **Shared shell (all 7):** `workflow` / `pipeline` / `run_type` feed
  `/ops/control-plane/filter-options` for `$run_id`; primary links preserve
  `$run_id` as HTTP identity.
- **`bioetl-runtime`:** `$run_type` depends on `$pipeline`; `$stage` depends on
  pipeline scope; hidden `$provider_hint` from pipeline name.
- **`bioetl-dq-v2`:** `$run_type` depends on `$pipeline`; `$stage` on pipeline +
  run_type.
- **`bioetl-provider-health-v2`:** `$provider` is primary business selector;
  shell is secondary; hidden `$pipeline_context` + `$adapter`.
- **`bioetl-incident-v1`:** shell + `$provider` for triage.
- **`bioetl-run-explorer-v1`:** shell only; canonical Ops HTTP ID/Processed hub.
- **`bioetl-overview-v2` / `bioetl-control-plane-v1`:** shell only; aggregate
  Status does not use `$run_id` as PromQL scope.

## Retired boards (do not reintroduce)

| Retired UID | Replacement |
| --- | --- |
| `bioetl-workflow-overview` | Runtime workflow band |
| `bioetl-alerts-slo` | Overview Alert/SLO row |
| `bioetl-silver-reject-explorer` | CLI `bioetl quarantine inspect` + DQ reject panels |

Historical selector names (`$status`, `$step_status`, `$step_kind`,
`$workflow_context`, `$pipeline_context_exact`, `$quarantine_run_id`,
`$payload_hash`, …) belonged to those retired boards and MUST NOT reappear on
primary Prometheus dashboards.

## Validation checklist

- [ ] Every variable in `templating.list` has a non-empty `description`
- [ ] Shared shell present on all 7 shipped dashboards
- [ ] `$pipeline` / `$provider` fail-closed boards remain single-select
- [ ] `$stage` defaults to All on Runtime + DQ
- [ ] `$provider` defaults to unknown; derivation documented
- [ ] No retired-board variables listed as currently shipped

## Related references

- [selector-architecture.md](selector-architecture.md)
- [dashboard-inventory.md](dashboard-inventory.md)
- [dashboard-v2-usage.md](dashboard-v2-usage.md)
- [design-system.md](design-system.md)
- `grafana/README.md`
- `tests/integration/test_grafana_variable_reference.py`
- `tests/integration/test_grafana_selector_contract.py`
