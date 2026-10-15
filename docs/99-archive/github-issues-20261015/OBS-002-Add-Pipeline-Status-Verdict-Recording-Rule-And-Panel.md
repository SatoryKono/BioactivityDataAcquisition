# Add Pipeline Status Verdict Recording Rule And Panel

**Status**: open
**GitHub Issue**: [#4830](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4830)
**Issue State**: open
**Synced**: 2026-05-30
**Priority**: P2
**Labels**: `enhancement`, `layer:infrastructure`, `priority:medium`
**Last audited**: 2026-05-30

## Problem

The observability audit (OBS-002 / p-wf-01) flagged that a Pipeline Status
verdict must not be driven only by the last observed stage: any intermediate
`FAILED` stage/run must override a final `COMPLETED`. Today the workflow
overview exposes failed-run evidence (`Failed Entity Pipeline Runs / Range`,
`bioetl_pipeline_runs_total{status="failed"}`) but there is no single
first-screen verdict gauge that fails closed when an intermediate failure
occurred inside the selected window.

Unlike OBS-001 (Batch Status), this is achievable now with existing metrics and
the established recording-rule pattern; no new domain instrumentation is needed.

## Evidence

- `grafana/prometheus-rules/bioetl_observability.yml`
  (existing `bioetl_runtime_current_status`, `bioetl_l1_workflow_global_status`
  recording rules establish the verdict pattern)
- `grafana/prometheus-rules/tests/bioetl_observability.test.yml`
- `grafana/dashboards/bioetl-workflow-overview.json`
- existing metrics: `bioetl_pipeline_runs_total{status}`,
  `bioetl_stage_records_total`, `bioetl_runtime_current_status`

## Proposed Solution

Add a recording rule (e.g. `bioetl_workflow_pipeline_verdict_status`) that maps
a pipeline/run_type window to a fail-closed verdict:

- `2` (CRIT) if any `bioetl_pipeline_runs_total{status="failed"}` increase > 0
  in the window (intermediate failure overrides completion)
- `1` (WARN) if runs are active but not yet terminal
- `0` (OK) only when terminal success is observed and no failure increase exists
- absent/`null` => `UNKNOWN`

Add a first-screen Pipeline Status stat panel on
`bioetl-workflow-overview.json` reading the new recording rule with the
canonical `0=OK / 1=WARN / >=2=CRIT / null=UNKNOWN` mapping, neutral colors, and
a drill-down dataLink to Runtime / Control Plane.

## Scope

- new recording rule in `grafana/prometheus-rules/bioetl_observability.yml`
- promtool unit test in `grafana/prometheus-rules/tests/bioetl_observability.test.yml`
- Pipeline Status panel in `bioetl-workflow-overview.json`
- bind any new alert (if added) to `configs/quality/observability_slo_alert_contract.yaml`
- update affected dashboard/rules contract tests

## Non-Goals

- do not introduce `run_id`-cardinality PromQL on dashboards
- do not depend on `bioetl_run_ledger_status` (metric does not exist)
- do not duplicate verdict logic into PromQL math on the panel beyond the
  status mapping

## Acceptance Criteria

- a single Pipeline Status verdict reads CRIT whenever an intermediate failure
  occurred in the window, even if a later run completed
- recording rule has a passing promtool unit test
- dashboard/rules contract and metric-semantics tests pass

## Validation

```bash
python -m pytest -q tests/integration/test_prometheus_rules_config.py \
  tests/integration/test_grafana_dashboard_links.py \
  tests/integration/test_grafana_dashboard_metric_semantics.py \
  tests/architecture/test_observability_dashboard_contracts.py
# promtool (if available locally):
# promtool check rules grafana/prometheus-rules/bioetl_observability.yml
# promtool test rules grafana/prometheus-rules/tests/bioetl_observability.test.yml
```

## Risks

- a verdict rule that does not fail closed on missing telemetry would re-create
  the false-`COMPLETED` problem; keep `UNKNOWN` distinct from `OK`
- window-based failure detection must align with the existing 15m/30m recording
  rule conventions to avoid verdict flapping

## Related

- companion of `OBS-001` (Batch Status), which is blocked on core wiring
- builds on the `Failed Entity Pipeline Runs / Range` panel added during the
  dashboard refactor
