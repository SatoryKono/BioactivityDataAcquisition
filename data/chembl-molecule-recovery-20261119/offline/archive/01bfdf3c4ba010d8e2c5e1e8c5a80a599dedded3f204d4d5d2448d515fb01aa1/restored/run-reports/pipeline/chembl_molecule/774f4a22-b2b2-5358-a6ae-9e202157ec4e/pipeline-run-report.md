# Pipeline run report: chembl_molecule

- **run_id:** `774f4a22-b2b2-5358-a6ae-9e202157ec4e`
- **status:** success
- **run_type:** backfill
- **tracking:** full
- **catalog:** reason_catalog_v1
- **manifest_id:** `e685a593-9b79-5fb9-aeb5-d99f59841a29`
- **provider/entity:** chembl / molecule
- **started_at:** 2026-11-19T19:54:02.365261+00:00
- **completed_at:** 2026-11-19T19:54:08.491637+00:00
- **duration_seconds:** 6.126376

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

- **pipeline_name:** `chembl_molecule`
- **run_type:** `backfill`
- **limit:** `1000`
- **skip_gold:** `False`
- **dry_run:** `False`
- **use_cached_bronze:** `True`
- **cached_bronze_path:** `D:/github/BioactivityDataAcquisition/data/workflows-limit1000-20261118T042057Z/chembl_molecule/output/bronze/chembl/molecule`

## Schema versions

- **reason_catalog_version:** `reason_catalog_v1`
- **bioetl_version:** `6.1.0`

## Performance

- **duration_seconds:** `6.126376`
- **records_per_second:** `163.2286`

## Artifacts

- `bronze_batch`: `D:/github/BioactivityDataAcquisition/data/workflows-limit1000-20261118T042057Z/chembl_molecule/output/bronze/chembl/molecule/2026-11-18/batch_2026-11-18_64dfb0f8-ee12-557b-a3cf-ec181f7ccbbe.jsonl.zst`
- `pipeline_run_report_json`: `D:/github/BioactivityDataAcquisition/data/chembl-molecule-recovery-20261119/offline/reports/pipeline/chembl_molecule/774f4a22-b2b2-5358-a6ae-9e202157ec4e/pipeline-run-report.json`
- `pipeline_run_report_md`: `D:/github/BioactivityDataAcquisition/data/chembl-molecule-recovery-20261119/offline/reports/pipeline/chembl_molecule/774f4a22-b2b2-5358-a6ae-9e202157ec4e/pipeline-run-report.md`

## Reconciliation

- silver vs bronze: **OK** (delta=0)
- gold vs silver: **OK** (delta=0)
