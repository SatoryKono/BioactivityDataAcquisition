# Pipeline run report: chembl_publication

- **run_id:** `7e3cd3fe-8459-5351-a9f6-b2979d54cd15`
- **status:** success
- **run_type:** backfill
- **tracking:** full
- **catalog:** reason_catalog_v1
- **manifest_id:** `10177757-a553-53ba-b22b-211309e8d253`
- **provider/entity:** chembl / publication
- **started_at:** 2026-11-11T18:09:16.497532+00:00
- **completed_at:** 2026-11-11T18:10:18.488603+00:00
- **duration_seconds:** 61.991071
- **workflow:** `chembl_baseline` / `cbbad724-4f10-58bc-8044-fc627377c052` / `run_chembl_publication`

## Funnel

| Stage | In | Out | Removed | Balance | Tracking | Top reasons |
|-------|---:|----:|--------:|---------|----------|-------------|
| extract | 1000 | 1000 | 0 | OK | full | — |
| bronze | 1000 | 1000 | 0 | OK | full | — |
| silver | 1000 | 1000 | 0 | OK | full | — |
| gold | 1000 | 1000 | 0 | OK | full | — |

## Layers

- bronze: **1000**
- silver valid: **1000** (filtered=0, quarantined=0, skipped=0, dedup=0)
- gold written: **1000** (excluded=0, quarantined=0, skipped=0, dedup=0)

## Top reasons

- (none)

## IO

- **pipeline_name:** `chembl_publication`
- **run_type:** `backfill`
- **limit:** `1000`
- **filter_column:** `publication_id`
- **skip_gold:** `False`
- **dry_run:** `False`
- **use_cached_bronze:** `True`
- **filter_id_count:** `191`
- **filter_id_hash:** `26573bda865b2f4c`

## Schema versions

- **reason_catalog_version:** `reason_catalog_v1`
- **bioetl_version:** `6.1.0`

## Performance

- **duration_seconds:** `61.991071`
- **records_per_second:** `16.1314`

## Artifacts

- `pipeline_run_report_json`: `D:/github/BioactivityDataAcquisition/data/workflow-reconciliation/repair-20261111/chembl_baseline/reports/run-reports/pipeline/chembl_publication/7e3cd3fe-8459-5351-a9f6-b2979d54cd15/pipeline-run-report.json`
- `pipeline_run_report_md`: `D:/github/BioactivityDataAcquisition/data/workflow-reconciliation/repair-20261111/chembl_baseline/reports/run-reports/pipeline/chembl_publication/7e3cd3fe-8459-5351-a9f6-b2979d54cd15/pipeline-run-report.md`

## Reconciliation

- silver vs bronze: **OK** (delta=0)
- gold vs silver: **OK** (delta=0)
