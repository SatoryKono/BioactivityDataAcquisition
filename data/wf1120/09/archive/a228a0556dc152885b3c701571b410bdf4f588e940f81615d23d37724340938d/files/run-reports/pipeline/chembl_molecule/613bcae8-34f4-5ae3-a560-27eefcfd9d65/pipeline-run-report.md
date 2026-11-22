# Pipeline run report: chembl_molecule

- **run_id:** `613bcae8-34f4-5ae3-a560-27eefcfd9d65`
- **status:** success
- **run_type:** backfill
- **tracking:** full
- **catalog:** reason_catalog_v1
- **manifest_id:** `309f8758-6104-5b15-90ea-8b3ec9b38b06`
- **provider/entity:** chembl / molecule
- **started_at:** 2026-11-20T09:02:22.355799+00:00
- **completed_at:** 2026-11-20T09:03:17.755140+00:00
- **duration_seconds:** 55.399341
- **workflow:** `chembl_molecule` / `ba4e3fc2-3c82-5c65-98b7-26290c0a8ffb` / `run_chembl_molecule`

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
- **use_cached_bronze:** `False`

## Schema versions

- **reason_catalog_version:** `reason_catalog_v1`
- **bioetl_version:** `6.1.0`

## Performance

- **duration_seconds:** `55.399341`
- **records_per_second:** `18.0508`

## Artifacts

- `pipeline_run_report_json`: `D:/github/BioactivityDataAcquisition/data/wf1120/09/reports/pipeline/chembl_molecule/613bcae8-34f4-5ae3-a560-27eefcfd9d65/pipeline-run-report.json`
- `pipeline_run_report_md`: `D:/github/BioactivityDataAcquisition/data/wf1120/09/reports/pipeline/chembl_molecule/613bcae8-34f4-5ae3-a560-27eefcfd9d65/pipeline-run-report.md`

## Reconciliation

- silver vs bronze: **OK** (delta=0)
- gold vs silver: **OK** (delta=0)
