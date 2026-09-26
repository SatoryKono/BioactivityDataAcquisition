# Architecture evidence inventory (#7372 / epic #7362)

Date: 2026-08-03
Base: origin/main@2c55a7d6fb
Branch: chore/architecture-evidence-closeout-7362

## Ownership map

| Artifact | Canonical generator | Owning test / gate | Disposition | Overlap |
| --- | --- | --- | --- | --- |
| `reports/quality/module-coverage-inventory.json` | `python -m scripts.engineering.qa.report_module_coverage_inventory --allow-missing-coverage-xml` | `tests/architecture/test_module_coverage_inventory.py` | refresh / current | #7371 |
| `reports/quality/test-governance-current.json` | `python -m scripts.engineering.qa.refresh_test_governance_baseline` | `tests/architecture/test_test_governance_audit.py`; `report_test_governance_audit.py --check` | refresh / current | #6239, #7257 |
| `reports/quality/test-fixture-asset-duplication.json` | same TG baseline command | TG audit | refresh / current | #6239 |
| `reports/quality/architecture-quality-scorecard.json` | `python -m scripts.engineering.qa.report_architecture_quality_scorecard` | `tests/architecture/test_architecture_quality_scorecard.py` | refresh / current | #7373 |
| `reports/quality/debt-governance-gates.json` | `python -m scripts.engineering.qa.report_debt_governance_gates --update` | debt-governance gates | refresh / current | #7373, #7038 |
| `reports/quality/compatibility-importer-census.json` | `python -m scripts.engineering.qa.report_compatibility_importer_census` | importer census governance tests | refresh / current | #7375, #7038 |
| `reports/quality/dead-code-inventory.json` | `python -m scripts.engineering.qa.report_dead_code_inventory` | debt gates | current | #7038 |
| `reports/quality/hotspot-family-baseline.json` | `python -m scripts.engineering.qa.report_hotspot_family_baseline --update` | generated_artifact_drift | refresh / current | #7373 |
| `reports/quality/config-surface-backlog.json` | `python -m scripts.engineering.qa.report_config_surface_backlog` | generated_artifact_drift | refresh / current | #7373 |
| `reports/quality/architecture-debt-remote-main-baseline.json` | `python -m scripts.engineering.qa.report_architecture_debt_remote_main_baseline --update` | remote_main_architecture_debt_baseline | refresh / current | #7038 |
| `reports/observability/scenes-parity-ledger.json` | `python -m scripts.engineering.qa.report_dashboard_scenes_parity` | `tests/architecture/test_dashboard_scenes_contract.py` | current | #7374 |
| `reports/quality/layer-contract-coverage-matrix.json` | committed matrix (entity config coverage) | `tests/architecture/test_layer_contract_coverage_matrix.py` | current | #7374 |
| `configs/quality/technical_debt_audit_registry.yaml` + `reports/quality/total-tech-debt-audit-main-current.md` | registry pin + report markers | `python -m scripts.engineering.qa.technical_debt_audit_registry` | refresh / current | #7038 |

## Markerless remediation

| Test | Fix |
| --- | --- |
| `tests/architecture/test_module_coverage_inventory.py::test_module_coverage_git_guard_avoids_windows_pipe_reader_threads` | `@pytest.mark.architecture` |
| `tests/unit/helpers/test_module_coverage_inventory_support.py` | module `pytestmark = pytest.mark.unit` (already present on main) |

## Budgets

No debt budgets, coverage targets, thresholds, or exemptions increased.

## Verification (local)

- module-coverage inventory `--check` PASS
- test-governance audit `--check` PASS (markerless=0)
- debt-governance gates `--check` PASS (45/45)
- technical-debt audit registry PASS
- scenes parity `--check` PASS
- importer census `--check` PASS
- dead-code inventory `--check` PASS

## Restored surfaces

- Restored `layer-contract-coverage-matrix` from governed history and updated chembl_activity contract_test_paths to repo-backed location.
- Restored scenes-baseline `render-manifest.json` evidence for 4 viewport/theme groups.
