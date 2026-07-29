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
"""Architecture guardrails for config-root normalization."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = ROOT / "src" / "bioetl"
CANONICAL_CONFIG_ROOT_HELPER = SRC_ROOT / "infrastructure" / "config" / "config_root.py"
EFFECTIVE_CONFIG_SOURCE_REF_BUILDER = (
    ROOT
    / "src"
    / "bioetl"
    / "composition"
    / "runtime_builders"
    / "_effective_config_artifact_builder_support.py"
)


def _contains_parents_reference(node: ast.AST) -> bool:
    return any(
        isinstance(child, ast.Attribute) and child.attr == "parents"
        for child in ast.walk(node)
    )


def _contains_configs_literal(node: ast.AST) -> bool:
    return any(
        isinstance(child, ast.Constant) and child.value == "configs"
        for child in ast.walk(node)
    )


def _contains_name(node: ast.AST, names: set[str]) -> bool:
    return any(
        isinstance(child, ast.Name) and child.id in names for child in ast.walk(node)
    )


def _iter_assigned_names(target: ast.AST) -> tuple[str, ...]:
    if isinstance(target, ast.Name):
        return (target.id,)
    if isinstance(target, (ast.Tuple, ast.List)):
        return tuple(
            name for element in target.elts for name in _iter_assigned_names(element)
        )
    return ()


def _parent_derived_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and _contains_parents_reference(node.value):
            for target in node.targets:
                names.update(_iter_assigned_names(target))
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            if _contains_parents_reference(node.value):
                names.update(_iter_assigned_names(node.target))
    return names


def test_effective_config_source_refs_use_canonical_config_root_anchor() -> None:
    """Effective-config source refs must not infer repo root from source layout."""
    text = EFFECTIVE_CONFIG_SOURCE_REF_BUILDER.read_text(encoding="utf-8")

    assert "resolve_configs_root().parent" in text
    assert "Path(__file__).resolve().parents" not in text


def test_runtime_config_discovery_does_not_use_source_parent_arithmetic(
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """Runtime code must use config-root helpers instead of parents[N] / configs."""
    violations: list[str] = []

    for path, tree in sorted(source_ast_cache.items()):
        if path == CANONICAL_CONFIG_ROOT_HELPER:
            continue
        parent_names = _parent_derived_names(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.BinOp):
                continue
            if not _contains_configs_literal(node):
                continue
            if _contains_parents_reference(node) or _contains_name(node, parent_names):
                rel_path = path.relative_to(ROOT).as_posix()
                violations.append(f"{rel_path}:{node.lineno}")

    assert not violations, (
        "Runtime config discovery must use "
        "bioetl.infrastructure.config.config_root helpers instead of source "
        "layout parent arithmetic:\n" + "\n".join(violations)
    )
