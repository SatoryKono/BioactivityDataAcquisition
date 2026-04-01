# scripts/qa — Quality & Architecture Checks

Architecture and quality-gate checks, debt telemetry, and code hygiene audits.

## Unified Entry Point

```bash
python -m scripts.qa --help
python -m scripts.qa <command> [args...]
```

## Commands

| Command | Script | Description |
|---------|--------|-------------|
| `check-naming` | `naming_audit.py` | Naming convention audit (RULES.md §2) with `configs/naming_exceptions.yaml` as exception registry |
| `check-c901` | `check_c901_baseline.py` | C901 complexity baseline enforcement |
| `check-naming-pkg` | `check_naming_package_consistency.py` | Package naming consistency check |
| `check-exemptions` | `check_quality_exemptions.py` | Quality exemptions audit |
| `check-terminology` | `lint_terminology.py` | Terminology linting against glossary |
| `report-dep-map` | `generate_architecture_dependency_map.py` | Generate/check architecture dependency map |
| `report-vcr-metadata` | `report_vcr_metadata_catalog.py` | Generate/check canonical VCR metadata catalog |
| `report-hotspots` | `generate_hotspot_degradation_report.py` | Generate performance hotspot degradation report |
| `report-duplication-baseline` | `report_duplication_baseline.py` | Generate report-only duplication baseline for `composition`/`application` |
| `calibrate-hotspots` | `scripts/qa/calibrate_hotspot_budgets.py` | Calibrate hotspot budgets |

## When to Use

| Command | When | Trigger |
|---------|------|---------|
| `check-naming` | After adding/renaming classes, functions, or modules; enforces NAME-001..009 rules | CI gate (`architecture.yml`, every PR) |
| `check-c901` | After modifying complex functions; prevents new C901 violations above baseline | CI gate (`import-linter.yml`, every PR) |
| `check-naming-pkg` | After restructuring packages or adding new modules; enforces factory isolation | CI gate (`architecture.yml`) |
| `check-exemptions` | After modifying quality exemption registry | CI gate (`architecture.yml`) |
| `check-terminology` | After adding domain terms; validates code uses canonical terminology per `glossary.md` | CI gate (`architecture.yml`) |
| `report-dep-map` | After changing imports in `src/bioetl/`; use `--check` for drift detection, `--update` to regenerate | Pre-commit hook + CI gate |
| `report-vcr-metadata` | When updating VCR fixture governance rollout or sidecar inventory; use `--check` for drift detection, `--update` to regenerate | Architecture / test-governance maintenance |
| `report-hotspots` | After performance benchmark runs; generates degradation report from JSONL observations | Manual, on-demand |
| `report-duplication-baseline` | When reviewing duplication pressure in `composition` or `application`; generates report-only baseline artifacts without creating a blocking gate | Manual, on-demand |
| `calibrate-hotspots` | After collecting new performance observations; recalculates budget thresholds | Manual, on-demand |

Important distinction:

- `report-hotspots` is for benchmark-backed performance hotspots.
- `report-duplication-baseline` is for structural duplication visibility in `src/bioetl/composition` and `src/bioetl/application`.
- Source-tree size hotspots such as `>10 KB` files or `>350 LOC` files are a separate structural inventory and should be discussed as hotspot inventory, not as scorecard exemption debt.
- `check-c901` remains the clean blocking baseline for complexity debt; file-size scorecard numbers refer to exemption registry state unless a policy explicitly says otherwise.

Direct script path:

- `scripts/qa/report_duplication_baseline.py` (`python -m scripts.qa report-duplication-baseline`) generates report-only duplication baseline artifacts for governance review.

## Canonical Commands

```bash
python scripts/qa/generate_architecture_dependency_map.py --check
python scripts/qa/generate_architecture_dependency_map.py --update
python scripts/qa/report_vcr_metadata_catalog.py --check
python scripts/qa/report_vcr_metadata_catalog.py --update
python scripts/qa/report_duplication_baseline.py
```

`scripts/generate_architecture_dependency_map.py` remains a compatibility wrapper only.
