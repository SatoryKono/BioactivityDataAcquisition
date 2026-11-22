# Pipeline run report: chembl_molecule

- **run_id:** `3f634546-3144-5462-9b0b-62c2ce411ccc`
- **status:** success
- **run_type:** backfill
- **tracking:** full
- **catalog:** reason_catalog_v1
- **manifest_id:** `223829d1-c380-5b78-a0cd-a4b1f3f2274c`
- **provider/entity:** chembl / molecule
- **started_at:** 2026-11-20T04:36:57.420111+00:00
- **completed_at:** 2026-11-20T04:37:39.127729+00:00
- **duration_seconds:** 41.707618
- **workflow:** `chembl_molecule` / `0b68c9b0-17a2-5f2b-ad4c-f5056820fdce` / `run_chembl_molecule`

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

- **duration_seconds:** `41.707618`
- **records_per_second:** `23.9764`

## Artifacts

- `pipeline_run_report_json`: `D:/github/BioactivityDataAcquisition/data/chembl-molecule-recovery-20261119/live/reports/pipeline/chembl_molecule/3f634546-3144-5462-9b0b-62c2ce411ccc/pipeline-run-report.json`
- `pipeline_run_report_md`: `D:/github/BioactivityDataAcquisition/data/chembl-molecule-recovery-20261119/live/reports/pipeline/chembl_molecule/3f634546-3144-5462-9b0b-62c2ce411ccc/pipeline-run-report.md`

## Reconciliation

- silver vs bronze: **OK** (delta=0)
- gold vs silver: **OK** (delta=0)
