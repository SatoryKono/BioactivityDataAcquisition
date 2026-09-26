# Architecture Governance Audit Evidence

This page is a navigation mirror for current architecture-governance evidence.
It does not redefine runtime behavior, agent behavior, or debt budgets.

## Current Evidence Artifacts

| Evidence | Machine-readable source | Guard |
| --- | --- | --- |
| Architecture quality scorecard | `reports/quality/architecture-quality-scorecard.json` | `tests/architecture/test_architecture_quality_scorecard.py` |
| Hotspot family baseline | `reports/quality/hotspot-family-baseline.json` | `tests/architecture/test_hotspot_growth_family_ratchets.py`, `tests/architecture/test_hotspot_fan_in_family_ratchets.py`, `tests/architecture/test_hotspot_duplication_family_ratchets.py` |
| Gold contract coverage | `reports/quality/contract-coverage-matrix.json` | `tests/architecture/test_contract_coverage_matrix_integrity.py`, `tests/architecture/test_contract_coverage_matrix_drift.py` |
| Bronze/Silver/Gold layer coverage | `reports/quality/layer-contract-coverage-matrix.json` | `tests/architecture/test_layer_contract_coverage_matrix.py` |
| Replay-critical time seams | `configs/quality/time_seam_classification.yaml` | `tests/architecture/test_time_seam_classification.py`, `tests/architecture/test_replay_critical_time_seams.py` |
| VCR metadata catalog | `reports/quality/vcr-metadata-catalog.json` | `tests/architecture/test_vcr_metadata_catalog_drift.py` |
| Generated artifact drift workflow | `docs/05-operations/runbooks/generated-artifact-drift-workflow.md` | `tests/architecture/test_generated_artifact_drift_workflow.py` |

## Numeric Examples

Numeric values in narrative docs are historical unless the paragraph links to
one of the machine-readable artifacts above. Current decisions should read the
JSON/YAML artifacts and their guard tests first.

## Budget Policy

Technical-debt budgets can only stay flat or decrease. A generated artifact
showing debt growth requires architecture review and remediation planning, not a
budget increase.
