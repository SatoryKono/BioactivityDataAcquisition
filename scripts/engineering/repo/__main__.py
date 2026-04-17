#!/usr/bin/env python3
"""Unified entry point for scripts/engineering/repo/ commands.

Usage:
    python -m scripts.engineering.repo <command> [args...]
    python -m scripts.engineering.repo --help

Commands:
    check-inventory    Check scripts inventory drift
    sync-inventory     Refresh scripts inventory manifest
    check-catalog      Validate catalog governance policy
    check-versions     Check version consistency across project files
    check-cleanliness  Audit repository root layout allowlist
    split-testing-roadmap  Create or preview #2511 child issues
    sync-docs-issues   Preview or apply docs-sync issue metadata
    all                Run all checks sequentially
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

COMMANDS: dict[str, str] = {
    "check-inventory": "check_scripts_inventory.py",
    "sync-inventory": "sync_scripts_inventory.py",
    "check-catalog": "check_scripts_catalog.py",
    "check-versions": "check_version_consistency.py",
    "check-cleanliness": "audit_root_cleanliness.py",
    "split-testing-roadmap": "split_testing_roadmap_issue.py",
    "sync-docs-issues": "sync_docs_issues.py",
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

    if cmd == "all":
        for name, script in COMMANDS.items():
            print(f"\n{'=' * 60}")
            print(f"  {name}")
            print(f"{'=' * 60}\n")
            rc = _run_script(script, rest)
            if rc != 0:
                print(f"\n[FAIL] {name} exited with code {rc}", file=sys.stderr)
                return rc
        print(f"\n{'=' * 60}")
        print("  All checks passed.")
        print(f"{'=' * 60}")
        return 0

    if cmd not in COMMANDS:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        print(f"Available: {', '.join(COMMANDS)} | all", file=sys.stderr)
        return 2

    return _run_script(COMMANDS[cmd], rest)


if __name__ == "__main__":
    raise SystemExit(main())
