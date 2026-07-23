# Pipeline and workflow run reports

Program: `run-reports-v1` (issues #6519–#6526).

## Contracts

| Schema | Path |
|--------|------|
| `pipeline_run_report_v1` | `configs/contracts/reports/pipeline_run_report.v1.json` |
| `workflow_run_report_v1` | `configs/contracts/reports/workflow_run_report.v1.json` |
| Reason catalog | `configs/contracts/reports/reason_catalog.v1.yaml` |

Golden examples: `tests/fixtures/reports/*_golden.json`.

## Operator questions

### Pipeline report

- How many records were **obtained** (extract / bronze in)?
- How many were **removed** at each stage (`records_in`, `records_out`, `removed_total`)?
- **Why** (stable `reason_code` + `outcome` buckets)?
- Is accounting **balanced** (`balance_status`, reconciliation)?

### Workflow report

- Which pipelines/steps were planned and executed?
- How many records were **extracted** per step (`records_extracted`)?
- Workflow total extracted?

## Artifact layout

```text
reports/run-reports/
  pipeline/<pipeline_name>/<run_id>/
    pipeline-run-report.json
    pipeline-run-report.md
  workflow/<workflow_name>/<workflow_run_id>/
    workflow-run-report.json
    workflow-run-report.md
```

## Source of truth

1. **Stage accounting** records losses at drop-path time (ContextVar-bound accumulator).
2. Report builders **project** accounting + coarse `RunResult` metrics.
3. Prometheus / Processed Records remain **live** surfaces, not post-run SoT.

## Hook inventory (high-volume)

| Path | File | Outcome / reason |
|------|------|------------------|
| Records fetched | `application/core/batch_metrics.py` `track_records_fetched` | extract in |
| Bronze/silver/gold processed | `batch_metrics.py` `track_processed_records` | stage out / silver removals |
| Filter rejects | `batch_metrics.py` `track_silver_filter_rejection` | `filtered_out` + reason_code |
| Filter aggregate | `application/core/_quarantine_metrics_support.py` `record_filtered_quarantine_metrics` | `FILTERED_OUT_SILVER` |
| Quarantine | `batch_metrics.py` `track_quarantined_records` | `quarantined` + ErrorType |
| Gold excludes (metric backfill) | `execution/_pipeline_runner_support.py` `_seed_gold_removals_from_metrics` | `excluded_by_contract` |
| Pipeline report write | `execution/_pipeline_runner_support.py` `finalize_pipeline_run_report` | JSON+MD |
| Workflow report write | `workflow_runner_service.py` `_attach_workflow_run_report` | JSON+MD |

## HTTP ops (optional)

- `GET /ops/observability/pipeline-run-report?run_id=…&pipeline=…`
- `GET /ops/observability/workflow-run-report?workflow_run_id=…&workflow=…`

Missing artifact → structured 404 (`status=not_found`), not invented zeros.

## Conservation

For each stage:

```text
records_in = records_out + sum(removals[*].count) + unaccounted
```

- `unaccounted == 0` → `balance_status=OK`
- partial instrumentation with gap → `DEGRADED`
- severe imbalance → `FAILING`

## Tracking coverage

- `full` — stage instrumented with reason maps
- `partial` — coarse metrics / incomplete hooks
- `not_tracked` — no accounting for stage

## Related agent memory

- Curated lesson: `src/memory/curated/lessons/run-reports-and-governance-hash-refresh.md`
- Project memory entry: `docs/00-project/ai/memory/agent-memory.md` (Run reports + governance closeouts)
- After `src/bioetl/**` changes, refresh inventory / topology SUMMARY / debt gates /
  evidence_surface_sha256 (and test-telemetry hash if tests changed) before
  architecture closeout.
