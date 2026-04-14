# Grafana Prompt: Add Silver Filter Rejections

Update the shipped Grafana dashboards to expose **silver filter rejections** as a
first-class signal, separate from DQ quarantine.

## Context

- Runtime behavior was changed so Silver filter failures are routed to quarantine
  with:
  - `classification = "filter_rejection"`
  - `quarantine_category = "silver_filter"`
- CLI output now shows a separate `Silver filter rejects` count.
- We are **not** changing DQ threshold semantics in code. DQ quarantine remains a
  separate concept from silver filter rejection.

## Existing metrics to use

Do **not** invent a new Prometheus metric if current metrics are sufficient.
Use the existing metric:

- `bioetl_records_processed_total{pipeline, stage, run_type}`

Silver filter rejections are already emitted via:

- `bioetl_records_processed_total{stage="filtered_out"}`

Keep DQ quarantine visualized separately via:

- `bioetl_dq_records_quarantined_total{pipeline, error_type, run_type}`

## Dashboards to update

Update these shipped dashboards:

- `grafana/dashboards/bioetl-overview-v2.json`
- `grafana/dashboards/bioetl-dq-v2.json`
- `grafana/dashboards/bioetl-runtime.json`

Review, and update only if needed:

- `grafana/README.md`
- `tests/integration/test_grafana_config.py`
- `tests/integration/test_prometheus_rules_config.py`

## Required dashboard changes

### 1. Overview dashboard

In `grafana/dashboards/bioetl-overview-v2.json`:

- Add a visible stat panel for **Silver Filter Rejects**.
- Query should use `stage="filtered_out"`.
- Follow existing shipped-dashboard conventions for `pipeline` and `run_type`
  variables.
- Prefer a query shape consistent with the rest of the v2 dashboards, for
  example:

```promql
round(sum(increase(bioetl_records_processed_total{pipeline=~"$pipeline", run_type=~"$run_type", stage="filtered_out"}[24h])) or vector(0))
```

- Add a companion ratio panel if it fits the dashboard layout:

```promql
sum(increase(bioetl_records_processed_total{pipeline=~"$pipeline", run_type=~"$run_type", stage="filtered_out"}[24h]))
/
clamp_min(sum(increase(bioetl_records_processed_total{pipeline=~"$pipeline", run_type=~"$run_type", stage="bronze"}[24h])), 1)
```

### 2. DQ dashboard

In `grafana/dashboards/bioetl-dq-v2.json`:

- Add a separate panel for **Silver Filter Rejects**.
- Keep it distinct from **DQ Quarantined**.
- Do **not** merge filter rejects into existing DQ quarantine panels.
- Add a breakdown-by-pipeline or stage panel if space allows.
- Update any quality-ratio/help text so it is explicit:
  - DQ quarantine = `bioetl_dq_records_quarantined_total`
  - Silver filter rejects = `bioetl_records_processed_total{stage="filtered_out"}`

### 3. Runtime dashboard

In `grafana/dashboards/bioetl-runtime.json`:

- Add a runtime triage panel showing recent Silver filter reject volume.
- The panel should help operators distinguish:
  - runtime/DQ problems
  - schema validation failures
  - intentional filter exclusions

Suggested query:

```promql
round(sum(increase(bioetl_records_processed_total{pipeline=~"$pipeline", run_type=~"$run_type", stage="filtered_out"}[1h])) or vector(0))
```

## Constraints

- Keep current dashboard variables unchanged:
  - `pipeline`
  - `run_type`
- Do not introduce a `run_id` variable.
- Do not repurpose DQ quarantine panels to mean filter rejects.
- Use zero-safe PromQL patterns (`or vector(0)`, `clamp_min`) where current
  tests expect them.
- Reuse existing dashboard naming style and shipped-dashboard JSON structure.

## Test updates

Update integration tests so the dashboards remain contract-checked:

- `tests/integration/test_grafana_config.py`
  - assert the new panels exist
  - assert they use `bioetl_records_processed_total`
  - assert `stage="filtered_out"` appears in the relevant panel queries
- `tests/integration/test_prometheus_rules_config.py`
  - update only if dashboard/rule expectations or referenced metrics change

## Acceptance criteria

- `bioetl-overview-v2.json` contains an explicit Silver filter rejects panel.
- `bioetl-dq-v2.json` contains an explicit Silver filter rejects panel, separate
  from DQ quarantine.
- `bioetl-runtime.json` contains a recent Silver filter reject signal.
- Dashboard tests pass.
- Metric names stay valid under the current Grafana config tests.
