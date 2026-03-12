#!/usr/bin/env python3
"""Unified entry point for scripts/docs/ commands.

Usage:
    python -m scripts.docs <command> [args...]
    python -m scripts.docs --help

Commands:
    check-links        Check documentation links, specs, and configs
    check-drift        Check documentation drift (ports, classes)
    check-docstrings   Check docstring coverage
    check-kpi          Report documentation KPI metrics
    fix-links-auto     Auto-fix broken documentation links
    fix-links-explicit Fix documentation links with explicit rules
    fix-link-warnings  Fix link warnings in specified files
    audit-sentence     Sentence-level documentation audit
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

COMMANDS: dict[str, str] = {
    "check-links": "check_doc_links.py",
    "check-drift": "check_doc_drift.py",
    "check-docstrings": "check_docstring_coverage.py",
    "check-kpi": "report_docs_kpi.py",
    "fix-links-auto": "fix_doc_links_auto.py",
    "fix-links-explicit": "fix_doc_links_explicit.py",
    "fix-link-warnings": "fix_link_warnings.py",
    "audit-sentence": "sentence_doc_audit.py",
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
