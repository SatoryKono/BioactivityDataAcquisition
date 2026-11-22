# Pipeline run report: chembl_protein_class

- **run_id:** `0151d488-d942-51ba-8f06-d9dfe652382f`
- **status:** success
- **run_type:** backfill
- **tracking:** full
- **catalog:** reason_catalog_v1
- **manifest_id:** `99d5e6b7-5c27-591e-948b-5cbc54b88e4c`
- **provider/entity:** chembl / protein_class
- **started_at:** 2026-11-20T09:03:30.195296+00:00
- **completed_at:** 2026-11-20T09:04:15.781551+00:00
- **duration_seconds:** 45.586255
- **workflow:** `chembl_protein_class` / `a573be01-a6ab-5b86-9d72-46b9f0b13889` / `run_chembl_protein_class`

## Funnel

| Stage | In | Out | Removed | Balance | Tracking | Top reasons |
|-------|---:|----:|--------:|---------|----------|-------------|
| extract | 905 | 905 | 0 | OK | full | — |
| bronze | 905 | 905 | 0 | OK | full | — |
| silver | 905 | 904 | 1 | OK | full | FILTERED_OUT_SILVER:protein_class_id=1 |
| gold | 904 | 904 | 0 | OK | full | — |

## Layers

- bronze: **905**
- silver valid: **904** (filtered=1, quarantined=0, skipped=0, dedup=0)
- gold written: **904** (excluded=0, quarantined=0, skipped=0, dedup=0)

## Top reasons

- `FILTERED_OUT_SILVER:protein_class_id` (filtered_out): 1

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

- **duration_seconds:** `45.586255`
- **records_per_second:** `19.8525`

## Artifacts

- `pipeline_run_report_json`: `D:/github/BioactivityDataAcquisition/data/wf1120/10/reports/pipeline/chembl_protein_class/0151d488-d942-51ba-8f06-d9dfe652382f/pipeline-run-report.json`
- `pipeline_run_report_md`: `D:/github/BioactivityDataAcquisition/data/wf1120/10/reports/pipeline/chembl_protein_class/0151d488-d942-51ba-8f06-d9dfe652382f/pipeline-run-report.md`

## Reconciliation

- silver vs bronze: **OK** (delta=0)
- gold vs silver: **OK** (delta=0)
