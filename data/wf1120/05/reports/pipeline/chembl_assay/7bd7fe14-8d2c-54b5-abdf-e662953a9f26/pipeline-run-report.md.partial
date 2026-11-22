# Pipeline run report: chembl_assay

- **run_id:** `7bd7fe14-8d2c-54b5-abdf-e662953a9f26`
- **status:** failed
- **run_type:** backfill
- **tracking:** partial
- **catalog:** reason_catalog_v1
- **manifest_id:** `4bd4e6bf-1cc6-530f-ad9d-cc5b70b25e6b`
- **provider/entity:** chembl / assay
- **started_at:** 2026-11-20T08:52:41.551800+00:00
- **completed_at:** 2026-11-20T08:54:20.525017+00:00
- **duration_seconds:** 98.973217
- **workflow:** `chembl_baseline` / `2b028c59-db6a-5ff3-afc4-6d17c60706b6` / `run_chembl_assay`

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
- **error_message:** `Circuit breaker open for chembl. Retry after 2998.7404711000127s`
- **failed_stage:** `None`
- **exit_hint:** `Investigate ServiceUnavailableError; check quarantine and gold contract exclusions.`

## IO

- **pipeline_name:** `chembl_assay`
- **run_type:** `backfill`
- **limit:** `1000`
- **skip_gold:** `False`
- **dry_run:** `False`
- **use_cached_bronze:** `False`

## Schema versions

- **reason_catalog_version:** `reason_catalog_v1`
- **bioetl_version:** `6.1.0`

## Performance

- **duration_seconds:** `98.973217`
- **records_per_second:** `None`

## Artifacts

- `pipeline_run_report_json`: `D:/github/BioactivityDataAcquisition/data/wf1120/05/reports/pipeline/chembl_assay/7bd7fe14-8d2c-54b5-abdf-e662953a9f26/pipeline-run-report.json`
- `pipeline_run_report_md`: `D:/github/BioactivityDataAcquisition/data/wf1120/05/reports/pipeline/chembl_assay/7bd7fe14-8d2c-54b5-abdf-e662953a9f26/pipeline-run-report.md`

## Reconciliation

- silver vs bronze: **OK** (delta=0)
- gold vs silver: **OK** (delta=0)
