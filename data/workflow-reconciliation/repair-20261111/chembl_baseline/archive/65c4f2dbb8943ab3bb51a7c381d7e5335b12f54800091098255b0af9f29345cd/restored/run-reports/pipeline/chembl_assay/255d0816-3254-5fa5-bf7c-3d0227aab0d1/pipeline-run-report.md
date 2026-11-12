# Pipeline run report: chembl_assay

- **run_id:** `255d0816-3254-5fa5-bf7c-3d0227aab0d1`
- **status:** success
- **run_type:** backfill
- **tracking:** full
- **catalog:** reason_catalog_v1
- **manifest_id:** `ad764b87-84e1-54ce-9475-40e9c9f4f1d8`
- **provider/entity:** chembl / assay
- **started_at:** 2026-11-11T18:14:33.437672+00:00
- **completed_at:** 2026-11-11T18:14:42.337404+00:00
- **duration_seconds:** 8.899732
- **workflow:** `chembl_baseline` / `30b43f27-5d21-56de-8289-a6c62181d6da` / `run_chembl_assay`

## Funnel

| Stage | In | Out | Removed | Balance | Tracking | Top reasons |
|-------|---:|----:|--------:|---------|----------|-------------|
| extract | 1000 | 1000 | 0 | OK | full | — |
| bronze | 1000 | 1000 | 0 | OK | full | — |
| silver | 1000 | 1000 | 0 | OK | full | — |
| gold | 1000 | 983 | 17 | OK | full | column_filter_mismatch:bao_format=15, column_filter_mismatch:assay_test_type=2 |

## Layers

- bronze: **1000**
- silver valid: **1000** (filtered=0, quarantined=0, skipped=0, dedup=0)
- gold written: **983** (excluded=17, quarantined=0, skipped=0, dedup=0)

## Top reasons

- `column_filter_mismatch:bao_format` (excluded_by_contract): 15
- `column_filter_mismatch:assay_test_type` (excluded_by_contract): 2

## IO

- **pipeline_name:** `chembl_assay`
- **run_type:** `backfill`
- **limit:** `1000`
- **skip_gold:** `False`
- **dry_run:** `False`
- **use_cached_bronze:** `True`

## Contract summary

- **gold_excluded_by_contract:** `17`
- **reasons:**
  - `{'reason_code': 'column_filter_mismatch:bao_format', 'outcome': 'excluded_by_contract', 'reason_family': 'system', 'count': 15}`
  - `{'reason_code': 'column_filter_mismatch:assay_test_type', 'outcome': 'excluded_by_contract', 'reason_family': 'system', 'count': 2}`
- **rejection_details:**
  - `{'reason_code': 'column_filter_mismatch', 'rule_type': 'column_filters', 'field': 'assay_test_type', 'operator': 'not_in', 'count': 2}`
  - `{'reason_code': 'column_filter_mismatch', 'rule_type': 'column_filters', 'field': 'bao_format', 'operator': 'not_in', 'count': 15}`

## Schema versions

- **reason_catalog_version:** `reason_catalog_v1`
- **bioetl_version:** `6.1.0`

## Performance

- **duration_seconds:** `8.899732`
- **records_per_second:** `112.3629`

## Artifacts

- `pipeline_run_report_json`: `D:/github/BioactivityDataAcquisition/data/workflow-reconciliation/repair-20261111/chembl_baseline/reports/run-reports/pipeline/chembl_assay/255d0816-3254-5fa5-bf7c-3d0227aab0d1/pipeline-run-report.json`
- `pipeline_run_report_md`: `D:/github/BioactivityDataAcquisition/data/workflow-reconciliation/repair-20261111/chembl_baseline/reports/run-reports/pipeline/chembl_assay/255d0816-3254-5fa5-bf7c-3d0227aab0d1/pipeline-run-report.md`

## Reconciliation

- silver vs bronze: **OK** (delta=0)
- gold vs silver: **OK** (delta=0)
