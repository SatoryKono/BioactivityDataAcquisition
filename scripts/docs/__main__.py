#!/usr/bin/env python3
"""Unified entry point for scripts/docs/ commands.

Usage:
    python -m scripts.docs <command> [args...]
    python -m scripts.docs --help

Commands:
    verify             Run the canonical docs verification chain
    build-site         Build the MkDocs site through the packaged build entrypoint
    check-links        Check documentation links, specs, and configs
    check-drift        Check documentation drift (ports, classes, bounded narrative parity, runtime mirrors, freshness)
    check-docstrings   Check docstring coverage
    check-kpi          Report documentation KPI metrics
    generate-cleanup-inventory Generate/check documentation cleanup inventory
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
    passports          Generate/check pipeline and workflow passports
    rename-passport-paths Preview/apply/check passport Markdown kebab-case paths
"""

from __future__ import annotations

from pathlib import Path

from scripts.engineering.common.cli_dispatch import dispatch_cli, module_command

COMMANDS = {
    "verify": "scripts.docs.checks.verify",
    "build-site": "scripts.docs.build.mkdocs_build",
    "check-links": "scripts.docs.checks.check_links",
    "check-drift": "scripts.docs.checks.check_drift",
    "check-docstrings": "scripts.docs.checks.check_docstrings",
    "check-kpi": "scripts.docs.checks.report_docs_kpi",
    "generate-cleanup-inventory": "scripts.docs.checks.documentation_cleanup_inventory",
    "export-matrix-structural-contract": "scripts.docs.matrix.export_structural_contract",
    "generate-field-matrix": "scripts.docs.matrix.generate_field_matrix",
    "generate-pipeline-normalization-matrix": "scripts.docs.matrix.generate_pipeline_normalization_matrix",
    "build-matrix-dicts": "scripts.docs.matrix.build_matrix_dicts",
    "enrich-matrix-normalization-details": "scripts.docs.matrix.enrich_normalization_details",
    "filter-matrix-rows": "scripts.docs.matrix.filter_rows",
    "normalize-matrix-values": "scripts.docs.matrix.normalize_values",
    "sync-matrix-structural-policy": "scripts.docs.matrix.sync_structural_policy",
    "fix-links-auto": "scripts.docs.fixers.fix_links_auto",
    "fix-links-explicit": "scripts.docs.fixers.fix_links_explicit",
    "fix-link-warnings": "scripts.docs.fixers.link_warnings",
    "audit-sentence": "scripts.docs.fixers.sentence_audit",
    "sync-repo-identity": "scripts.docs.fixers.repo_identity",
    "passports": "scripts.docs.passports.cli",
    "rename-passport-paths": (
        "scripts.docs.passports.rename_underscore_to_hyphen"
    ),
}
COMMAND_SPECS = {
    name: module_command(module_name) for name, module_name in COMMANDS.items()
}
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
