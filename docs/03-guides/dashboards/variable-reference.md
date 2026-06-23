______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-05-16'

______________________________________________________________________

# Grafana Dashboard Variable Reference

Дата сверки: **2026-05-16**
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
- Primary operator dashboards `0..5` expose the shared context shell:
  `$workflow`, `$pipeline`, `$run_type`, `$run_id`. Role-specific selectors
  such as `$stage`, `$provider`, `$status`, `$step_status`, `$step_kind`, and
  hidden handoff vars are additive.
- `$workflow` is context/evidence unless a dashboard explicitly documents a
  truthful current-status intersection. It does not force a
  workflow -> pipeline dependency.
- `$workflow` remains single-select with Include All across primary dashboards,
  including `bioetl-workflow-overview`, so cross-dashboard handoffs preserve
  one coherent workflow shell value while aggregate `All` scope stays
  available.
- Pipeline-scoped operator dashboards use single-select `$pipeline`, except
  Overview where intentional landing default = `All`.
- `$run_type` always uses include-all fallback. Missing context is represented as
  `All`, not `unknown`.
- `$run_id` in primary operator dashboards is HTTP-backed control-plane
  identity context. It feeds the shared `ID` panel, is preserved between
  primary dashboards that expose `$run_id`, and MUST NOT leak into Prometheus
  label filtering or Silver forensic selectors.
  Its option list is constrained by the current `workflow`, `pipeline`, and
  `run_type` shell context through `/ops/control-plane/filter-options`; this
  does not make current-status PromQL exact-run scoped.
- Exact forensic identifiers (`$quarantine_run_id`, `$payload_hash`) in
  `bioetl-silver-reject-explorer` remain explorer-only narrowing filters.
- Hidden context variables are allowed only when they preserve return-path,
  exact-run handoff, or detail-only scope, например `$pipeline_context`,
  `$workflow_context`, and `$adapter`.
- Variable behavior is standardized by the shared operator context shell plus
  role-specific extensions, not by one flat universal query model.
## Common variables

| Variable | Dashboards | Datasource / query family | Selection mode | Default / fallback | Notes |
| --- | --- | --- | --- | --- | --- |
| `$workflow` | `bioetl-overview-v2`, `bioetl-control-plane-v1`, `bioetl-runtime`, `bioetl-provider-health-v2`, `bioetl-dq-v2`, `bioetl-workflow-overview`, `bioetl-alerts-slo` | Prometheus `label_values(bioetl_workflow_runs_total, workflow)` | Single-select with Include All | `All` / `$__all` | Context/evidence selector in the shared operator shell unless a dashboard documents a truthful current-status intersection. Silver Reject Explorer intentionally does not own this selector. |
| `$pipeline` | `bioetl-overview-v2`, `bioetl-control-plane-v1`, `bioetl-runtime`, `bioetl-provider-health-v2`, `bioetl-dq-v2`, `bioetl-workflow-overview`, `bioetl-silver-reject-explorer`, `bioetl-alerts-slo` | Prometheus label query from each dashboard's bounded universe: Overview/DQ/Provider/Workflow/Alerts use `bioetl_records_processed_total`; Runtime uses `bioetl_runtime_pipeline_run_type_universe`; Control Plane uses `bioetl_control_plane_run_type_universe`; Explorer uses concrete pipeline scope for Quarantine API | Single-select | `All` on Overview; otherwise fail-closed `unknown` | Canonical pipeline context. Explorer requires one concrete pipeline. Provider/Workflow/Alerts expose it as context shell, not as their primary business selector. |
| `$run_type` | `bioetl-overview-v2`, `bioetl-control-plane-v1`, `bioetl-runtime`, `bioetl-provider-health-v2`, `bioetl-dq-v2`, `bioetl-workflow-overview`, `bioetl-silver-reject-explorer`, `bioetl-alerts-slo` | Prometheus label query from the same bounded universe as `$pipeline`, or explorer API context | Multi-select with Include All | `All` / `$__all` | Cross-dashboard links MUST NOT pass `run_type=unknown`. |
| `$run_id` | `bioetl-overview-v2`, `bioetl-control-plane-v1`, `bioetl-runtime`, `bioetl-provider-health-v2`, `bioetl-dq-v2`, `bioetl-workflow-overview` | Quarantine Explorer HTTP `/ops/control-plane/filter-options?dimension=run_id&response_shape=list&workflow=${workflow}&pipeline=${pipeline}&run_type=${run_type:csv}` | Single-select, no Include All | `-` | Preserved identity context for shared HTTP `ID`/details panels and primary-dashboard handoffs; not a Prometheus label. Generic inbound links to Silver Reject Explorer must not map this value into `$quarantine_run_id`; outbound explorer/alert links do not export primary `$run_id`. |
| `$stage` | `bioetl-runtime`, `bioetl-dq-v2` | Runtime: `bioetl_pipeline_stage_expected`; DQ: `bioetl_records_processed_total` | Multi-select with Include All | Dynamic Grafana selection | Bounded stage breakdown filter, not a forensic identifier. |

## Dashboard-specific variables

| Variable | Dashboard | Selection mode | Default / fallback | Notes |
| --- | --- | --- | --- | --- |
| `$provider` | `bioetl-provider-health-v2` | Single-select | `unknown` | Fail-closed provider scope for provider triage. |
| `$pipeline_context` | `bioetl-provider-health-v2` | Hidden context var | `unknown` | Preserves source pipeline for return handoff; not a first-class provider filter. |
| `$adapter` | `bioetl-provider-health-v2` | Multi-select with Include All | Dynamic Grafana selection | Detail-only provider breakdown; links may omit it and let target fall back to all adapters. |
| `$reason_code` | `bioetl-silver-reject-explorer` | Multi-select with Include All | `All` / `$__all` | Explorer-only forensic narrowing for bounded reject causes. |
| `$field` | `bioetl-silver-reject-explorer` | Multi-select with Include All | `All` / `$__all` | Explorer-only forensic narrowing for rejected fields. |
| `$quarantine_run_id` | `bioetl-silver-reject-explorer` | Single-select | Empty until selected | Explorer-only forensic selector backed by Quarantine API `dimension=run_id`; MUST NOT appear in Prometheus queries or generic cross-dashboard links. |
| `$payload_hash` | `bioetl-silver-reject-explorer` | Visible textbox | Empty string | Forensic exact-record selector; visible only in the explorer and MUST NOT propagate into other dashboards. |
| `$status` | `bioetl-workflow-overview` | Multi-select with Include All | `All` / `$__all` | Workflow run-status filter. |
| `$workflow_context` | `bioetl-workflow-overview` | Hidden context var | `All` | Exact-run-aware workflow handoff selector. When `$run_id` is selected it resolves workflow identity from the local control-plane catalog; otherwise it falls back to the visible workflow selector text. |
| `$pipeline_context` | `bioetl-workflow-overview` | Hidden context var | `unknown` | Preserves single-pipeline handoff scope for downstream dashboards; multi-pipeline workflows fail-close to `unknown`. |
| `$pipeline_context_exact` | `bioetl-workflow-overview` | Hidden exact-run handoff var | `unknown` | Exact-run-aware pipeline handoff selector. It resolves pipeline from the selected `$run_id` when present, otherwise falls back to `$pipeline_context`. |
| `$run_type_context` | `bioetl-workflow-overview` | Hidden context var | `All` | Preserves effective run_type for single-pipeline workflows; multi-pipeline workflows fail-close to `All`. |
| `$run_type_context_exact` | `bioetl-workflow-overview` | Hidden exact-run handoff var | `All` | Exact-run-aware run_type handoff selector. It resolves run_type from the selected `$run_id` when present, otherwise falls back to `$run_type_context`. |
| `$provider_context` | `bioetl-workflow-overview` | Hidden context var | `unknown` | Preserves inferred provider for downstream Provider Health handoff; multi-pipeline workflows fail-close to `unknown`. |
| `$provider_context_exact` | `bioetl-workflow-overview` | Hidden exact-run handoff var | `unknown` | Exact-run-aware provider handoff selector. It resolves provider from the selected `$run_id` when present, otherwise falls back to `$provider_context`. |
| `$step_status` | `bioetl-workflow-overview` | Multi-select with Include All | `All` / `$__all` | Workflow step-status filter for step evidence panels. |
| `$step_kind` | `bioetl-workflow-overview` | Multi-select with Include All | `All` / `$__all` | Bounded step-kind filter, e.g. `pipeline`, `transform`. |

## Dependency chains

- `0..5 shared context shell`
  - `/ops/control-plane/filter-options` resolves local run-id option lists from
    `workflow`, `pipeline`, and `run_type`
  - `/ops/control-plane/selector-context` can resolve a coherent local selector
    tuple for selector-shell clients; exact `run_id` wins when selected
  - dashboard-to-dashboard links between primary dashboards preserve `$run_id`
    as exact HTTP identity context; links to `Silver Reject Explorer` do not map
    it to `$quarantine_run_id`
  - native Grafana variables do not auto-write sibling selector values, so true
    bidirectional selector synchronization requires a custom selector shell
- `bioetl-runtime`
  - `$workflow`, `$pipeline`, `$run_type`, `$run_id` form the shared context shell
  - `$run_type` depends on `$pipeline`
  - `$stage` depends on runtime-selected scope and expected-stage metric family
- `bioetl-dq-v2`
  - `$workflow`, `$pipeline`, `$run_type`, `$run_id` form the shared context shell
  - `$run_type` depends on `$pipeline`
  - `$stage` depends on `$pipeline` and `$run_type`
- `bioetl-control-plane-v1`
  - `$workflow`, `$pipeline`, `$run_type`, `$run_id` form the shared context shell
  - `$run_id` affects only HTTP-backed identity surfaces: the shared compact
    `ID` panel and the Control Plane-only `/ops/control-plane/identity-evidence`
    detail row
  - `/ops/control-plane/identity-evidence` exposes full identity values in
    tables; those values MUST NOT be copied into Prometheus labels or
    cross-dashboard variable handoffs
- `bioetl-provider-health-v2`
  - `$workflow`, `$pipeline`, `$run_type`, `$run_id` form the shared context shell
  - `$provider` remains the primary provider-health business selector
  - `$pipeline_context` is preserved from source dashboard links
  - `$adapter` is optional detail scope, not required on handoff
- `bioetl-silver-reject-explorer`
  - `$pipeline` is required before Quarantine Explorer reads are trustworthy
  - `$reason_code`, `$field`, `$quarantine_run_id`, `$payload_hash` are explorer-only narrowing filters
- `bioetl-overview-v2`
  - `$workflow`, `$pipeline`, and `$run_type` define the aggregate L0 context
  - `$run_id` is loaded from `/ops/control-plane/filter-options` using
    `$workflow`, `$pipeline`, and `$run_type`, and defaults to `-`
  - selecting a concrete `$run_id` affects only HTTP-backed identity/detail
    panels and is preserved when navigating to other primary dashboards
- `bioetl-workflow-overview`
  - `$workflow`, `$pipeline`, `$run_type`, `$run_id` form the shared context shell
  - `$status`, `$step_status`, `$step_kind` are local to workflow evidence
  - `$pipeline`, `$run_type`, and `$run_id` are context/identity selectors, not live-run Prometheus filters
  - `$workflow_context`, `$pipeline_context_exact`, `$run_type_context_exact`, and `$provider_context_exact` are exact-run-aware hidden handoff selectors backed by `/ops/control-plane/filter-options?exact_run_only=1`
  - `$pipeline_context`, `$run_type_context`, `$provider_context` remain workflow-metric-derived fallback handoff selectors
  - these variables MUST NOT be propagated into non-workflow dashboards

## Role-specific defaults

### L0 / pipeline-scoped dashboards

- `bioetl-overview-v2` intentionally defaults to `Workflow=All`,
  `Pipeline=All`, `Run Type=All`, and `Run ID=-`; the dash means no exact run
  is selected.
- `bioetl-overview-v2` uses control-plane-backed `$run_id=-` for its optional
  `ID` panel only.
- `bioetl-control-plane-v1`, `bioetl-runtime`, `bioetl-dq-v2`, and
  `bioetl-provider-health-v2` expose the same visible context shell, but their
  Status panels remain role-specific and do not use `$run_id` as Prometheus
  scope.
- `bioetl-silver-reject-explorer` fail-closes to `pipeline=unknown` when source
  context is absent.

### Provider triage

- `bioetl-provider-health-v2` defaults to `provider=unknown`.
- Shared `$pipeline` / `$run_type` / `$run_id` are context-shell inputs for
  Provenance, ID, and Processed Records; `$provider` remains the current-status
  selector.
- `$pipeline_context` remains hidden and preserves return-path context only.

### Workflow evidence

- `bioetl-workflow-overview` exposes the shared context shell plus
  `$status`, `$step_status`, and `$step_kind`.
- Pipeline/run-type/run-id values are context and identity aids here; workflow
  Status is selected-range evidence rather than current live-run state.
- Hidden `$workflow_context`, `$pipeline_context_exact`,
  `$run_type_context_exact`, and `$provider_context_exact` preserve exact-run
  handoff scope when `$run_id` is selected, while `$pipeline_context`,
  `$run_type_context`, and `$provider_context` remain workflow-derived
  fallbacks for multi-run scope.

### Explorer forensics

- `bioetl-silver-reject-explorer` requires single-select `$pipeline`.
- `$quarantine_run_id` and `$payload_hash` remain local forensic selectors and do not
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
