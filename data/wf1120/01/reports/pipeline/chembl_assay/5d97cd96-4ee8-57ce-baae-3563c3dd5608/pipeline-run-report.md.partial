# Pipeline run report: chembl_assay

- **run_id:** `5d97cd96-4ee8-57ce-baae-3563c3dd5608`
- **status:** failed
- **run_type:** backfill
- **tracking:** partial
- **catalog:** reason_catalog_v1
- **manifest_id:** `6a0c8eac-5f85-5978-be64-65c0b0644518`
- **provider/entity:** chembl / assay
- **started_at:** 2026-11-20T08:44:26.539440+00:00
- **completed_at:** 2026-11-20T08:45:05.220382+00:00
- **duration_seconds:** 38.680942
- **workflow:** `chembl_assay` / `f8c603ea-21ae-58fa-a984-bfcaee19f8e8` / `run_chembl_assay`

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
- **error_message:** `Circuit breaker open for chembl. Retry after 2990.1472589999903s`
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

- **duration_seconds:** `38.680942`
- **records_per_second:** `None`

## Artifacts

- `pipeline_run_report_json`: `D:/github/BioactivityDataAcquisition/data/wf1120/01/reports/pipeline/chembl_assay/5d97cd96-4ee8-57ce-baae-3563c3dd5608/pipeline-run-report.json`
- `pipeline_run_report_md`: `D:/github/BioactivityDataAcquisition/data/wf1120/01/reports/pipeline/chembl_assay/5d97cd96-4ee8-57ce-baae-3563c3dd5608/pipeline-run-report.md`

## Reconciliation

- silver vs bronze: **OK** (delta=0)
- gold vs silver: **OK** (delta=0)
