# Pipeline run report: chembl_activity

- **run_id:** `f9ee04d2-965c-5c07-9c39-5a23ad0e6b82`
- **status:** success
- **run_type:** backfill
- **tracking:** full
- **catalog:** reason_catalog_v1
- **manifest_id:** `891d17d2-11d9-5b58-90f1-54cdee07e1b1`
- **provider/entity:** chembl / activity
- **started_at:** 2026-11-20T08:47:25.149933+00:00
- **completed_at:** 2026-11-20T08:48:40.495375+00:00
- **duration_seconds:** 75.345442
- **workflow:** `chembl_activity` / `fefad8ca-d1ba-5488-b777-39d641b33359` / `run_chembl_activity`

## Funnel

| Stage | In | Out | Removed | Balance | Tracking | Top reasons |
|-------|---:|----:|--------:|---------|----------|-------------|
| extract | 1000 | 1000 | 0 | OK | full | — |
| bronze | 1000 | 1000 | 0 | OK | full | — |
| silver | 1000 | 924 | 76 | OK | full | required_field_missing=76 |
| gold | 924 | 910 | 14 | OK | full | range_filter_mismatch:pchembl_value=14 |

## Layers

- bronze: **1000**
- silver valid: **924** (filtered=76, quarantined=0, skipped=0, dedup=0)
- gold written: **910** (excluded=14, quarantined=0, skipped=0, dedup=0)

## Top reasons

- `required_field_missing` (filtered_out): 76
- `range_filter_mismatch:pchembl_value` (excluded_by_contract): 14

## IO

- **pipeline_name:** `chembl_activity`
- **run_type:** `backfill`
- **limit:** `1000`
- **skip_gold:** `False`
- **dry_run:** `False`
- **use_cached_bronze:** `False`

## DQ summary

- **records_filtered_out:** `76`
- **records_quarantined:** `0`
- **reasons:**

## Contract summary

- **gold_excluded_by_contract:** `14`
- **reasons:**
  - `{'reason_code': 'range_filter_mismatch:pchembl_value', 'outcome': 'excluded_by_contract', 'reason_family': 'system', 'count': 14}`
- **rejection_details:**
  - `{'reason_code': 'range_filter_mismatch', 'rule_type': 'range_filters', 'field': 'pchembl_value', 'operator': 'range', 'count': 14}`

## Schema versions

- **reason_catalog_version:** `reason_catalog_v1`
- **bioetl_version:** `6.1.0`

## Performance

- **duration_seconds:** `75.345442`
- **records_per_second:** `13.2722`

## Artifacts

- `pipeline_run_report_json`: `D:/github/BioactivityDataAcquisition/data/wf1120/03/reports/pipeline/chembl_activity/f9ee04d2-965c-5c07-9c39-5a23ad0e6b82/pipeline-run-report.json`
- `pipeline_run_report_md`: `D:/github/BioactivityDataAcquisition/data/wf1120/03/reports/pipeline/chembl_activity/f9ee04d2-965c-5c07-9c39-5a23ad0e6b82/pipeline-run-report.md`

## Reconciliation

- silver vs bronze: **OK** (delta=0)
- gold vs silver: **OK** (delta=0)
