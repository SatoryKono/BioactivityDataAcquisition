"""Guardrails for internal docs script bootstrap patterns."""

from __future__ import annotations

import pytest

from pathlib import Path


pytestmark = pytest.mark.architecture

INTERNAL_DOCS_MODULES = (
    "scripts/docs/checks/check_docstrings.py",
    "scripts/docs/checks/check_drift.py",
    "scripts/docs/checks/check_links.py",
    "scripts/docs/checks/report_docs_kpi.py",
    "scripts/docs/matrix/build_matrix_dicts.py",
    "scripts/docs/matrix/enrich_normalization_details.py",
    "scripts/docs/matrix/export_structural_contract.py",
    "scripts/docs/matrix/filter_rows.py",
    "scripts/docs/matrix/generate_field_matrix.py",
    "scripts/docs/matrix/generate_pipeline_normalization_matrix.py",
    "scripts/docs/matrix/normalize_values.py",
    "scripts/docs/matrix/structural_contract.py",
    "scripts/docs/matrix/sync_structural_policy.py",
)


def test_internal_docs_modules_use_local_bootstrap_helpers() -> None:
    for relative_path in INTERNAL_DOCS_MODULES:
        source = Path(relative_path).read_text(encoding="utf-8")
        assert "_bootstrap import" in source, relative_path
        assert "Path(__file__).resolve().parents[3]" not in source, relative_path
        assert "repo_root = Path(__file__).resolve()" not in source, relative_path
