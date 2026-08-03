# Silver Filter Rejects Observability Plan

## Context

This document captures the current-state analysis, target design, rollout plan,
and implementation backlog for improving operator visibility into Silver filter
rejections in BioETL.

Scope:

- show total Silver filter rejects quickly
- inspect record-level rejection reasons conveniently
- aggregate reject counts by reason
- use both CLI/quarantine and Grafana where appropriate

Constraints:

- no code changes in this planning document
- recommendations must align with the current BioETL repository
- local-only runtime and existing architecture boundaries must be preserved

## Recommended Skills And Agents

Recommended skills:

- `py-plan-bot`
- `grafana-dashboard-extension`
- `prometheus-metric-discovery`
- `prometheus-query-debugger`
- `architecture-guardian`

Recommended agent split:

- Agent 1 `explorer`: CLI/quarantine UX and data-flow analysis
- Agent 2 `explorer`: Grafana/Prometheus feasibility and dashboard design
- Agent 3 `explorer`: architecture, rollout, testing, docs impact

## Current State

- Pipeline run output already exposes total Silver filter rejects via
  `Silver filter rejects` in
  `src/bioetl/interfaces/cli/commands/domains/run/result_presenter.py`.
- Silver filter rejections are persisted to unified quarantine storage with:
  - `error_code = FILTERED_OUT_SILVER`
  - `classification = filter_rejection`
  - `quarantine_category = silver_filter`
    as implemented in
    `src/bioetl/application/core/quarantine_manager.py`.
- Filter evaluation already produces structured reject metadata in
  `src/bioetl/domain/filtering/_filter_decision.py` and
  `src/bioetl/domain/filtering/_filter_evaluator.py`, including:
  - `reason_code`
  - `rule_type`
  - `field`
  - `operator`
  - `expected`
  - `actual`
  - `message`
- Unified quarantine storage already exists as a Delta table under
  `data/output/quarantine/common.quarantine/`, documented in
  `docs/03-guides/local-storage-layout.md` and implemented in
  `src/bioetl/infrastructure/quarantine/unified.py`.
- `bioetl quarantine inspect` already fetches full records including deserialized
  `payload` and `error_details`, but current CLI rendering truncates the output to
  `Error + Payload` in `src/bioetl/interfaces/cli/formatters.py`.
- `bioetl quarantine stats` currently aggregates only:
  - `by_error_code`
  - `by_status`
    and does not provide a by-reason or by-field breakdown.
- Existing shipped Grafana dashboards already visualize `filtered_out` volume:
  - `grafana/dashboards/bioetl-overview-v2.json`
  - `grafana/dashboards/bioetl-dq-v2.json`
  - `grafana/dashboards/bioetl-runtime.json`
- Existing Grafana intent is documented in
  `docs/reports/grafana_silver_filter_rejections_prompt.md`.
- Prometheus already provides high-level reject volume through
  `bioetl_records_processed_total{stage="filtered_out"}`.
- Prometheus also records bounded quarantine reason labels through
  `quarantine_records_total`, but current normalization collapses Silver filter
  rejects to a coarse `filtered_out_silver` bucket in
  `src/bioetl/infrastructure/observability/prometheus_metric_label_dispatch.py`.

## Gaps

- There is no operator-friendly CLI path for viewing the detailed rejection
  reason for each Silver-filtered record.
- There is no built-in grouped CLI summary for:
  - counts by `reason_code`
  - counts by `field`
  - counts by `rule_type`
  - counts by composite cause
- Current `quarantine inspect` output hides the most useful reject diagnostics
  even though the data is already present in storage.
- Current `quarantine stats` does not expose Silver reject analytics beyond
  `FILTERED_OUT_SILVER` as a single error code.
- Grafana already covers total reject volume, but not exact reason-level
  analytics for operators.
- Prometheus is sufficient for total/trend/reject ratio, but not sufficient for
  exact reason-level analytics if the goal is "how many records were rejected for
  each specific reason" without additional aggregation.
- Docs and runbooks still frame quarantine primarily as a DQ failure path and do
  not yet present Silver filter rejects as a first-class operator workflow.

## Recommended Target Design

- Keep quarantine as the canonical record-level source of truth.
- Keep Grafana as the primary interface for volume, trend, ratio, and operator
  summary views.
- Keep CLI as the primary interface for record-level inspection and exact
  by-reason analysis.
- Treat Silver filter rejects as a distinct operator-facing concept, separate
  from DQ quarantine.
- Define the canonical stable reason key for aggregation as:
  - `reason_code`
  - `rule_type`
  - `field`
  - `operator`
- Treat `message` as human-readable display text only, not as the primary
  aggregation key.
- Use Prometheus for high-level observability, but rely on quarantine-derived
  aggregation for exact reason analytics.

## CLI Plan

### Operator Goals

- see how many Silver rejects happened
- see why they happened overall
- inspect the exact cause for each record

### Target CLI UX

Suggested target capabilities:

- `summary`
  - total rejects
  - top reasons
  - top fields
  - ratio to Bronze
- `inspect`
  - one record per block
  - includes `payload_hash`, `message`, `reason_code`, `rule_type`, `field`,
    `operator`, `expected`, `actual`
- `group-by`
  - by `reason_code`
  - by `field`
  - by `rule_type`
  - by `reason_code + field`

### Design Guidance

- Build on top of `bioetl quarantine inspect` and `bioetl quarantine stats`.
- Avoid requiring operators to memorize `FILTERED_OUT_SILVER`.
- Prefer explicit Silver-reject filtering in UX rather than generic quarantine
  terminology.
- Reuse the existing quarantine table and deserialized `error_details`.
- Do not move record analytics into the domain layer; keep rendering and query
  logic in CLI/application/infrastructure boundaries.

## Grafana Plan

### What Grafana Already Covers Well

- total reject volume
- recent reject trend
- reject ratio using `filtered_out` vs `bronze`

### What Grafana Should Become

Grafana should be the operator summary layer for:

- total Silver rejects over selected time range
- reject trend over time
- reject ratio to Bronze throughput
- breakdown by pipeline and run type
- coarse reason family where feasible

### What Grafana Should Not Become

- the primary raw record inspection interface
- a free-text reason explorer backed by high-cardinality labels

### Recommended Dashboard UX

- Preserve existing `filtered_out` panels as baseline.
- Add or refine panels that make Silver rejects visually explicit and separate
  from DQ quarantine.
- Add dashboard help text or drilldown hints:
  - "Use CLI/quarantine for record-level root cause"
  - "This panel shows summary only"
- Plan exact by-reason and by-field panels only after a bounded aggregation
  source exists.

## Metrics/Data Model Implications

### Already Available

- `bioetl_records_processed_total{pipeline, stage, run_type}`
- `stage="filtered_out"` for Silver reject volume
- `quarantine_records_total{pipeline, reason}` with bounded reason labels

### Not Yet Sufficient For Exact Reason Analytics

- Prometheus does not currently carry exact `reason_code`, `field`, and
  `rule_type` for Silver reject analytics.
- The current bounded reason label intentionally collapses detail to avoid
  cardinality problems.

### Recommended Data Model Direction

- Keep exact record-level details in quarantine.
- Add a bounded aggregation layer for dashboard analytics if reason-level Grafana
  views are required.
- Do not expose raw `message` values as Prometheus labels.
- Do not expose unconstrained `field` or composite reason text as labels without
  an explicit bounded-label policy.

## Implementation Options

### Minimal

- Improve CLI rendering for `quarantine inspect`
- Add by-reason summary in CLI using existing quarantine data
- Keep Grafana limited to existing `filtered_out` summary panels

Best for:

- fastest operator value
- lowest architectural risk

### Balanced

- Minimal option plus:
  - explicit Silver-reject-oriented CLI workflow
  - quarantine-derived grouped summaries
  - bounded aggregation source for Grafana reason panels

Best for:

- operator usability
- sustainable dashboard analytics

### Extended

- Balanced option plus:
  - richer drilldowns
  - dedicated Silver reject dashboard section
  - broader breakdowns by field, rule, pipeline, and time windows

Best for:

- mature observability program
- longer-term operator analytics

## Rollout Plan

### Phase 1: Taxonomy And UX Contract

- freeze terminology for Silver filter rejects
- define stable aggregation key
- define CLI and Grafana responsibilities
- document the distinction between:
  - DQ quarantine
  - Silver filter rejects

### Phase 2: CLI Operator Workflow

- extend record-level rendering
- add by-reason summary
- add grouped breakdown modes
- ensure operators can inspect exact reject causes without raw Delta reads

### Phase 3: Documentation And Runbooks

- update running guide
- update quarantine runbook
- update troubleshooting guidance
- document when to use Grafana versus CLI

### Phase 4: Grafana Summary Hardening

- refine existing `filtered_out` panels
- ensure naming and operator wording are explicit
- add ratio and trend if still missing in operator workflow

### Phase 5: Reason-Level Dashboard Analytics

- design bounded aggregation source
- add top reasons and top fields panels
- add drilldown guidance from Grafana to CLI/quarantine

## Risks

- High-cardinality Prometheus labels if exact reasons are exported directly.
- Semantic confusion if DQ quarantine and Silver rejects are merged in UX.
- Unstable analytics if aggregation uses `message` instead of structured keys.
- Overloading Grafana with drilldown responsibilities better handled by CLI.
- Architecture drift if dashboard- or CLI-specific logic leaks into domain code.

## Validation Plan

### Unit Tests

- filter reason extraction remains stable
- grouped aggregation produces expected counts
- rendering handles zero-state and missing optional fields

### Integration Tests

- `quarantine inspect` for `FILTERED_OUT_SILVER`
- `quarantine stats` by-reason summaries
- deserialization of `error_details`

### Dashboard/Config Tests

- verify `stage="filtered_out"` panels still exist
- verify zero-safe PromQL patterns remain valid
- verify new panels use approved metrics and variables

### Architecture Validation

- verify CLI rendering stays in interface layer
- verify aggregation/query logic stays outside domain
- verify observability changes preserve label-cardinality guardrails

## Backlog

### Epic A: Silver Rejects CLI Visibility

Tasks:

- Add explicit CLI workflow for `FILTERED_OUT_SILVER`
- Expand record-level output to include structured reject fields
- Add summary mode for top reasons and top fields
- Add grouped breakdowns for common operator pivots

Likely files:

- `src/bioetl/interfaces/cli/commands/domains/quarantine/command.py`
- `src/bioetl/interfaces/cli/commands/domains/quarantine/support.py`
- `src/bioetl/interfaces/cli/commands/domains/quarantine/rendering.py`
- `src/bioetl/interfaces/cli/formatters.py`
- `src/bioetl/infrastructure/quarantine/operations.py`

Acceptance criteria:

- operator can view only Silver rejects without manual filtering
- operator can inspect record-level reject reasons directly in CLI
- operator can view counts by cause without manual post-processing

### Epic B: Canonical Reason Model

Tasks:

- Define stable aggregation key
- Separate human-readable text from analytics key
- Document how filter decisions map into quarantine metadata and UI

Likely files:

- `src/bioetl/application/core/quarantine_manager.py`
- `src/bioetl/domain/filtering/_filter_decision.py`
- `src/bioetl/domain/filtering/_filter_evaluator.py`
- `configs/entities/chembl/activity.yaml`

Acceptance criteria:

- analytics keys remain stable if message wording changes
- documentation clearly distinguishes display message from reason key

### Epic C: Grafana Operator UX

Tasks:

- Baseline and preserve current `filtered_out` panels
- Refine total, ratio, and trend panels
- Add operator guidance for drilldown path
- Plan exact by-reason panels only after bounded aggregation exists

Likely files:

- `grafana/dashboards/bioetl-overview-v2.json`
- `grafana/dashboards/bioetl-dq-v2.json`
- `grafana/dashboards/bioetl-runtime.json`
- `grafana/README.md`
- `docs/reports/grafana_silver_filter_rejections_prompt.md`
- `docs/03-guides/dashboards/dashboard-v2-usage.md`

Acceptance criteria:

- Grafana clearly separates Silver rejects from DQ quarantine
- operator can assess volume and trend quickly
- dashboard guidance tells the operator when to switch to CLI

### Epic D: Aggregation Source For Reason-Level Analytics

Tasks:

- Evaluate bounded aggregation source for Grafana by-reason panels
- Compare minimal, balanced, and extended observability paths
- Preserve low-cardinality metric policy

Likely files:

- `src/bioetl/infrastructure/observability/prometheus_metrics.py`
- `src/bioetl/infrastructure/observability/prometheus_metric_label_dispatch.py`
- `src/bioetl/infrastructure/observability/prometheus_metric_label_policy_sets.py`
- `docs/03-guides/metrics-monitoring.md`

Acceptance criteria:

- one canonical source exists for dashboard by-reason analytics
- Prometheus label policy remains bounded and reviewable

### Epic E: Docs And Runbooks

Tasks:

- Update running guide for Silver reject workflow
- Update quarantine management runbook
- Update troubleshooting docs
- Clarify local storage path and drilldown workflow

Likely files:

- `docs/03-guides/running-pipelines.md`
- `docs/03-guides/local-storage-layout.md`
- `docs/03-guides/troubleshooting.md`
- `docs/05-operations/runbooks/quarantine-management.md`

Acceptance criteria:

- operator can follow the full workflow without reading code
- docs no longer imply quarantine is only for DQ failures
- CLI and Grafana guidance are aligned

## Definition Of Done

- CLI supports record-level and grouped Silver reject analysis.
- Grafana supports fast operator summary for Silver rejects.
- DQ quarantine and Silver rejects remain semantically separate.
- Exact causes are aggregated using stable structured keys.
- Docs, tests, and dashboard checks align with the final operator workflow.
