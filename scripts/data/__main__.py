#!/usr/bin/env python3
"""Compatibility entry point for scripts/data commands.

Usage:
    python -m scripts.data <command> [args...]
    python -m scripts.data --help

Canonical command groups:
    python -m scripts.ops.data <command>
    python -m scripts.engineering.qa.vcr <command>
    python -m scripts.engineering.baselines <command>

Commands:
    check-vcr-placement    Block VCR cassette anti-patterns
    check-vcr-naming       Enforce VCR filename policy
    check-vcr-secrets      Detect potential secret leaks in VCR cassettes
    check-delta            Check Delta Lake integrity
    check-data-dir         Validate data directory structure
    vacuum                 Vacuum Delta tables
    checksums              Generate/verify file checksums
    dq-baseline            Update DQ baseline metrics
    report-null-fields     Extract null field statistics
    report-content-hash    Generate content hash comparison report
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.common.repo_paths import REPO_ROOT

COMMANDS: dict[str, str] = {
    "check-vcr-placement": "scripts/engineering/qa/vcr/check_root_vcr_cassettes.py",
    "check-vcr-naming": "scripts/engineering/qa/vcr/check_vcr_filename_policy.py",
    "check-vcr-secrets": "scripts/engineering/qa/vcr/check_vcr_secrets.py",
    "check-delta": "scripts/ops/data/check_delta_integrity.py",
    "check-data-dir": "scripts/ops/data/validate_data_dir.py",
    "vacuum": "scripts/ops/data/vacuum_delta.py",
    "checksums": "scripts/ops/data/verify_checksums.py",
    "dq-baseline": "scripts/engineering/baselines/dq_baseline_update.py",
    "report-null-fields": "scripts/ops/data/extract_null_fields.py",
    "report-content-hash": "scripts/ops/data/generate_content_hash_comparison_report.py",
}


def _run_script(name: str, argv: list[str]) -> int:
    script = REPO_ROOT / name
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
