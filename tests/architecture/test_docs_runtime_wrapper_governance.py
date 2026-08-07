# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Guardrails for retired top-level ``scripts/docs`` compatibility shims (#8043)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.helpers.git_index_scan import git_grep_fixed

pytestmark = pytest.mark.architecture

RETIRED_DOCS_SHIMS = (
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
    "scripts/docs/_compat_shim.py",
    "scripts/docs/checks/_bootstrap.py",
    "scripts/docs/matrix/_bootstrap.py",
)
ROOT = Path(__file__).resolve().parents[2]
SCRIPT_LIFECYCLE = ROOT / "configs" / "quality" / "scripts_lifecycle_registry.json"
ACTIVE_DIRECT_DISPATCH_ROOTS = (
    ".github",
    "docs/00-project",
    "docs/01-requirements",
    "docs/02-architecture",
    "docs/03-guides",
    "docs/04-reference",
    "docs/05-operations",
    "scripts",
)
SKIPPED_DIRECT_DISPATCH_PATH_PARTS = {
    "99-archive",
    "reports",
    "plans",
}
RETIRED_COMPATIBILITY_WRAPPERS = {
    "scripts/ai/vibe/__main__.py",
    *RETIRED_DOCS_SHIMS,
}


def test_docs_top_level_shims_are_removed() -> None:
    lingering = [path for path in RETIRED_DOCS_SHIMS if (ROOT / path).exists()]
    assert not lingering, (
        "Top-level scripts/docs compatibility shims must stay removed (#8043):\n"
        + "\n".join(lingering)
    )


def test_docs_direct_file_dispatch_does_not_regrow_in_active_surfaces() -> None:
    """Active docs/workflows should use module dispatch instead of docs shim files."""
    matches = git_grep_fixed(
        root=ROOT,
        patterns=("python scripts/docs/", "python3 scripts/docs/"),
        paths=ACTIVE_DIRECT_DISPATCH_ROOTS,
        suffixes=(".md", ".py", ".yml", ".yaml"),
    )
    violations = {
        match.path
        for match in matches
        if not SKIPPED_DIRECT_DISPATCH_PATH_PARTS.intersection(Path(match.path).parts)
    }
    assert not violations, (
        "Active surfaces must not document direct-file scripts/docs dispatch; "
        "use `python -m scripts.docs <command>` instead:\n"
        + "\n".join(sorted(violations))
    )


def test_retired_script_compatibility_wrappers_stay_absent() -> None:
    """Retired script compatibility wrappers must not re-enter lifecycle debt."""
    payload = json.loads(SCRIPT_LIFECYCLE.read_text(encoding="utf-8"))
    entries = payload["entries"]
    assert isinstance(entries, dict)

    lingering_files = [
        path for path in RETIRED_COMPATIBILITY_WRAPPERS if (ROOT / path).exists()
    ]
    lingering_registry_rows = sorted(RETIRED_COMPATIBILITY_WRAPPERS & set(entries))

    assert not lingering_files, (
        "Retired script compatibility wrappers must stay removed:\n"
        + "\n".join(lingering_files)
    )
    assert not lingering_registry_rows, (
        "Retired script compatibility wrappers must not remain lifecycle debt:\n"
        + "\n".join(lingering_registry_rows)
    )


def test_docs_common_bootstrap_exists() -> None:
    path = ROOT / "scripts/docs/common/bootstrap.py"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "ensure_repo_imports" in text
    assert "PROJECT_ROOT" in text
    assert "DOCS_DIR" in text
