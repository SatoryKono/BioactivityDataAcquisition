# Pipeline run report: chembl_publication

- **run_id:** `73e55611-b579-5982-ba78-14a91b6965fa`
- **status:** success
- **run_type:** backfill
- **tracking:** full
- **catalog:** reason_catalog_v1
- **manifest_id:** `e5d93b37-3f9c-5899-95ad-b36e443e9885`
- **provider/entity:** chembl / publication
- **started_at:** 2026-11-11T18:16:12.848125+00:00
- **completed_at:** 2026-11-11T18:17:12.033776+00:00
- **duration_seconds:** 59.185651
- **workflow:** `chembl_baseline` / `30b43f27-5d21-56de-8289-a6c62181d6da` / `run_chembl_publication`

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

- **duration_seconds:** `59.185651`
- **records_per_second:** `16.896`

## Artifacts

- `pipeline_run_report_json`: `D:/github/BioactivityDataAcquisition/data/workflow-reconciliation/repair-20261111/chembl_baseline/reports/run-reports/pipeline/chembl_publication/73e55611-b579-5982-ba78-14a91b6965fa/pipeline-run-report.json`
- `pipeline_run_report_md`: `D:/github/BioactivityDataAcquisition/data/workflow-reconciliation/repair-20261111/chembl_baseline/reports/run-reports/pipeline/chembl_publication/73e55611-b579-5982-ba78-14a91b6965fa/pipeline-run-report.md`

## Reconciliation

- silver vs bronze: **OK** (delta=0)
- gold vs silver: **OK** (delta=0)
