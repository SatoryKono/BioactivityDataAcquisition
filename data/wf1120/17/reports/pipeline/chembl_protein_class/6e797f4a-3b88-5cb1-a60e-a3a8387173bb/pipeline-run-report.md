# Pipeline run report: chembl_protein_class

- **run_id:** `6e797f4a-3b88-5cb1-a60e-a3a8387173bb`
- **status:** failed
- **run_type:** backfill
- **tracking:** full
- **catalog:** reason_catalog_v1
- **manifest_id:** `48042bb7-aa87-5ac3-8258-8b78d3d33dcc`
- **provider/entity:** chembl / protein_class
- **started_at:** 2026-11-20T09:22:37.261435+00:00
- **completed_at:** 2026-11-20T09:23:40.400691+00:00
- **duration_seconds:** 63.139256
- **workflow:** `chembl_target_protein_classification` / `e7d65d91-dbbf-5b05-a5b4-f972fd1fd589` / `run_chembl_protein_class`

## Funnel

| Stage | In | Out | Removed | Balance | Tracking | Top reasons |
|-------|---:|----:|--------:|---------|----------|-------------|
| extract | 500 | 500 | 0 | OK | full | — |
| bronze | 500 | 500 | 0 | OK | full | — |
| silver | 500 | 499 | 1 | OK | full | FILTERED_OUT_SILVER:protein_class_id=1 |
| gold | 499 | 499 | 0 | OK | full | — |

## Layers

- bronze: **500**
- silver valid: **499** (filtered=1, quarantined=0, skipped=0, dedup=0)
- gold written: **499** (excluded=0, quarantined=0, skipped=0, dedup=0)

## Top reasons

- `FILTERED_OUT_SILVER:protein_class_id` (filtered_out): 1

## Failure

- **error_type:** `ExternalServiceError`
- **error_message:** `[Errno 11001] getaddrinfo failed`
- **failed_stage:** `None`
- **exit_hint:** `Investigate ExternalServiceError; check quarantine and gold contract exclusions.`

## IO

- **pipeline_name:** `chembl_protein_class`
- **run_type:** `backfill`
- **limit:** `1000`
- **skip_gold:** `False`
- **dry_run:** `False`
- **use_cached_bronze:** `False`

## DQ summary

- **records_filtered_out:** `1`
- **records_quarantined:** `0`
- **reasons:**

## Schema versions

- **reason_catalog_version:** `reason_catalog_v1`
- **bioetl_version:** `6.1.0`

## Performance

- **duration_seconds:** `63.139256`
- **records_per_second:** `7.919`

## Artifacts

- `pipeline_run_report_json`: `D:/github/BioactivityDataAcquisition/data/wf1120/17/reports/pipeline/chembl_protein_class/6e797f4a-3b88-5cb1-a60e-a3a8387173bb/pipeline-run-report.json`
- `pipeline_run_report_md`: `D:/github/BioactivityDataAcquisition/data/wf1120/17/reports/pipeline/chembl_protein_class/6e797f4a-3b88-5cb1-a60e-a3a8387173bb/pipeline-run-report.md`

## Reconciliation

- silver vs bronze: **OK** (delta=0)
- gold vs silver: **OK** (delta=0)
