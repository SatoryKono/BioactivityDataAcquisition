#!/usr/bin/env python3
"""Unified entry point for scripts/engineering/ci/ commands.

Usage:
    python -m scripts.engineering.ci <command> [args...]
    python -m scripts.engineering.ci --help

Commands:
    run-tests       Run pytest with resilient retry logic
    quality-gate    Integral quality gate for CI
    e2e-skip-rate   Check E2E matrix skip rate against threshold
    e2e-rerun       Check E2E rerun stability
    neo4j-memory    Check deterministic Neo4j memory ontology invariants
    neo4j-memory-live  Apply deterministic sync and validate live Neo4j drift
    debt-report     Generate weekly quality debt report
    apply-ci-fixes  Apply one-off hosted GitHub workflow fixes
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

COMMANDS: dict[str, str] = {
    "run-tests": "run_pytest_resilient.py",
    "quality-gate": "quality_integral_gate.py",
    "e2e-skip-rate": "check_e2e_matrix_skip_rate.py",
    "e2e-rerun": "check_e2e_rerun_stability.py",
    "neo4j-memory": "check_neo4j_memory_ontology.py",
    "neo4j-memory-live": "check_neo4j_memory_live_audit.py",
    "debt-report": "report_quality_debt_weekly.py",
    "apply-ci-fixes": "apply_ci_fixes.py",
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
