# Wire Batch Aggregate Status Into Runtime Observability

**Status**: open
**GitHub Issue**: [#4829](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4829)
**Issue State**: open
**Synced**: 2026-05-30
**Priority**: P2
**Labels**: `enhancement`, `layer:domain`, `layer:application`, `layer:infrastructure`, `priority:medium`
**Last audited**: 2026-05-30

## Problem

The observability audit (OBS-002 / f-004) asked the Batch Status panel to expose
the full batch write lifecycle (`OPEN`, `SEALED`, `WRITING`, `COMMITTED`,
`FAILED`) so batches stop "jumping" from `OPEN` straight to `COMMITTED` on
dashboards.

That panel cannot be implemented faithfully today. The domain aggregate that
models those states is **not wired into the runtime execution path**:

- `BatchStatus` (`OPEN/SEALED/WRITING/COMMITTED/FAILED`) and its transitions
  (`seal()`, `mark_writing()`, `mark_committed()`, `mark_failed()`) exist only
  inside the `bioetl.domain.aggregates` package.
- No `application/` or `infrastructure/` code calls those transitions.
- The live pipeline uses `application/core/batch_executor.py` plus the
  `BatchExecutionState` FSM (`IDLE/STREAMING/PROCESSING/STATE_COMMIT/...`) and
  emits `bioetl_batch_lifecycle_events_total{event=created|written|failed}`.

Adding a `bioetl_batch_status{state=...}` metric without wiring the aggregate
would produce dead/synthetic telemetry with no real source — violating the
project determinism / telemetry-honesty invariants.

## Evidence

- `src/bioetl/domain/aggregates/_batch_status.py`
- `src/bioetl/domain/aggregates/_batch_mixins.py` (`seal/mark_writing/mark_committed/mark_failed`)
- `src/bioetl/domain/aggregates/_batch_lifecycle.py`
- `src/bioetl/application/core/batch_executor.py`
- `src/bioetl/application/core/lifecycle/batch_fsm.py` (`BatchExecutionState`)
- `src/bioetl/application/core/batch_metrics.py` (`track_batch_created/written/failed`)
- `src/bioetl/application/observability/pipeline_metrics.py` (`record_batch_lifecycle_event`)
- `src/bioetl/infrastructure/observability/_metrics_defs_core.py` (`BATCH_LIFECYCLE_EVENTS_TOTAL`)
- `grafana/dashboards/bioetl-workflow-overview.json`

## Proposed Solution

Decide one of two directions and execute it end to end:

**Option A — Adopt the aggregate in the runtime (full fix).**
Drive `Batch` aggregate transitions from the application write path (seal →
writing → committed/failed), then add a transition-event counter
`bioetl_batch_state_transitions_total{pipeline, run_type, state}` (counter, not
gauge, to stay Pushgateway-safe and avoid stale-state reads). Surface it on a
Batch Status panel with `state=~"open|sealed|writing|committed|failed"`.

**Option B — Formally retire the unused aggregate.**
If the runtime will not model these states, document `BatchStatus` as a
non-runtime domain model and keep the existing
`bioetl_batch_lifecycle_events_total{event}` as the only observable batch
signal, updating the audit expectation accordingly.

Option A is the faithful fix; it is a core-pipeline change, not observability-only.

## Scope

- application write-path wiring for `Batch` aggregate transitions (Option A), or
  explicit non-runtime documentation (Option B)
- new metric definition + full registry/export/label-policy/vocab/dispatch chain
  (Option A)
- recorder method in `application/observability/pipeline_metrics.py` (Option A)
- Batch Status panel in `bioetl-workflow-overview.json` (Option A)
- metric registry / golden / contract tests and metrics catalog docs

## Non-Goals

- do not emit synthetic `SEALED/WRITING/COMMITTED` values without a real source
- do not encode domain batch states in PromQL before the metric exists
- do not change unrelated execution-loop FSM semantics

## Acceptance Criteria

- Batch Status panel renders real `open/sealed/writing/committed/failed`
  transitions backed by a shipped metric (Option A), **or**
- the unused aggregate is explicitly documented as non-runtime and the audit
  expectation is closed (Option B)
- metric label-schema and dashboard contract tests pass

## Validation

```bash
python -m pytest -q tests/integration/test_grafana_dashboard_links.py \
  tests/integration/test_grafana_dashboard_metric_semantics.py \
  tests/architecture/test_observability_dashboard_contracts.py
```

## Risks

- Option A touches the core write path and the full metric contract chain;
  high blast radius, requires golden-test updates.
- Emitting a gauge for short-lived batch states risks stale reads in the local
  Pushgateway model; prefer a transition counter.

## Related

- companion of `OBS-002` (Pipeline Status verdict), which is deliverable now
  with existing metrics
