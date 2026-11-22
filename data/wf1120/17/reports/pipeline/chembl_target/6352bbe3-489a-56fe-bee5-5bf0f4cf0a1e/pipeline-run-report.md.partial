# Pipeline run report: chembl_target

- **run_id:** `6352bbe3-489a-56fe-bee5-5bf0f4cf0a1e`
- **status:** success
- **run_type:** backfill
- **tracking:** full
- **catalog:** reason_catalog_v1
- **manifest_id:** `189e4e8a-263b-58f9-9108-31eac28f43f0`
- **provider/entity:** chembl / target
- **started_at:** 2026-11-20T09:23:40.562543+00:00
- **completed_at:** 2026-11-20T09:25:07.371599+00:00
- **duration_seconds:** 86.809056
- **workflow:** `chembl_target_protein_classification` / `e7d65d91-dbbf-5b05-a5b4-f972fd1fd589` / `run_chembl_target`

## Funnel

| Stage | In | Out | Removed | Balance | Tracking | Top reasons |
|-------|---:|----:|--------:|---------|----------|-------------|
| extract | 1000 | 1000 | 0 | OK | full | — |
| bronze | 1000 | 1000 | 0 | OK | full | — |
| silver | 1000 | 1000 | 0 | OK | full | — |
| gold | 1000 | 922 | 78 | OK | full | column_filter_mismatch:organism_class=78 |

## Layers

- bronze: **1000**
- silver valid: **1000** (filtered=0, quarantined=0, skipped=0, dedup=0)
- gold written: **922** (excluded=78, quarantined=0, skipped=0, dedup=0)

## Top reasons

- `column_filter_mismatch:organism_class` (excluded_by_contract): 78

## IO

- **pipeline_name:** `chembl_target`
- **run_type:** `backfill`
- **limit:** `1000`
- **skip_gold:** `False`
- **dry_run:** `False`
- **use_cached_bronze:** `False`

## Contract summary

- **gold_excluded_by_contract:** `78`
- **reasons:**
  - `{'reason_code': 'column_filter_mismatch:organism_class', 'outcome': 'excluded_by_contract', 'reason_family': 'system', 'count': 78}`
- **rejection_details:**
  - `{'reason_code': 'column_filter_mismatch', 'rule_type': 'column_filters', 'field': 'organism_class', 'operator': 'not_in', 'count': 78}`

## Schema versions

- **reason_catalog_version:** `reason_catalog_v1`
- **bioetl_version:** `6.1.0`

## Performance

- **duration_seconds:** `86.809056`
- **records_per_second:** `11.5195`

## Artifacts

- `pipeline_run_report_json`: `D:/github/BioactivityDataAcquisition/data/wf1120/17/reports/pipeline/chembl_target/6352bbe3-489a-56fe-bee5-5bf0f4cf0a1e/pipeline-run-report.json`
- `pipeline_run_report_md`: `D:/github/BioactivityDataAcquisition/data/wf1120/17/reports/pipeline/chembl_target/6352bbe3-489a-56fe-bee5-5bf0f4cf0a1e/pipeline-run-report.md`

## Reconciliation

- silver vs bronze: **OK** (delta=0)
- gold vs silver: **OK** (delta=0)
