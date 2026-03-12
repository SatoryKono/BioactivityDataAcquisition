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
