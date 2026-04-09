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
    "verify": "verify_docs.py",
    "check-links": "check_doc_links.py",
    "check-drift": "check_doc_drift.py",
    "check-docstrings": "check_docstring_coverage.py",
    "check-kpi": "report_docs_kpi.py",
    "export-matrix-structural-contract": "export_chembl_matrix_structural_contract.py",
    "generate-field-matrix": "generate_chembl_activity_field_matrix.py",
    "generate-pipeline-normalization-matrix": "generate_pipeline_normalization_field_matrix.py",
    "build-matrix-dicts": "generate_chembl_matrix_dictionaries.py",
    "enrich-matrix-normalization-details": "enrich_chembl_matrix_normalization_details.py",
    "filter-matrix-rows": "filter_chembl_matrix_rows.py",
    "normalize-matrix-values": "normalize_chembl_matrix_workbook.py",
    "sync-matrix-structural-policy": "sync_chembl_matrix_structural_policy.py",
    "fix-links-auto": "fix_doc_links_auto.py",
    "fix-links-explicit": "fix_doc_links_explicit.py",
    "fix-link-warnings": "fix_link_warnings.py",
    "audit-sentence": "sentence_doc_audit.py",
    "sync-repo-identity": "sync_repo_identity.py",
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
