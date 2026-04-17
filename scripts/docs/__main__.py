#!/usr/bin/env python3
"""Unified entry point for scripts/docs/ commands.

Usage:
    python -m scripts.docs <command> [args...]
    python -m scripts.docs --help

Commands:
    verify             Run the canonical docs verification chain
    check-links        Check documentation links, specs, and configs
    check-drift        Check documentation drift (ports, classes, runtime mirrors, freshness)
    check-docstrings   Check docstring coverage
    check-kpi          Report documentation KPI metrics
    export-matrix-structural-contract Export canonical runtime structural contract for ChEMBL matrix sync
    generate-field-matrix Generate code-derived ChemBL Activity field-matrix artifacts
    generate-pipeline-normalization-matrix Generate code-derived normalization field-matrix artifacts for all pipelines
    build-matrix-dicts Generate ChEMBL matrix inventory and sheet dictionaries
    enrich-matrix-normalization-details Populate exact per-row normalization details in the ChEMBL matrix workbook
    filter-matrix-rows Remove rows from ChEMBL matrix workbook by column value
    normalize-matrix-values Normalize controlled values in ChEMBL matrix workbook
    sync-matrix-structural-policy Sync the ChEMBL matrix workbook with structural Silver policy semantics
    fix-links-auto     Auto-fix broken documentation links
    fix-links-explicit Fix documentation links with explicit rules
    fix-link-warnings  Fix link warnings in specified files
    audit-sentence     Sentence-level documentation audit
    sync-repo-identity Sync active docs/workflows to canonical repo identity
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

COMMANDS: dict[str, str] = {
    "verify": "checks/verify.py",
    "check-links": "checks/check_links.py",
    "check-drift": "checks/check_drift.py",
    "check-docstrings": "checks/check_docstrings.py",
    "check-kpi": "checks/report_docs_kpi.py",
    "export-matrix-structural-contract": "matrix/export_structural_contract.py",
    "generate-field-matrix": "matrix/generate_field_matrix.py",
    "generate-pipeline-normalization-matrix": "matrix/generate_pipeline_normalization_matrix.py",
    "build-matrix-dicts": "matrix/build_matrix_dicts.py",
    "enrich-matrix-normalization-details": "matrix/enrich_normalization_details.py",
    "filter-matrix-rows": "matrix/filter_rows.py",
    "normalize-matrix-values": "matrix/normalize_values.py",
    "sync-matrix-structural-policy": "matrix/sync_structural_policy.py",
    "fix-links-auto": "fixers/fix_links_auto.py",
    "fix-links-explicit": "fixers/fix_links_explicit.py",
    "fix-link-warnings": "fixers/link_warnings.py",
    "audit-sentence": "fixers/sentence_audit.py",
    "sync-repo-identity": "fixers/repo_identity.py",
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
