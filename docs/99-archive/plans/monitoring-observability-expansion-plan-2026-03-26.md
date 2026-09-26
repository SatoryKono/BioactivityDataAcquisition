# Monitoring And Traceability Observability Expansion Plan

*Status: Working planning artifact (non-normative)*
*Created: 2026-03-26*
*Scope: incremental expansion of existing Prometheus/Grafana observability for control-plane and lineage rollout*

## Freshness note

This document is a bounded implementation plan, not a replacement for the
canonical monitoring contract. If this plan conflicts with active guides or
reference contracts, the active documents win:

- `docs/03-guides/metrics-monitoring.md`
- `docs/04-reference/contracts/observability.md`
- `docs/05-operations/01-monitoring-guide.md`
- `docs/04-reference/contracts/run-manifest-ledger.md`

## Goal

Expand the current monitoring stack so that recent traceability and
control-plane changes become observable in the same operational surface as the
existing runtime, DQ, and provider-health signals.

The intended outcome is not a second monitoring architecture. The outcome is a
targeted extension of the current `bioetl_*` metrics catalog, Grafana
dashboards, Prometheus alert rules, and operational docs.

## Why this plan exists

The repository already has:

- a published monitoring guide and metrics catalog;
- accepted observability architecture via ADR-017;
- canonical observability contract and alert baseline;
- active Grafana dashboards and Prometheus rules;
- immutable run manifest and append-only run ledger contracts.

What is still missing is a coherent rollout plan for exposing the new
traceability and control-plane surfaces in Prometheus/Grafana without creating
duplicate docs, duplicate naming conventions, or high-cardinality metrics.

## Guardrails

The implementation must follow these constraints:

1. Do not publish planning content under `docs/03-guides/` as if it were a
   normative guide.
1. Do not introduce a second metric naming scheme. New metrics must follow the
   canonical `bioetl_*` `snake_case` convention.
1. Do not bypass the existing generic `MetricsPort` pattern. New metrics must
   be defined in the existing observability metric definition modules and
   registered through the Prometheus adapter path already used by the project.
1. Do not copy the current high-cardinality drift of `run_id` labels into new
   metrics.
1. Do not model per-record, per-field, or per-path lineage as Prometheus
   labels. Prometheus is for aggregate operational signals; run-specific
   inspection remains the job of manifest, ledger, and sidecar inspection.
1. Prefer extending existing dashboards and alert rule files before adding new
   top-level assets.

## Current state summary

### Existing monitoring surfaces

- Prometheus exposition endpoint on the local BioETL process.
- Existing dashboards:
  - `grafana/dashboards/bioetl-overview-v2.json`
  - `grafana/dashboards/bioetl-dq-v2.json`
  - `grafana/dashboards/bioetl-provider-health-v2.json`
- Existing alert rules:
  - `grafana/prometheus-rules/bioetl_observability.yml`
- Existing datasource and Prometheus provisioning:
  - `grafana/provisioning/datasources-core/prometheus.yml`
  - `grafana/prometheus.yml`

### Existing traceability/control-plane surfaces

- Immutable run manifest contract with `code_provenance`, `source_refs`, and
  `planned_artifacts`.
- Append-only run ledger with lifecycle and lineage events plus
  `metrics_snapshot`.
- CLI inspection already available through `bioetl run-manifest show` and
  `bioetl run-manifest diff`.

### Observability gaps for the current rollout

1. No dedicated aggregate metrics for manifest creation, ledger appends, and
   checkpoint compatibility outcomes.
1. No aggregated operational metrics for lineage fragment emission or lineage
   completeness by layer.
1. No Grafana row or dashboard focused on control-plane and lineage health.
1. No alert set covering control-plane write failures or lineage completeness
   regressions.
1. Existing documentation does not yet connect monitoring workflows with the
   run manifest/run ledger inspection path.

## Proposed rollout

### Phase 1. Contract alignment and documentation sync

Update the active docs first so the monitoring expansion has a single published
story:

- update `docs/04-reference/contracts/observability.md` with an explicit
  section for control-plane and lineage monitoring;
- update `docs/03-guides/metrics-monitoring.md` with the approved new metric
  names and low-cardinality label policy;
- update `docs/05-operations/01-monitoring-guide.md` with dashboard usage for
  control-plane and traceability troubleshooting;
- update `docs/03-guides/dashboards/monitoring-index.md` if new dashboard
  assets or rows are added.

Definition of done for Phase 1:

- no duplicate monitoring guide is introduced;
- active docs describe the new signals using the existing conventions;
- new monitoring work clearly points users to manifest/ledger inspection for
  run-level investigation.

### Phase 2. Metrics expansion in the existing observability stack

Add new low-cardinality metrics through the existing metric definition and
registration flow.

Candidate metrics to evaluate and implement:

| Candidate metric                               | Type    | Labels                                   | Purpose                                            |
| ---------------------------------------------- | ------- | ---------------------------------------- | -------------------------------------------------- |
| `bioetl_control_plane_manifest_writes_total`   | Counter | `pipeline,run_type,status`               | Track successful and failed manifest persistence   |
| `bioetl_control_plane_ledger_appends_total`    | Counter | `pipeline,event_type,status`             | Track ledger append outcomes                       |
| `bioetl_checkpoint_compatibility_events_total` | Counter | `pipeline,disposition`                   | Observe resume compatibility outcomes              |
| `bioetl_lineage_fragments_emitted_total`       | Counter | `pipeline,layer,status`                  | Count lineage fragment publication attempts        |
| `bioetl_lineage_refs_missing_total`            | Counter | `pipeline,layer,ref_type`                | Surface missing upstream references                |
| `bioetl_composite_source_selection_total`      | Counter | `pipeline,decision_type,selected_source` | Observe composite merge/source-selection decisions |

Label policy for new metrics:

- allowed labels: `pipeline`, `run_type`, `status`, `layer`, `event_type`,
  `disposition`, `ref_type`, `decision_type`, `selected_source`;
- forbidden labels: `run_id`, `manifest_id`, filesystem paths, dataset version
  hashes, source batch IDs, field names, record IDs.

Expected code touchpoints:

- `src/bioetl/infrastructure/observability/_metrics_defs_core.py`
- `src/bioetl/infrastructure/observability/_metrics_defs_pipeline.py`
- `src/bioetl/infrastructure/observability/prometheus_metrics.py`
- application or infrastructure services that emit run-manifest, run-ledger,
  checkpoint, and lineage events

Definition of done for Phase 2:

- all new metrics use the `bioetl_*` convention;
- no new high-cardinality labels are introduced;
- Prometheus registration remains centralized in the existing adapter path.

### Phase 3. Dashboard expansion

Prefer incremental extension of current dashboards before introducing a new
dashboard file.

Recommended dashboard work order:

1. Extend `grafana/dashboards/bioetl-overview-v2.json` with a compact
   control-plane health row:
   - manifest writes;
   - ledger append success/failure;
   - checkpoint compatibility events.
1. Extend `grafana/dashboards/bioetl-dq-v2.json` only where lineage and DQ
   overlap operationally:
   - missing lineage references;
   - lineage completeness versus DQ failures.
1. Introduce a dedicated `bioetl-control-plane-v1.json` only if the added
   panels materially overload the existing overview dashboard.

Dashboard requirements:

- preserve existing variable model where practical;
- avoid per-run dashboard filtering based on `run_id`;
- link operational investigation steps to run-manifest CLI and runbooks.

Definition of done for Phase 3:

- operators can see control-plane and lineage health without opening raw JSON
  artifacts;
- the dashboard index documents the canonical source of the new panels.

### Phase 4. Alert rule expansion

Extend the existing rule set in
`grafana/prometheus-rules/bioetl_observability.yml`.

Candidate alert families:

- `ControlPlaneManifestWriteFailures`
- `RunLedgerAppendFailures`
- `CheckpointCompatibilityBlocks`
- `LineageReferencesMissing`
- `LineageFragmentEmissionStopped`

Alerting guardrails:

- severities must map to the current alert baseline in the observability
  contract;
- prefer reuse of existing runbooks until a dedicated control-plane runbook is
  justified;
- alerts should fire on aggregate operational failure patterns, not on one-off
  run-local details better handled via CLI inspection.

Definition of done for Phase 4:

- alert names, severities, and runbook links fit the current observability
  baseline;
- control-plane and lineage failures have at least one actionable operator
  alert path.

### Phase 5. Validation and regression protection

Validation must cover both runtime observability and documentation drift.

Required checks:

- unit tests for new metric definitions and adapter registration;
- dashboard contract validation for any changed panels;
- Prometheus rule validation for the updated alert file;
- documentation sync so the published monitoring docs match the metric catalog;
- a smoke run proving that manifest/ledger events and aggregate metrics are both
  emitted during a pipeline run.

Additional explicit check:

- verify that no new metric labels introduce `run_id` or similar
  high-cardinality identifiers.

## File-level change plan

### Documentation

- `docs/04-reference/contracts/observability.md`
- `docs/03-guides/metrics-monitoring.md`
- `docs/05-operations/01-monitoring-guide.md`
- `docs/03-guides/dashboards/monitoring-index.md`
- `docs/04-reference/contracts/run-manifest-ledger.md`

### Grafana/Prometheus assets

- `grafana/dashboards/bioetl-overview-v2.json`
- `grafana/dashboards/bioetl-dq-v2.json`
- `grafana/prometheus-rules/bioetl_observability.yml`
- optional: `grafana/dashboards/bioetl-control-plane-v1.json`

### Runtime implementation touchpoints

- `src/bioetl/infrastructure/observability/_metrics_defs_core.py`
- `src/bioetl/infrastructure/observability/_metrics_defs_pipeline.py`
- `src/bioetl/infrastructure/observability/prometheus_metrics.py`
- control-plane and lineage emitters under `src/bioetl/domain/control_plane/`
  and the corresponding application/infrastructure orchestration services

## Explicit non-goals

- no new standalone monitoring architecture;
- no new published monitoring guide separate from the canonical docs;
- no field-level lineage metrics in Prometheus;
- no per-run Prometheus labels for manifest IDs, dataset paths, or source batch
  IDs;
- no assumptions about a multi-service deployment when the current runtime
  profile remains local-only single-instance.

## Recommended execution order

1. Align contracts and docs.
1. Add low-cardinality metrics.
1. Extend existing dashboards.
1. Add alert rules.
1. Add tests and smoke validation.

## Acceptance criteria

- Operators can detect manifest/ledger/control-plane failures from Grafana or
  Prometheus without inspecting raw files first.
- Operators can see aggregated lineage completeness signals by pipeline/layer.
- Run-specific deep inspection still routes through manifest and ledger
  inspection rather than Prometheus labels.
- Active docs describe the rollout without introducing a second source of
  truth.
- The implementation does not worsen the known high-cardinality drift already
  documented in observability specs.
