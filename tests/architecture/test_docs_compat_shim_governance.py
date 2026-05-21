"""Guardrails for top-level ``scripts/docs`` compatibility shims."""

from __future__ import annotations

import json
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
ROOT = Path(__file__).resolve().parents[2]
SCRIPT_LIFECYCLE = ROOT / "configs" / "quality" / "scripts_lifecycle_registry.json"
ACTIVE_DIRECT_DISPATCH_ROOTS = (
    ROOT / ".github",
    ROOT / "docs" / "00-project",
    ROOT / "docs" / "01-requirements",
    ROOT / "docs" / "02-architecture",
    ROOT / "docs" / "03-guides",
    ROOT / "docs" / "04-reference",
    ROOT / "docs" / "05-operations",
    ROOT / "scripts",
)
SKIPPED_DIRECT_DISPATCH_PATH_PARTS = {
    "99-archive",
    "reports",
    "plans",
}
COMPATIBILITY_LIFECYCLE_WRAPPERS = {
    "scripts/docs/_compat_shim.py",
}
RETIRED_COMPATIBILITY_WRAPPERS = {
    "scripts/ai/vibe/__main__.py",
}


def test_docs_shims_delegate_to_shared_compat_helper() -> None:
    for relative_path in DOCS_SHIMS:
        source = Path(relative_path).read_text(encoding="utf-8")
        assert "_compat_shim" in source, relative_path
        assert "globals().update(" not in source, relative_path
        assert "exec(compile(" not in source, relative_path
        assert "Path(__file__).resolve().parents[2]" not in source, relative_path


def _iter_active_text_files() -> list[Path]:
    files: list[Path] = []
    for root in ACTIVE_DIRECT_DISPATCH_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if any(part in SKIPPED_DIRECT_DISPATCH_PATH_PARTS for part in path.parts):
                continue
            if path.suffix not in {".md", ".py", ".yml", ".yaml"}:
                continue
            files.append(path)
    return files


def test_docs_direct_file_dispatch_does_not_regrow_in_active_surfaces() -> None:
    """Active docs/workflows should use module dispatch instead of docs shim files."""
    violations: list[str] = []
    for path in _iter_active_text_files():
        text = path.read_text(encoding="utf-8")
        if "python scripts/docs/" not in text and "python3 scripts/docs/" not in text:
            continue
        violations.append(path.relative_to(ROOT).as_posix())

    assert not violations, (
        "Active surfaces must not document direct-file scripts/docs dispatch; "
        "use `python -m scripts.docs <command>` instead:\n"
        + "\n".join(sorted(violations))
    )


def test_script_compatibility_wrappers_have_lifecycle_rows() -> None:
    """Retained script compatibility wrappers must stay visible in lifecycle policy."""
    payload = json.loads(SCRIPT_LIFECYCLE.read_text(encoding="utf-8"))
    entries = payload["entries"]
    assert isinstance(entries, dict)

    missing = COMPATIBILITY_LIFECYCLE_WRAPPERS - set(entries)
    assert not missing, (
        "Compatibility wrappers missing scripts lifecycle rows:\n"
        + "\n".join(sorted(missing))
    )
    for path in COMPATIBILITY_LIFECYCLE_WRAPPERS:
        row = entries[path]
        assert row["decision"] in {"compatibility_wrapper", "internal_helper_orphan"}
        assert row["review_by"] >= "2026-07-15"
        assert "Retain" in row["next_step"]


def test_retired_script_compatibility_wrappers_stay_absent() -> None:
    """Retired script compatibility wrappers must not re-enter lifecycle debt."""
    payload = json.loads(SCRIPT_LIFECYCLE.read_text(encoding="utf-8"))
    entries = payload["entries"]
    assert isinstance(entries, dict)

    lingering_files = [
        path
        for path in RETIRED_COMPATIBILITY_WRAPPERS
        if (ROOT / path).exists()
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
