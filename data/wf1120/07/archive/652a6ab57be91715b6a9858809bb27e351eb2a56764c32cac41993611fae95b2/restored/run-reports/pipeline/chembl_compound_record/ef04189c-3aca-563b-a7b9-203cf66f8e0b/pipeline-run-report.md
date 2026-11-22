# Pipeline run report: chembl_compound_record

- **run_id:** `ef04189c-3aca-563b-a7b9-203cf66f8e0b`
- **status:** success
- **run_type:** backfill
- **tracking:** full
- **catalog:** reason_catalog_v1
- **manifest_id:** `a109014c-d9e3-5ffc-8e1d-9b020328e317`
- **provider/entity:** chembl / compound_record
- **started_at:** 2026-11-20T08:55:17.860398+00:00
- **completed_at:** 2026-11-20T08:57:33.541683+00:00
- **duration_seconds:** 135.681285
- **workflow:** `chembl_compound_record` / `46a3891a-ece5-5a84-9247-2b944c3a829d` / `run_chembl_compound_record`

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

- **pipeline_name:** `chembl_compound_record`
- **run_type:** `backfill`
- **limit:** `1000`
- **skip_gold:** `False`
- **dry_run:** `False`
- **use_cached_bronze:** `False`

## Schema versions

- **reason_catalog_version:** `reason_catalog_v1`
- **bioetl_version:** `6.1.0`

## Performance

- **duration_seconds:** `135.681285`
- **records_per_second:** `7.3702`

## Artifacts

- `pipeline_run_report_json`: `D:/github/BioactivityDataAcquisition/data/wf1120/07/reports/pipeline/chembl_compound_record/ef04189c-3aca-563b-a7b9-203cf66f8e0b/pipeline-run-report.json`
- `pipeline_run_report_md`: `D:/github/BioactivityDataAcquisition/data/wf1120/07/reports/pipeline/chembl_compound_record/ef04189c-3aca-563b-a7b9-203cf66f8e0b/pipeline-run-report.md`

## Reconciliation

- silver vs bronze: **OK** (delta=0)
- gold vs silver: **OK** (delta=0)
