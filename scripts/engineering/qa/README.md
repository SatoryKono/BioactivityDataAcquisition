# scripts/qa — Quality & Architecture Checks

Architecture and quality-gate checks, debt telemetry, and code hygiene audits.

## Unified Entry Point

```bash
python -m scripts.engineering.qa --help
python -m scripts.engineering.qa <command> [args...]
```

## Commands

| Command                       | Script                                    | Description                                                                                       |
| ----------------------------- | ----------------------------------------- | ------------------------------------------------------------------------------------------------- |
| `check-naming`                | `naming_audit.py`                         | Naming convention audit (RULES.md §2) with `configs/naming_exceptions.yaml` as exception registry |
| `check-architecture`          | `check_architecture.py`                   | Canonical compatibility wrapper for the legacy infrastructure architecture check                  |
| `check-app-deps`              | `check_application_deps.py`               | Canonical compatibility wrapper for the legacy application dependency check                       |
| `check-constructor-args`      | `check_constructor_args.py`               | Canonical compatibility wrapper for the legacy constructor argument audit                         |
| `check-c901`                  | `check_c901_baseline.py`                  | C901 complexity baseline enforcement                                                              |
| `check-naming-pkg`            | `check_naming_package_consistency.py`     | Package naming consistency check                                                                  |
| `check-exemptions`            | `check_quality_exemptions.py`             | Quality exemptions audit                                                                          |
| `generate-debt-tasks`         | `generate_architecture_debt_tasks.py`     | Generate `tasks_architecture_metric_exemptions_*.json` from the registry                          |
| `reduce-architecture-debt`    | `reduce_architecture_debt.py`             | Build `architecture_debt_execution_plan_*.json` from the latest tasks file                        |
| `check-terminology`           | `lint_terminology.py`                     | Terminology linting against glossary                                                              |
| `report-dep-map`              | `generate_architecture_dependency_map.py` | Generate/check architecture dependency map                                                        |
| `report-vcr-metadata`         | `report_vcr_metadata_catalog.py`          | Generate/check canonical VCR metadata catalog                                                     |
| `report-provider-contract-drift` | `report_provider_contract_drift.py`    | Generate provider contract drift diagnostics from replay cassettes                                |
| `report-family-baseline`      | `report_hotspot_family_baseline.py` | Generate/check RF-06 hotspot-family baseline artifacts                                             |
| `report-hotspots`             | `generate_hotspot_degradation_report.py`  | Generate performance hotspot degradation report                                                   |
| `report-duplication-baseline` | `report_duplication_baseline.py`          | Generate report-only duplication baseline for `composition`/`application`                         |
| `analyze-duplicate-functions` | `analyze_duplicate_functions.py`          | Compatibility wrapper for the legacy AST duplicate-function analyzer                              |
| `calibrate-hotspots`          | `scripts/engineering/qa/calibrate_hotspot_budgets.py` | Calibrate hotspot budgets                                                                         |

## When to Use

| Command                       | When                                                                                                                                             | Trigger                                    |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------ |
| `check-naming`                | After adding/renaming classes, functions, or modules; enforces NAME-001..009 rules                                                               | CI gate (`architecture.yml`, every PR)     |
| `check-architecture`          | When reproducing or migrating the legacy infrastructure architecture check through the canonical QA entrypoint                                   | Manual, Makefile migration path            |
| `check-app-deps`              | When reproducing or migrating the legacy application dependency check through the canonical QA entrypoint                                        | Manual, Makefile migration path            |
| `check-constructor-args`      | When reproducing or migrating the legacy constructor-args audit through the canonical QA entrypoint                                              | CI migration path, manual use              |
| `check-c901`                  | After modifying complex functions; prevents new C901 violations above baseline                                                                   | CI gate (`import-linter.yml`, every PR)    |
| `check-naming-pkg`            | After restructuring packages or adding new modules; enforces factory isolation                                                                   | CI gate (`architecture.yml`)               |
| `check-exemptions`            | After modifying quality exemption registry                                                                                                       | CI gate (`architecture.yml`)               |
| `generate-debt-tasks`         | Before a debt-reduction campaign; creates the canonical refactoring task backlog from the registry                                               | Manual, on-demand                          |
| `reduce-architecture-debt`    | Before running the debt-reduction agent; classifies latest tasks into an execution order                                                         | Manual, on-demand                          |
| `check-terminology`           | After adding domain terms; validates code uses canonical terminology per `glossary.md`                                                           | CI gate (`architecture.yml`)               |
| `report-dep-map`              | After changing imports in `src/bioetl/`; use `--check` for drift detection, `--update` to regenerate                                             | Pre-commit hook + CI gate                  |
| `report-vcr-metadata`         | When updating VCR fixture governance rollout or sidecar inventory; use `--check` for drift detection, `--update` to regenerate                   | Architecture / test-governance maintenance |
| `report-provider-contract-drift` | When reviewing provider-facing API drift in PR/CI; writes a machine-readable replay report and can fail on warnings/breaking drift            | Provider contract replay CI gate           |
| `report-family-baseline`      | When reviewing RF-06 hotspot-family budgets or checking that the committed family baseline artifacts still match the code                      | Manual, preflight / CI drift check         |
| `report-hotspots`             | After performance benchmark runs; generates degradation report from JSONL observations                                                           | Manual, on-demand                          |
| `report-duplication-baseline` | When reviewing duplication pressure in `composition` or `application`; generates report-only baseline artifacts without creating a blocking gate | Manual, on-demand                          |
| `analyze-duplicate-functions` | When you need the older duplicate-function AST report through the canonical QA entrypoint                                                        | Manual, audit/reporting                    |
| `calibrate-hotspots`          | After collecting new performance observations; recalculates budget thresholds                                                                    | Manual, on-demand                          |

Important distinction:

- `report-hotspots` is for benchmark-backed performance hotspots.
- `report-duplication-baseline` is for structural duplication visibility in `src/bioetl/composition` and `src/bioetl/application`.
- Source-tree size hotspots such as `>10 KB` files or `>350 LOC` files are a separate structural inventory and should be discussed as hotspot inventory, not as scorecard exemption debt.
- `check-c901` remains the clean blocking baseline for complexity debt; file-size scorecard numbers refer to exemption registry state unless a policy explicitly says otherwise.

Direct script path:

- `scripts/engineering/qa/report_duplication_baseline.py` (`python -m scripts.engineering.qa report-duplication-baseline`) generates report-only duplication baseline artifacts for governance review.
- `scripts/engineering/qa/generate_architecture_debt_tasks.py` (`python -m scripts.engineering.qa generate-debt-tasks`) generates the canonical architecture debt task backlog.
- `scripts/engineering/qa/reduce_architecture_debt.py` (`python -m scripts.engineering.qa reduce-architecture-debt`) builds the orchestration plan consumed by the architecture-debt agent.

## Canonical Commands

```bash
python scripts/engineering/qa/generate_architecture_dependency_map.py --check
python scripts/engineering/qa/generate_architecture_dependency_map.py --update
python scripts/engineering/qa/report_vcr_metadata_catalog.py --check
python scripts/engineering/qa/report_vcr_metadata_catalog.py --update
python scripts/engineering/qa/report_provider_contract_drift.py --output reports/quality/provider-contract-drift-report.json --fail-on breaking
python -m scripts.engineering.qa report-family-baseline --check
python -m scripts.engineering.qa report-family-baseline --update
python scripts/engineering/qa/report_duplication_baseline.py
python -m scripts.engineering.qa check-architecture
python -m scripts.engineering.qa check-app-deps
python -m scripts.engineering.qa check-constructor-args -- --warn-only
python -m scripts.engineering.qa analyze-duplicate-functions
```

`scripts/generate_architecture_dependency_map.py` remains a compatibility wrapper only.
The legacy direct paths for the historical architecture, application-deps, and
constructor-args checks remain supported during the migration window, but new
integrations should use the grouped QA commands above. The grouped QA commands
now own the implementation, while the older `src/tools/scripts/check_*` paths
act only as compatibility wrappers.
