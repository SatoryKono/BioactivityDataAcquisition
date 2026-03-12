#!/usr/bin/env python3
"""Unified entry point for scripts/qa/ commands.

Usage:
    python -m scripts.qa <command> [args...]
    python -m scripts.qa --help

Commands:
    check-naming         Naming convention audit
    check-c901           C901 complexity baseline enforcement
    check-naming-pkg     Package naming consistency check
    check-exemptions     Quality exemptions audit
    check-terminology    Terminology linting
    report-dep-map       Generate/check architecture dependency map
    report-hotspots      Generate hotspot degradation report
    calibrate-hotspots   Calibrate hotspot budgets
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

COMMANDS: dict[str, str] = {
    "check-naming": "naming_audit.py",
    "check-c901": "check_c901_baseline.py",
    "check-naming-pkg": "check_naming_package_consistency.py",
    "check-exemptions": "check_quality_exemptions.py",
    "check-terminology": "lint_terminology.py",
    "report-dep-map": "generate_architecture_dependency_map.py",
    "report-hotspots": "generate_hotspot_degradation_report.py",
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
