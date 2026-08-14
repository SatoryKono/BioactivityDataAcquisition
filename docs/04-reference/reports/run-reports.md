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
List responses also expose the backward-compatible `report_root`, `marker`, and
`marker_status` fields plus bounded `source_identity*` diagnostics. The layout
marker and source identity are independent, so operators can distinguish “no
runs yet”, “invalid reports tree”, and “valid tree from another checkout”.

## Report root and Docker bind

| Concept | Path / env |
|---------|------------|
| Run-reports root (writers + Ops HTTP) | `reports/run-reports` (default) or `BIOETL_REPORT_ROOT` |
| Dashboard bind mount (Compose) | host `BIOETL_DASHBOARD_REPORT_ROOT` → container `/app/reports` |
| Layout marker (tracked) | `reports/.bioetl-report-root` (token `bioetl-report-root-v1`) |
| Source attestation (machine-local, ignored) | `reports/.bioetl-report-source.json` (`bioetl-report-source-v1`) |
| Fail-closed readiness | `BIOETL_ENFORCE_REPORT_ROOT_MARKER=1` (default in `docker-compose.yml`) |

Inside the main `bioetl` container the effective root is
`/app/reports/run-reports`. Host CLI runs and container Ops HTTP **must** see
the same tree. Stale Docker Desktop bind caches that mount an empty path make
Grafana **Inspect Recent Runs** show empty while host `bioetl report list`
still finds artifacts.

Verify:

```bash
python scripts/ops/runtime/docker/verify_report_bind.py --pipeline chembl_assay
curl -s http://127.0.0.1:8000/health/ready | jq .checks.report_root
```

### Preventing empty Inspect Recent Runs (bind mismatch)

Root cause class: Docker Desktop binds `./reports` from a **stale project working_dir**
(virtual Docker Desktop WSL bind-mount paths) so Ops HTTP sees an empty
`/app/reports` while host CLI writers fill the real checkout tree.

Guards (fail-closed):

1. `runtime_manager` injects **absolute** compose-safe `BIOETL_DASHBOARD_*` paths
   (`E:/repo/reports`, not relative `./reports` and not backslash paths).
2. Before main `start`/`recover`, the manager atomically writes the versioned
   source attestation. Its digest binds the selected repository root and the
   contracted `data/` + `reports/` mount roots to `BIOETL_RUNTIME_SOURCE_ID`.
   The canonical resolver in
   `src/bioetl/application/services/run_reports/source_identity.py` uses this
   precedence: computed runtime root, process environment, repository env
   loader, container environment, then container label. A present invalid
   higher-precedence value and any lower-precedence disagreement fail closed.
3. `/health/ready` requires both `layout_status=healthy` and
   `source_identity_status=healthy` when enforcement is enabled. A valid static
   marker from another checkout therefore cannot make readiness healthy.
4. Main stack `up` uses `--force-recreate` so old empty binds cannot stick.
5. After successful readiness, `runtime_manager start --stack main` runs
   `verify_report_bind.py`. The verifier compares the normalized bind path,
   container label, host attestation, Ops readiness/list identities, and newest
   run ID; any mismatch fails the lifecycle action even when counts are equal or
   both trees are empty.
6. Operator re-check: `python scripts/ops/runtime/docker/verify_report_bind.py`.
7. After application code changes that touch Ops HTTP / `report_root` readiness,
   refresh the image source tree (full `docker compose build bioetl` or a
   src-overlay rebuild) so `/health/ready` exposes `checks.report_root`.
   Host-side verify **must not** export container path
   `BIOETL_REPORT_ROOT=/app/reports/run-reports` into the shell — that path is
   for the container only; on Windows it becomes a bogus `E:\app\...` root.

If verification fails, recreate the main stack from the canonical checkout
(not a transient Docker Desktop hash bind path):

```bash
python scripts/ops/runtime/docker/runtime_manager.py start --stack main --timeout 180
```

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
