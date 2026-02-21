#!/usr/bin/env python3
"""Compatibility wrapper for the terminology linter.

Deprecated: use src/tools/scripts/lint_terminology.py instead.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _load_impl():
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root / "src"))
    from tools.scripts import lint_terminology as impl

    return impl


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check BioETL code for terminology violations.",
        epilog="See docs/glossary.md for canonical terminology.",
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help="Files or directories to check",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Enable strict mode (adds docs/configs to checks)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show files being checked (deprecated; ignored).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output violations as JSON",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Deprecated flag (ignored).",
    )
    return parser.parse_args()


def main() -> int:
    impl = _load_impl()
    args = parse_args()

    patterns = list(impl.PYTHON_PATTERNS)
    if args.strict:
        patterns.extend(impl.MARKDOWN_PATTERNS)
        patterns.extend(impl.YAML_PATTERNS)

    combined = impl.LintResult()
    for path in args.paths:
        resolved = path
        if not resolved.is_absolute():
            resolved = Path.cwd() / path
        result = impl.lint_path(resolved, tuple(patterns))
        combined.violations.extend(result.violations)
        combined.files_checked += result.files_checked

    if args.json:
        impl.log_report_json(combined)
    else:
        impl.log_report_text(combined)

    return 1 if combined.total_violations > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
