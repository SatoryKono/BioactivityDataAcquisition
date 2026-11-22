# Pipeline run report: chembl_assay_parameters

- **run_id:** `49e3e40f-ad71-5c3c-b25c-15e8204f74ad`
- **status:** success
- **run_type:** backfill
- **tracking:** full
- **catalog:** reason_catalog_v1
- **manifest_id:** `98b24715-5e1b-5800-be87-06b818977cc9`
- **provider/entity:** chembl / assay_parameters
- **started_at:** 2026-11-20T08:48:57.677376+00:00
- **completed_at:** 2026-11-20T08:52:23.483323+00:00
- **duration_seconds:** 205.805947
- **workflow:** `chembl_assay_parameters` / `bee6e25d-6a00-50ec-a4aa-32f2933cb4dc` / `run_chembl_assay_parameters`

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

- **pipeline_name:** `chembl_assay_parameters`
- **run_type:** `backfill`
- **limit:** `1000`
- **skip_gold:** `False`
- **dry_run:** `False`
- **use_cached_bronze:** `False`

## Schema versions

- **reason_catalog_version:** `reason_catalog_v1`
- **bioetl_version:** `6.1.0`

## Performance

- **duration_seconds:** `205.805947`
- **records_per_second:** `4.8589`

## Artifacts

- `pipeline_run_report_json`: `D:/github/BioactivityDataAcquisition/data/wf1120/04/reports/pipeline/chembl_assay_parameters/49e3e40f-ad71-5c3c-b25c-15e8204f74ad/pipeline-run-report.json`
- `pipeline_run_report_md`: `D:/github/BioactivityDataAcquisition/data/wf1120/04/reports/pipeline/chembl_assay_parameters/49e3e40f-ad71-5c3c-b25c-15e8204f74ad/pipeline-run-report.md`

## Reconciliation

- silver vs bronze: **OK** (delta=0)
- gold vs silver: **OK** (delta=0)
