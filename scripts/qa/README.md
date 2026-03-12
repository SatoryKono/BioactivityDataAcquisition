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
| `check-naming` | `naming_audit.py` | Naming convention audit (RULES.md §2) |
| `check-c901` | `check_c901_baseline.py` | C901 complexity baseline enforcement |
| `check-naming-pkg` | `check_naming_package_consistency.py` | Package naming consistency check |
| `check-exemptions` | `check_quality_exemptions.py` | Quality exemptions audit |
| `check-terminology` | `lint_terminology.py` | Terminology linting against glossary |
| `report-dep-map` | `generate_architecture_dependency_map.py` | Generate/check architecture dependency map |
| `report-hotspots` | `generate_hotspot_degradation_report.py` | Generate hotspot degradation report |
| `calibrate-hotspots` | `calibrate_hotspot_budgets.py` | Calibrate hotspot budgets |

## When to Use

| Command | When | Trigger |
|---------|------|---------|
| `check-naming` | After adding/renaming classes, functions, or modules; enforces NAME-001..009 rules | CI gate (`architecture.yml`, every PR) |
| `check-c901` | After modifying complex functions; prevents new C901 violations above baseline | CI gate (`import-linter.yml`, every PR) |
| `check-naming-pkg` | After restructuring packages or adding new modules; enforces factory isolation | CI gate (`architecture.yml`) |
| `check-exemptions` | After modifying quality exemption registry | CI gate (`architecture.yml`) |
| `check-terminology` | After adding domain terms; validates code uses canonical terminology per `glossary.md` | CI gate (`architecture.yml`) |
| `report-dep-map` | After changing imports in `src/bioetl/`; use `--check` for drift detection, `--update` to regenerate | Pre-commit hook + CI gate |
| `report-hotspots` | After performance benchmark runs; generates degradation report from JSONL observations | Manual, on-demand |
| `calibrate-hotspots` | After collecting new performance observations; recalculates budget thresholds | Manual, on-demand |
