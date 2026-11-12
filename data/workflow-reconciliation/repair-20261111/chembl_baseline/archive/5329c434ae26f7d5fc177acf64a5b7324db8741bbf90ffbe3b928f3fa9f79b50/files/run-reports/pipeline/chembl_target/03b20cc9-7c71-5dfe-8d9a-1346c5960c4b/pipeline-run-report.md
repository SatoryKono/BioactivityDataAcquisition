# Pipeline run report: chembl_target

- **run_id:** `03b20cc9-7c71-5dfe-8d9a-1346c5960c4b`
- **status:** success
- **run_type:** backfill
- **tracking:** full
- **catalog:** reason_catalog_v1
- **manifest_id:** `d3b8775c-8d97-58b9-ab49-34f5139cbb5a`
- **provider/entity:** chembl / target
- **started_at:** 2026-11-11T18:14:44.803984+00:00
- **completed_at:** 2026-11-11T18:16:01.045748+00:00
- **duration_seconds:** 76.241764
- **workflow:** `chembl_baseline` / `30b43f27-5d21-56de-8289-a6c62181d6da` / `run_chembl_target`

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
- **filter_column:** `target_id`
- **skip_gold:** `False`
- **dry_run:** `False`
- **use_cached_bronze:** `True`
- **filter_id_count:** `73`
- **filter_id_hash:** `0089e2d9ce8844bd`

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

- **duration_seconds:** `76.241764`
- **records_per_second:** `13.1162`

## Artifacts

- `pipeline_run_report_json`: `D:/github/BioactivityDataAcquisition/data/workflow-reconciliation/repair-20261111/chembl_baseline/reports/run-reports/pipeline/chembl_target/03b20cc9-7c71-5dfe-8d9a-1346c5960c4b/pipeline-run-report.json`
- `pipeline_run_report_md`: `D:/github/BioactivityDataAcquisition/data/workflow-reconciliation/repair-20261111/chembl_baseline/reports/run-reports/pipeline/chembl_target/03b20cc9-7c71-5dfe-8d9a-1346c5960c4b/pipeline-run-report.md`

## Reconciliation

- silver vs bronze: **OK** (delta=0)
- gold vs silver: **OK** (delta=0)
