"""Core runtime must never depend on repository engineering modules."""

from __future__ import annotations
import ast
from pathlib import Path
import pytest

pytestmark = pytest.mark.architecture


def test_runtime_has_no_engineering_imports() -> None:
    root = Path(__file__).resolve().parents[3]
    violations: list[str] = []
    for path in (root / "src/bioetl").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            modules: list[str] = []
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules = [node.module]
            elif isinstance(node, ast.Call) and node.args:
                function = node.func
                is_loader = (
                    isinstance(function, ast.Name) and function.id == "__import__"
                ) or (
                    isinstance(function, ast.Attribute)
                    and function.attr == "import_module"
                )
                if (
                    is_loader
                    and isinstance(node.args[0], ast.Constant)
                    and isinstance(node.args[0].value, str)
                ):
                    modules = [node.args[0].value]
            for module in modules:
                if module == "scripts" or module.startswith("scripts."):
                    violations.append(
                        f"{path.relative_to(root)}:{node.lineno}:{module}"
                    )
    assert violations == []

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
    source = repo_root / "scripts/engineering/quality" / filename
    tree = ast.parse(source.read_text(encoding="utf-8"))
    imports = {
        node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
    }
    assert dependency in imports, (
        f"QM-07 blocker changed in {filename}; re-evaluate installed-wheel isolation"
    )
