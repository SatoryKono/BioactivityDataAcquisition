#!/usr/bin/env python3
"""Unified entry point for scripts/engineering/ci/ commands.

Usage:
    python -m scripts.engineering.ci <command> [args...]
    python -m scripts.engineering.ci --help

Commands:
    run-tests       Run pytest with resilient retry logic
    quality-gate    Integral quality gate for CI
    pr-gate         Classify and aggregate required PR checks
    e2e-skip-rate   Check E2E matrix skip rate against threshold
    e2e-rerun       Check E2E rerun stability
    neo4j-memory    Check deterministic Neo4j memory ontology invariants
    neo4j-memory-live  Apply deterministic sync and validate live Neo4j drift
    debt-report     Generate weekly quality debt report
    apply-ci-fixes  Apply one-off hosted GitHub workflow fixes
"""

from __future__ import annotations

from pathlib import Path

from scripts.engineering.common.cli_dispatch import (
    dispatch_cli,
    python_command,
)

COMMANDS = {
    "run-tests": "run_pytest_resilient.py",
    "quality-gate": "quality_integral_gate.py",
    "pr-gate": "pr_gate.py",
    "e2e-skip-rate": "check_e2e_matrix_skip_rate.py",
    "e2e-rerun": "check_e2e_rerun_stability.py",
    "neo4j-memory": "check_neo4j_memory_ontology.py",
    "neo4j-memory-live": "check_neo4j_memory_live_audit.py",
    "debt-report": "report_quality_debt_weekly.py",
    "apply-ci-fixes": "apply_ci_fixes.py",
}
COMMAND_SPECS = {name: python_command(script) for name, script in COMMANDS.items()}

_DIR = Path(__file__).parent


def main(argv: list[str] | None = None) -> int:
    return dispatch_cli(
        argv,
        help_text=__doc__ or "",
        commands=COMMAND_SPECS,
        base_dir=_DIR,
    )


if __name__ == "__main__":
    raise SystemExit(main())
