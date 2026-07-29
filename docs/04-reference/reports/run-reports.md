# Pipeline and workflow run reports

Program: `run-reports-v1` (issues #6519–#6526) with extension program
`run-reports-v1.1` (epic #6528, RR-ext-01…06).

## Contracts

| Schema | Path |
|--------|------|
| `pipeline_run_report_v1` | `configs/contracts/reports/pipeline_run_report.v1.json` |
| `workflow_run_report_v1` | `configs/contracts/reports/workflow_run_report.v1.json` |
| Reason catalog | `configs/contracts/reports/reason_catalog.v1.yaml` |

Golden examples: `tests/fixtures/reports/*_golden.json`.

Optional additive blocks on pipeline reports (omit when unknown; never invent zeros):

- `failure`, `io`, `quarantine`, `dq_summary`, `contract_summary`
- `schema_versions`, `stage_timings`, `http_summary`, `performance`
- `artifacts[]` (includes self-refs to JSON/MD after write)

Optional on workflow reports:

- execution `top_reasons`, `skip_reason`, `pipeline_report_ref`
- top-level `reasons_rollup`

## Operator questions

### Pipeline report

- How many records were **obtained** (extract / bronze in)?
- How many were **removed** at each stage (`records_in`, `records_out`, `removed_total`)?
- **Why** (stable `reason_code` + `outcome` buckets)?
- Is accounting **balanced** (`balance_status`, reconciliation)?
- Which artifacts to open next (`artifacts`, quarantine, debug export)?
- When did it run / how long (`started_at`, `duration_seconds`)?

### Workflow report

- Which pipelines/steps were planned and executed?
- How many records were **extracted** per step (`records_extracted`)?
- Workflow total extracted / silver / gold?
- Child pipeline report paths and top removal reasons?

## Artifact layout

```text
reports/run-reports/
  pipeline/<pipeline_name>/
    _latest.json
    <run_id>/
      pipeline-run-report.json
      pipeline-run-report.md
  workflow/<workflow_name>/
    _latest.json
    <workflow_run_id>/
      workflow-run-report.json
      workflow-run-report.md
```

## Source of truth

1. **Stage accounting** records losses at drop-path time (ContextVar-bound accumulator).
2. Report builders **project** accounting + coarse `RunResult` metrics.
3. Funnel geometry prefers **layer-aligned** in/out when bucket counters break conservation
   (e.g. gold batch over-count) while removal reason maps remain from accounting.
4. Prometheus / Processed Records remain **live** surfaces, not post-run SoT.

## Hook inventory (high-volume)

| Path | File | Outcome / reason |
|------|------|------------------|
| Records fetched | `application/core/batch_metrics.py` `track_records_fetched` | extract in |
| Bronze/silver/gold processed | `batch_metrics.py` `track_processed_records` | stage out / silver removals |
| Filter rejects | `batch_metrics.py` `track_silver_filter_rejection` | `filtered_out` + reason_code |
| Filter aggregate | `application/core/_quarantine_metrics_support.py` `record_filtered_quarantine_metrics` | `FILTERED_OUT_SILVER` |
| Quarantine | `batch_metrics.py` `track_quarantined_records` | `quarantined` + ErrorType |
| Gold excludes (metric backfill) | `execution/_pipeline_runner_support.py` `_seed_gold_removals_from_metrics` | `excluded_by_contract` |
| Pipeline report write | `execution/_pipeline_runner_support.py` `finalize_pipeline_run_report` | JSON+MD+`_latest` |
| Workflow report write | `workflow_runner_reports.py` `attach_workflow_run_report` | JSON+MD+`_latest` |

## CLI

```bash
bioetl report show --pipeline chembl_assay --latest
bioetl report show --pipeline chembl_assay --run-id <run_id>
bioetl report show --workflow activity_workflow --latest
bioetl report list --pipeline chembl_assay --limit 10
bioetl report diff --pipeline chembl_assay --run-id-a A --run-id-b B
bioetl report prune --kind pipeline --owner chembl_assay --max-count 50   # dry-run
bioetl report prune --kind pipeline --owner chembl_assay --max-count 50 --apply
```

## HTTP ops (optional)

- `GET /ops/observability/pipeline-run-report?run_id=…&pipeline=…`
- `GET /ops/observability/workflow-run-report?workflow_run_id=…&workflow=…`
- `GET /ops/observability/pipeline-run-reports?pipeline=…&limit=20`
- `GET /ops/observability/workflow-run-reports?workflow=…&limit=20`

Missing artifact → structured 404 (`status=not_found`), not invented zeros.
An empty list is a successful artifact-index response
(`status=ok`, `count=0`, `items=[]`); it is distinct from the bounded forensic
endpoint timeout response (`504`, `contract=forensic_endpoint_error_v1`).

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

## Retention

Working tree under `reports/run-reports/` is non-normative operator evidence.
Use `bioetl report prune` with explicit `--max-count` / `--max-age-days` (dry-run
by default; `--apply` required to delete).

## Related agent memory

- Curated lesson: `src/memory/curated/lessons/run-reports-and-governance-hash-refresh.md`
- Project memory entry: `docs/00-project/ai/memory/agent-memory.md` (Run reports + governance closeouts)
- After `src/bioetl/**` changes, refresh inventory / topology SUMMARY / debt gates /
  evidence_surface_sha256 (and test-telemetry hash if tests changed) before
  architecture closeout.
