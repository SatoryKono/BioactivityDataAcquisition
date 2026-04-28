#!/usr/bin/env python3
"""Unified entry point for scripts/ops/data commands.

Usage:
    python -m scripts.ops.data <command> [args...]
    python -m scripts.ops.data --help

Commands:
    check-delta            Check Delta Lake integrity
    check-data-dir         Validate data directory structure
    vacuum                 Vacuum Delta tables
    checksums              Generate/verify file checksums
    report-null-fields     Extract null field statistics
    report-content-hash    Generate content hash comparison report
"""

from pathlib import Path

from scripts._command_dispatch import dispatch_script_command

COMMANDS: dict[str, str] = {
    "check-delta": "check_delta_integrity.py",
    "check-data-dir": "validate_data_dir.py",
    "vacuum": "vacuum_delta.py",
    "checksums": "verify_checksums.py",
    "report-null-fields": "extract_null_fields.py",
    "report-content-hash": "generate_content_hash_comparison_report.py",
}

_DIR = Path(__file__).parent


def main(argv: list[str] | None = None) -> int:
    return dispatch_script_command(
        doc=__doc__,
        commands=COMMANDS,
        base_dir=_DIR,
        argv=argv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
