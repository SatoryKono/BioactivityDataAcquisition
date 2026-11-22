# Pipeline run report: chembl_target_component

- **run_id:** `288ccab7-aa13-5205-a1db-c23ed79a6e22`
- **status:** failed
- **run_type:** backfill
- **tracking:** partial
- **catalog:** reason_catalog_v1
- **manifest_id:** `ac10a78c-5f6c-5cd9-9578-8c28ddcc4e70`
- **provider/entity:** chembl / target_component
- **started_at:** 2026-11-20T09:21:58.891343+00:00
- **completed_at:** 2026-11-20T09:22:24.656372+00:00
- **duration_seconds:** 25.765029
- **workflow:** `chembl_target_component` / `b7f5cdc1-8f9d-542f-b750-4c9219119980` / `run_chembl_target_component`

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

- **error_type:** `ExternalServiceError`
- **error_message:** `[Errno 11001] getaddrinfo failed`
- **failed_stage:** `None`
- **exit_hint:** `Investigate ExternalServiceError; check quarantine and gold contract exclusions.`

## IO

- **pipeline_name:** `chembl_target_component`
- **run_type:** `backfill`
- **limit:** `1000`
- **skip_gold:** `False`
- **dry_run:** `False`
- **use_cached_bronze:** `False`

## Schema versions

- **reason_catalog_version:** `reason_catalog_v1`
- **bioetl_version:** `6.1.0`

## Performance

- **duration_seconds:** `25.765029`
- **records_per_second:** `None`

## Artifacts

- `pipeline_run_report_json`: `D:/github/BioactivityDataAcquisition/data/wf1120/16/reports/pipeline/chembl_target_component/288ccab7-aa13-5205-a1db-c23ed79a6e22/pipeline-run-report.json`
- `pipeline_run_report_md`: `D:/github/BioactivityDataAcquisition/data/wf1120/16/reports/pipeline/chembl_target_component/288ccab7-aa13-5205-a1db-c23ed79a6e22/pipeline-run-report.md`

## Reconciliation

- silver vs bronze: **OK** (delta=0)
- gold vs silver: **OK** (delta=0)
