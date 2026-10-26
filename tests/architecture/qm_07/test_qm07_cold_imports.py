"""Source evidence for the QM-07 installed-runtime BLOCKED status.

These dependencies must be moved out of core before claiming wheel isolation.
This inventory documents the blocker; it does not prove installed-wheel imports.
"""

import ast
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    ("filename", "dependency"),
    [
        (
            "architecture_quality_scorecard.py",
            "scripts.engineering.ci.validate_registry_dq_refs",
        ),
        (
            "architecture_quality_scorecard.py",
            "scripts.engineering.qa.report_adr_enforcement_matrix",
        ),
        (
            "architecture_quality_scorecard.py",
            "scripts.engineering.qa.report_lazy_import_inventory",
        ),
        ("debt_scorecard.py", "scripts.engineering.common.repo_paths"),
        ("exemptions_registry_access.py", "scripts.engineering.common.repo_paths"),
    ],
)
def test_installed_runtime_blocker_is_source_bound(
    filename: str,
    dependency: str,
) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    source = repo_root / "src/bioetl/infrastructure/quality" / filename
    tree = ast.parse(source.read_text(encoding="utf-8"))
    imports = {
        node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
    }
    assert dependency in imports, (
        f"QM-07 blocker changed in {filename}; re-evaluate installed-wheel isolation"
    )
