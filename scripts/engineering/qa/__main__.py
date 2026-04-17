#!/usr/bin/env python3
"""Unified entry point for scripts/engineering/qa/ commands.

Usage:
    python -m scripts.engineering.qa <command> [args...]
    python -m scripts.engineering.qa --help

Commands:
    check-naming         Naming convention audit
    check-architecture   Infrastructure architecture compatibility check
    check-app-deps       Application dependency compatibility check
    check-constructor-args Constructor argument compatibility check
    check-c901           C901 complexity baseline enforcement
    check-naming-pkg     Package naming consistency check
    check-exemptions     Quality exemptions audit
    generate-debt-tasks  Generate architecture debt task backlog from exemptions registry
    reduce-architecture-debt  Build execution plan from latest architecture debt tasks JSON
    check-terminology    Terminology linting
    report-dep-map       Generate/check architecture dependency map
    report-vcr-metadata  Generate/check canonical VCR metadata catalog
    report-provider-contract-drift  Generate provider contract drift diagnostics from replay cassettes
    sync-integration-vcr-policy Sync tracked integration/e2e inventory in integration VCR policy
    report-family-baseline Generate/check RF-06 hotspot-family baseline artifacts
    report-hotspots      Generate hotspot degradation report
    report-duplication-baseline  Generate report-only duplication baseline
    report-function-length-inventory Generate report-only near-threshold function length inventory
    report-normalization-fallback-inventory Generate report-only fallback normalization inventory
    report-observability-metric-inventory Generate registry/runtime/docs observability metric inventory
    analyze-duplicate-functions Analyze duplicate function names across selected code areas
    calibrate-hotspots   Calibrate hotspot budgets
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

COMMANDS: dict[str, str] = {
    "check-naming": "naming_audit.py",
    "check-architecture": "check_architecture.py",
    "check-app-deps": "check_application_deps.py",
    "check-constructor-args": "check_constructor_args.py",
    "check-c901": "check_c901_baseline.py",
    "check-naming-pkg": "check_naming_package_consistency.py",
    "check-exemptions": "check_quality_exemptions.py",
    "generate-debt-tasks": "generate_architecture_debt_tasks.py",
    "reduce-architecture-debt": "reduce_architecture_debt.py",
    "check-terminology": "lint_terminology.py",
    "report-dep-map": "generate_architecture_dependency_map.py",
    "report-vcr-metadata": "report_vcr_metadata_catalog.py",
    "report-provider-contract-drift": "report_provider_contract_drift.py",
    "sync-integration-vcr-policy": "sync_integration_vcr_policy.py",
    "report-family-baseline": "report_hotspot_family_baseline.py",
    "report-hotspots": "generate_hotspot_degradation_report.py",
    "report-duplication-baseline": "report_duplication_baseline.py",
    "report-function-length-inventory": "report_function_length_inventory.py",
    "report-normalization-fallback-inventory": "report_normalization_fallback_inventory.py",
    "report-observability-metric-inventory": "report_observability_metric_inventory.py",
    "analyze-duplicate-functions": "analyze_duplicate_functions.py",
    "calibrate-hotspots": "calibrate_hotspot_budgets.py",
}

_DIR = Path(__file__).parent


def _run_script(name: str, argv: list[str]) -> int:
    script = _DIR / name
    result = subprocess.run([sys.executable, str(script), *argv], check=False)
    return result.returncode


def _print_help() -> None:
    print(__doc__ or "", end="")


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]

    if not args or args[0] in ("--help", "-h"):
        _print_help()
        return 0

    cmd, rest = args[0], args[1:]

    if cmd not in COMMANDS:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        print(f"Available: {', '.join(COMMANDS)}", file=sys.stderr)
        return 2

    return _run_script(COMMANDS[cmd], rest)


if __name__ == "__main__":
    raise SystemExit(main())
