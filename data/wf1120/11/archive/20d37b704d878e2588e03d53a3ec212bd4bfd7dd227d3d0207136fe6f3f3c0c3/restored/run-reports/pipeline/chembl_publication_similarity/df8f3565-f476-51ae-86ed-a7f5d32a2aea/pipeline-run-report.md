# Pipeline run report: chembl_publication_similarity

- **run_id:** `df8f3565-f476-51ae-86ed-a7f5d32a2aea`
- **status:** success
- **run_type:** backfill
- **tracking:** full
- **catalog:** reason_catalog_v1
- **manifest_id:** `329e0aeb-5416-5c47-9506-b9fe04dabc2c`
- **provider/entity:** chembl / publication_similarity
- **started_at:** 2026-11-20T09:04:29.802044+00:00
- **completed_at:** 2026-11-20T09:06:19.942345+00:00
- **duration_seconds:** 110.140301
- **workflow:** `chembl_publication_similarity` / `bc4ead33-d7b1-5ab1-a7ad-c9d26c891b1d` / `run_chembl_publication_similarity`

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

- **pipeline_name:** `chembl_publication_similarity`
- **run_type:** `backfill`
- **limit:** `1000`
- **skip_gold:** `False`
- **dry_run:** `False`
- **use_cached_bronze:** `False`

## Schema versions

- **reason_catalog_version:** `reason_catalog_v1`
- **bioetl_version:** `6.1.0`

## Performance

- **duration_seconds:** `110.140301`
- **records_per_second:** `9.0793`

## Artifacts

- `pipeline_run_report_json`: `D:/github/BioactivityDataAcquisition/data/wf1120/11/reports/pipeline/chembl_publication_similarity/df8f3565-f476-51ae-86ed-a7f5d32a2aea/pipeline-run-report.json`
- `pipeline_run_report_md`: `D:/github/BioactivityDataAcquisition/data/wf1120/11/reports/pipeline/chembl_publication_similarity/df8f3565-f476-51ae-86ed-a7f5d32a2aea/pipeline-run-report.md`

## Reconciliation

- silver vs bronze: **OK** (delta=0)
- gold vs silver: **OK** (delta=0)
