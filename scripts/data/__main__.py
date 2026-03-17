#!/usr/bin/env python3
"""Unified entry point for scripts/data/ commands.

Usage:
    python -m scripts.data <command> [args...]
    python -m scripts.data --help

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

COMMANDS: dict[str, str] = {
    "check-vcr-placement": "check_root_vcr_cassettes.py",
    "check-vcr-naming": "check_vcr_filename_policy.py",
    "check-vcr-secrets": "check_vcr_secrets.py",
    "check-delta": "check_delta_integrity.py",
    "check-data-dir": "validate_data_dir.py",
    "vacuum": "vacuum_delta.py",
    "checksums": "verify_checksums.py",
    "dq-baseline": "dq_baseline_update.py",
    "report-null-fields": "extract_null_fields.py",
    "report-content-hash": "generate_content_hash_comparison_report.py",
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
