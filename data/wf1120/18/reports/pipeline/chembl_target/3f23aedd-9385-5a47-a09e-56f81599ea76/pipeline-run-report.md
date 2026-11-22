# Pipeline run report: chembl_target

- **run_id:** `3f23aedd-9385-5a47-a09e-56f81599ea76`
- **status:** failed
- **run_type:** backfill
- **tracking:** partial
- **catalog:** reason_catalog_v1
- **manifest_id:** `0b6d9402-ccd2-5835-97c3-176afdbd5d15`
- **provider/entity:** chembl / target
- **started_at:** 2026-11-20T09:26:17.189004+00:00
- **completed_at:** 2026-11-20T09:27:48.137377+00:00
- **duration_seconds:** 90.948373
- **workflow:** `chembl_target` / `79cebb92-2394-5c52-8b72-2ebb11252631` / `run_chembl_target`

## Funnel

| Stage | In | Out | Removed | Balance | Tracking | Top reasons |
|-------|---:|----:|--------:|---------|----------|-------------|
| extract | 0 | 0 | 0 | OK | partial | — |
| bronze | 0 | 0 | 0 | OK | partial | — |
| silver | 0 | 0 | 0 | OK | partial | — |
| gold | 0 | 0 | 0 | OK | partial | — |

## Layers

- bronze: **0**
- silver valid: **0** (filtered=0, quarantined=0, skipped=0, dedup=0)
- gold written: **0** (excluded=0, quarantined=0, skipped=0, dedup=0)

## Top reasons

- (none)

## Failure

- **error_type:** `ServiceUnavailableError`
- **error_message:** `Circuit breaker open for chembl. Retry after 2998.495377399988s`
- **failed_stage:** `None`
- **exit_hint:** `Investigate ServiceUnavailableError; check quarantine and gold contract exclusions.`

## IO

- **pipeline_name:** `chembl_target`
- **run_type:** `backfill`
- **limit:** `1000`
- **skip_gold:** `False`
- **dry_run:** `False`
- **use_cached_bronze:** `False`

## Schema versions

- **reason_catalog_version:** `reason_catalog_v1`
- **bioetl_version:** `6.1.0`

## Performance

- **duration_seconds:** `90.948373`
- **records_per_second:** `None`

## Artifacts

- `pipeline_run_report_json`: `D:/github/BioactivityDataAcquisition/data/wf1120/18/reports/pipeline/chembl_target/3f23aedd-9385-5a47-a09e-56f81599ea76/pipeline-run-report.json`
- `pipeline_run_report_md`: `D:/github/BioactivityDataAcquisition/data/wf1120/18/reports/pipeline/chembl_target/3f23aedd-9385-5a47-a09e-56f81599ea76/pipeline-run-report.md`

## Reconciliation

- silver vs bronze: **OK** (delta=0)
- gold vs silver: **OK** (delta=0)
