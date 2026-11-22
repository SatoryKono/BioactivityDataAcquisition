# Pipeline run report: chembl_tissue

- **run_id:** `b5159905-b580-5538-a482-f1d391df499f`
- **status:** failed
- **run_type:** backfill
- **tracking:** partial
- **catalog:** reason_catalog_v1
- **manifest_id:** `d8bafbd8-1d24-5208-98f0-3563a25f15b2`
- **provider/entity:** chembl / tissue
- **started_at:** 2026-11-20T09:19:57.200178+00:00
- **completed_at:** 2026-11-20T09:20:52.309590+00:00
- **duration_seconds:** 55.109412
- **workflow:** `chembl_reference_pack` / `6fb38224-594e-5802-aa72-7137e03a1eac` / `run_chembl_tissue`

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
- **error_message:** `Circuit breaker open for chembl. Retry after 2998.757514099998s`
- **failed_stage:** `None`
- **exit_hint:** `Investigate ServiceUnavailableError; check quarantine and gold contract exclusions.`

## IO

- **pipeline_name:** `chembl_tissue`
- **run_type:** `backfill`
- **limit:** `1000`
- **skip_gold:** `False`
- **dry_run:** `False`
- **use_cached_bronze:** `False`

## Schema versions

- **reason_catalog_version:** `reason_catalog_v1`
- **bioetl_version:** `6.1.0`

## Performance

- **duration_seconds:** `55.109412`
- **records_per_second:** `None`

## Artifacts

- `pipeline_run_report_json`: `D:/github/BioactivityDataAcquisition/data/wf1120/14/reports/pipeline/chembl_tissue/b5159905-b580-5538-a482-f1d391df499f/pipeline-run-report.json`
- `pipeline_run_report_md`: `D:/github/BioactivityDataAcquisition/data/wf1120/14/reports/pipeline/chembl_tissue/b5159905-b580-5538-a482-f1d391df499f/pipeline-run-report.md`

## Reconciliation

- silver vs bronze: **OK** (delta=0)
- gold vs silver: **OK** (delta=0)
