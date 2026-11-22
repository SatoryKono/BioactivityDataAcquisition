# Pipeline run report: chembl_target

- **run_id:** `d63e7efe-e60e-5616-b44d-bc401b17150c`
- **status:** failed
- **run_type:** backfill
- **tracking:** partial
- **catalog:** reason_catalog_v1
- **manifest_id:** `c1071ef9-2b10-52f4-9343-579cb47358c9`
- **provider/entity:** chembl / target
- **started_at:** 2026-11-20T08:59:58.873771+00:00
- **completed_at:** 2026-11-20T09:02:08.127184+00:00
- **duration_seconds:** 129.253413
- **workflow:** `chembl_core` / `5be49576-4861-5377-ab81-6f2ee6db429e` / `chembl_target_ingest`

## Funnel

| Stage | In | Out | Removed | Balance | Tracking | Top reasons |
|-------|---:|----:|--------:|---------|----------|-------------|
| extract | 20 | 20 | 0 | OK | partial | — |
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
- **error_message:** `Circuit breaker open for chembl. Retry after 2994.1759802000015s`
- **failed_stage:** `None`
- **exit_hint:** `Investigate ServiceUnavailableError; check quarantine and gold contract exclusions.`

## IO

- **pipeline_name:** `chembl_target`
- **run_type:** `backfill`
- **limit:** `1000`
- **filter_column:** `target_id`
- **skip_gold:** `False`
- **dry_run:** `False`
- **use_cached_bronze:** `False`
- **filter_id_count:** `73`
- **filter_id_hash:** `0089e2d9ce8844bd`

## Schema versions

- **reason_catalog_version:** `reason_catalog_v1`
- **bioetl_version:** `6.1.0`

## Performance

- **duration_seconds:** `129.253413`
- **records_per_second:** `0.1547`

## Artifacts

- `pipeline_run_report_json`: `D:/github/BioactivityDataAcquisition/data/wf1120/08/reports/pipeline/chembl_target/d63e7efe-e60e-5616-b44d-bc401b17150c/pipeline-run-report.json`
- `pipeline_run_report_md`: `D:/github/BioactivityDataAcquisition/data/wf1120/08/reports/pipeline/chembl_target/d63e7efe-e60e-5616-b44d-bc401b17150c/pipeline-run-report.md`

## Reconciliation

- silver vs bronze: **OK** (delta=0)
- gold vs silver: **OK** (delta=0)
