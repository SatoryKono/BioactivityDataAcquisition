# Pipeline run report: chembl_target

- **run_id:** `80bbca48-6d27-54e0-9969-359575d4fc16`
- **status:** failed
- **run_type:** backfill
- **tracking:** partial
- **catalog:** reason_catalog_v1
- **manifest_id:** `09e50cd8-fcd6-5b6a-a455-d3d4270bbe95`
- **provider/entity:** chembl / target
- **started_at:** 2026-11-20T09:19:24.267614+00:00
- **completed_at:** 2026-11-20T09:19:57.140132+00:00
- **duration_seconds:** 32.872518
- **workflow:** `chembl_reference_pack` / `6fb38224-594e-5802-aa72-7137e03a1eac` / `run_chembl_target`

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

- **error_type:** `ExternalServiceError`
- **error_message:** `[Errno 11001] getaddrinfo failed`
- **failed_stage:** `None`
- **exit_hint:** `Investigate ExternalServiceError; check quarantine and gold contract exclusions.`

## IO

- **pipeline_name:** `chembl_target`
- **run_type:** `backfill`
- **limit:** `1000`
- **skip_gold:** `False`
- **dry_run:** `False`
- **use_cached_bronze:** `False`

## Schema versions

- **reason_catalog_version:** `reason_catalog_v1`
- **bioetl_version:** `6.1.0`

## Performance

- **duration_seconds:** `32.872518`
- **records_per_second:** `None`

## Artifacts

- `pipeline_run_report_json`: `D:/github/BioactivityDataAcquisition/data/wf1120/14/reports/pipeline/chembl_target/80bbca48-6d27-54e0-9969-359575d4fc16/pipeline-run-report.json`
- `pipeline_run_report_md`: `D:/github/BioactivityDataAcquisition/data/wf1120/14/reports/pipeline/chembl_target/80bbca48-6d27-54e0-9969-359575d4fc16/pipeline-run-report.md`

## Reconciliation

- silver vs bronze: **OK** (delta=0)
- gold vs silver: **OK** (delta=0)
