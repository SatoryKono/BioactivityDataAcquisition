# Pipeline run report: chembl_molecule

- **run_id:** `c869cf53-f97b-5ac7-84cb-7ce83782d772`
- **status:** success
- **run_type:** incremental
- **tracking:** full
- **catalog:** reason_catalog_v1
- **manifest_id:** `cfb1dc13-5ddd-55bb-a0f0-b78f5b5eee99`
- **provider/entity:** chembl / molecule
- **started_at:** 2026-11-20T05:09:54.825059+00:00
- **completed_at:** 2026-11-20T05:10:03.223164+00:00
- **duration_seconds:** 8.398105

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
- **run_type:** `incremental`
- **limit:** `1000`
- **skip_gold:** `False`
- **dry_run:** `False`
- **use_cached_bronze:** `True`
- **cached_bronze_path:** `D:/github/BioactivityDataAcquisition/data/workflows-limit1000-20261118T042057Z/chembl_molecule/output/bronze/chembl/molecule`

## Schema versions

- **reason_catalog_version:** `reason_catalog_v1`
- **bioetl_version:** `6.1.0`

## Performance

- **duration_seconds:** `8.398105`
- **records_per_second:** `119.0745`

## Artifacts

- `bronze_batch`: `D:/github/BioactivityDataAcquisition/data/workflows-limit1000-20261118T042057Z/chembl_molecule/output/bronze/chembl/molecule/2026-11-18/batch_2026-11-18_64dfb0f8-ee12-557b-a3cf-ec181f7ccbbe.jsonl.zst`
- `pipeline_run_report_json`: `D:/github/BioactivityDataAcquisition/data/chembl-molecule-recovery-20261119/offline/reports/pipeline/chembl_molecule/c869cf53-f97b-5ac7-84cb-7ce83782d772/pipeline-run-report.json`
- `pipeline_run_report_md`: `D:/github/BioactivityDataAcquisition/data/chembl-molecule-recovery-20261119/offline/reports/pipeline/chembl_molecule/c869cf53-f97b-5ac7-84cb-7ce83782d772/pipeline-run-report.md`

## Reconciliation

- silver vs bronze: **OK** (delta=0)
- gold vs silver: **OK** (delta=0)
