"""Guardrails for top-level ``scripts/docs`` compatibility shims."""

from __future__ import annotations

from pathlib import Path


DOCS_SHIMS = (
    "scripts/docs/check_doc_drift.py",
    "scripts/docs/check_docstring_coverage.py",
    "scripts/docs/chembl_matrix_structural_contract.py",
    "scripts/docs/enrich_chembl_matrix_normalization_details.py",
    "scripts/docs/export_chembl_matrix_structural_contract.py",
    "scripts/docs/filter_chembl_matrix_rows.py",
    "scripts/docs/fix_doc_links_auto.py",
    "scripts/docs/fix_doc_links_explicit.py",
    "scripts/docs/fix_link_warnings.py",
    "scripts/docs/generate_chembl_activity_field_matrix.py",
    "scripts/docs/generate_chembl_matrix_dictionaries.py",
    "scripts/docs/generate_pipeline_normalization_field_matrix.py",
    "scripts/docs/normalize_chembl_matrix_workbook.py",
    "scripts/docs/report_docs_kpi.py",
    "scripts/docs/sentence_doc_audit.py",
    "scripts/docs/sync_chembl_matrix_structural_policy.py",
    "scripts/docs/sync_repo_identity.py",
    "scripts/docs/verify_docs.py",
)


def test_docs_shims_delegate_to_shared_compat_helper() -> None:
    for relative_path in DOCS_SHIMS:
        source = Path(relative_path).read_text(encoding="utf-8")
        assert "_compat_shim" in source, relative_path
        assert "globals().update(" not in source, relative_path
        assert "exec(compile(" not in source, relative_path
        assert "Path(__file__).resolve().parents[2]" not in source, relative_path
