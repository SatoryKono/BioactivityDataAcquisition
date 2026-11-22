# Pipeline run report: chembl_cell_line

- **run_id:** `14713067-7d42-5f2c-a0bd-08ab20d0a003`
- **status:** failed
- **run_type:** backfill
- **tracking:** partial
- **catalog:** reason_catalog_v1
- **manifest_id:** `968786c0-2372-5758-99d7-63416def95c2`
- **provider/entity:** chembl / cell_line
- **started_at:** 2026-11-20T08:54:30.543055+00:00
- **completed_at:** 2026-11-20T08:55:07.709509+00:00
- **duration_seconds:** 37.166454
- **workflow:** `chembl_cell_line` / `fafcf9ec-507d-5284-93e0-536f677f9f85` / `run_chembl_cell_line`

## Funnel

| Stage | In | Out | Removed | Balance | Tracking | Top reasons |
|-------|---:|----:|--------:|---------|----------|-------------|
| extract | 0 | 0 | 0 | OK | partial | — |
| bronze | 0 | 0 | 0 | OK | partial | — |
| silver | 0 | 0 | 0 | OK | partial | — |
| gold | 0 | 0 | 0 | OK | partial | — |

## Layers

- bronze: **0**
- silver valid: **0** (filtered=0, quarantined=0, skipped=0, dedup=0)
- gold written: **0** (excluded=0, quarantined=0, skipped=0, dedup=0)

## Top reasons

- (none)

## Failure

- **error_type:** `ServiceUnavailableError`
- **error_message:** `Circuit breaker open for chembl. Retry after 2998.546829900006s`
- **failed_stage:** `None`
- **exit_hint:** `Investigate ServiceUnavailableError; check quarantine and gold contract exclusions.`

## IO

- **pipeline_name:** `chembl_cell_line`
- **run_type:** `backfill`
- **limit:** `1000`
- **skip_gold:** `False`
- **dry_run:** `False`
- **use_cached_bronze:** `False`

## Schema versions

- **reason_catalog_version:** `reason_catalog_v1`
- **bioetl_version:** `6.1.0`

## Performance

- **duration_seconds:** `37.166454`
- **records_per_second:** `None`

## Artifacts

- `pipeline_run_report_json`: `D:/github/BioactivityDataAcquisition/data/wf1120/06/reports/pipeline/chembl_cell_line/14713067-7d42-5f2c-a0bd-08ab20d0a003/pipeline-run-report.json`
- `pipeline_run_report_md`: `D:/github/BioactivityDataAcquisition/data/wf1120/06/reports/pipeline/chembl_cell_line/14713067-7d42-5f2c-a0bd-08ab20d0a003/pipeline-run-report.md`

## Reconciliation

- silver vs bronze: **OK** (delta=0)
- gold vs silver: **OK** (delta=0)
