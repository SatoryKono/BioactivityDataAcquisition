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
"""Architecture guardrails for rollout/hash routing purity."""

from __future__ import annotations

import pytest

import ast
from pathlib import Path


pytestmark = pytest.mark.architecture


def _runtime_imports(module_path: Path) -> list[str]:
    """Return runtime imports, excluding TYPE_CHECKING-only blocks."""
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    imports: list[str] = []

    def visit_node(node: ast.AST, *, in_type_checking: bool = False) -> None:
        next_type_checking = in_type_checking
        if isinstance(node, ast.If):
            test = node.test
            if isinstance(test, ast.Name) and test.id == "TYPE_CHECKING":
                next_type_checking = True

        if not next_type_checking:
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imports.append(node.module)

        for child in ast.iter_child_nodes(node):
            visit_node(child, in_type_checking=next_type_checking)

    visit_node(tree)
    return imports


def test_rollout_and_hash_routing_application_domain_modules_stay_infra_free(
    src_dir: Path,
) -> None:
    """Rollout/hash routing in application+domain must stay free of runtime infra imports."""
    guarded_modules = [
        src_dir / "bioetl" / "application" / "core" / "config.py",
        src_dir
        / "bioetl"
        / "application"
        / "core"
        / "record_normalization_processor.py",
        src_dir / "bioetl" / "domain" / "types" / "contract_rollout.py",
        src_dir / "bioetl" / "domain" / "types" / "gold_schema_policy.py",
    ]

    violations: list[str] = []
    for module_path in guarded_modules:
        runtime_imports = _runtime_imports(module_path)
        bad_imports = sorted(
            imported
            for imported in runtime_imports
            if imported == "bioetl.infrastructure"
            or imported.startswith("bioetl.infrastructure.")
        )
        if bad_imports:
            rel_path = module_path.relative_to(src_dir)
            violations.append(f"{rel_path}: {', '.join(bad_imports)}")

    assert not violations, (
        "Rollout/hash routing must not pull infrastructure runtime dependencies "
        "into application/domain modules.\n"
        "Keep config loading, validators, and storage wiring in composition.\n"
        "Violations:\n" + "\n".join(f"  - {violation}" for violation in violations)
    )
