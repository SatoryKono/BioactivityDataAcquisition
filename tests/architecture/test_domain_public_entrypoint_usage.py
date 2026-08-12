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
"""Guardrails for domain public compatibility entrypoints over split internals."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

SPLIT_CONFIG_MODULES = frozenset(
    {
        "bioetl.domain.composite.config_models",
        "bioetl.domain.composite.config_merge",
        "bioetl.domain.composite.config_runtime",
        "bioetl.domain.composite.config_dq",
        "bioetl.domain.composite.config_validators",
        "bioetl.domain.composite.config_composite_serialization",
        "bioetl.domain.composite.config_composite_validation",
    }
)
SPLIT_VALUE_OBJECT_MODULES = frozenset(
    {
        "bioetl.domain.value_objects.activity_concentration",
        "bioetl.domain.value_objects.activity_type",
        "bioetl.domain.value_objects.pchembl_value",
    }
)
ALLOWED_CONFIG_TEST_FILES = frozenset(
    {
        ROOT
        / "tests"
        / "unit"
        / "domain"
        / "composite"
        / "test_composite_config_facade.py",
        ROOT
        / "tests"
        / "unit"
        / "domain"
        / "composite"
        / "test_composite_config_edge_cases.py",
        ROOT
        / "tests"
        / "unit"
        / "domain"
        / "composite"
        / "_config_internal_test_support.py",
    }
)
ALLOWED_VALUE_OBJECT_TEST_FILES = frozenset(
    {
        ROOT
        / "tests"
        / "unit"
        / "domain"
        / "value_objects"
        / "test_value_object_facade_reexports.py",
    }
)


def _iter_import_records(
    ast_cache: dict[Path, ast.Module],
    *,
    module_names: frozenset[str],
) -> list[tuple[Path, int, str]]:
    records: list[tuple[Path, int, str]] = []
    for py_file, tree in sorted(ast_cache.items()):
        for node in ast.walk(tree):
            records.extend(_iter_node_import_records(py_file, node, module_names))
    return records


def _iter_node_import_records(
    py_file: Path,
    node: ast.AST,
    module_names: frozenset[str],
) -> list[tuple[Path, int, str]]:
    if isinstance(node, ast.ImportFrom) and node.module in module_names:
        return [(py_file, node.lineno, node.module)]
    if isinstance(node, ast.Import):
        return [
            (py_file, node.lineno, alias.name)
            for alias in node.names
            if alias.name in module_names
        ]
    return []


def _format_prefix_confined_violations(
    records: list[tuple[Path, int, str]],
    *,
    allowed_prefix: Path,
    allowed_test_files: frozenset[Path] = frozenset(),
) -> list[str]:
    violations: list[str] = []
    for py_file, lineno, module_name in records:
        if py_file in allowed_test_files:
            continue
        if py_file.is_relative_to(allowed_prefix):
            continue
        rel_path = py_file.relative_to(ROOT).as_posix()
        violations.append(f"{rel_path}:{lineno} imports {module_name}")
    return violations


@pytest.mark.architecture
def test_split_composite_config_modules_are_confined_to_domain_composite(
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """First-party code outside domain.composite must use the public config entrypoint."""
    violations = _format_prefix_confined_violations(
        _iter_import_records(source_ast_cache, module_names=SPLIT_CONFIG_MODULES),
        allowed_prefix=ROOT / "src" / "bioetl" / "domain" / "composite",
    )
    assert not violations, (
        "Split composite-config internals leaked outside domain/composite; use "
        "bioetl.domain.composite.config instead:\n" + "\n".join(violations)
    )


@pytest.mark.architecture
def test_split_composite_config_modules_are_only_used_by_dedicated_tests(
    test_ast_cache: dict[Path, ast.Module],
) -> None:
    """Split config internals must stay confined to dedicated composite-config tests."""
    violations = _format_prefix_confined_violations(
        _iter_import_records(test_ast_cache, module_names=SPLIT_CONFIG_MODULES),
        allowed_prefix=ROOT / "tests" / "__never__",
        allowed_test_files=ALLOWED_CONFIG_TEST_FILES,
    )
    assert not violations, (
        "Split composite-config internals gained new non-dedicated test imports:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_split_value_object_modules_are_confined_to_domain_value_objects(
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """First-party code outside domain.value_objects must use the public facades."""
    violations = _format_prefix_confined_violations(
        _iter_import_records(source_ast_cache, module_names=SPLIT_VALUE_OBJECT_MODULES),
        allowed_prefix=ROOT / "src" / "bioetl" / "domain" / "value_objects",
    )
    assert not violations, (
        "Split value-object internals leaked outside domain/value_objects; use "
        "public entrypoints instead:\n" + "\n".join(violations)
    )


@pytest.mark.architecture
def test_split_value_object_modules_are_not_imported_from_tests(
    test_ast_cache: dict[Path, ast.Module],
) -> None:
    """Tests should exercise public value-object facades, not split internals."""
    violations = _format_prefix_confined_violations(
        _iter_import_records(test_ast_cache, module_names=SPLIT_VALUE_OBJECT_MODULES),
        allowed_prefix=ROOT / "tests" / "__never__",
        allowed_test_files=ALLOWED_VALUE_OBJECT_TEST_FILES,
    )
    assert not violations, (
        "Split value-object internals gained direct test imports:\n"
        + "\n".join(violations)
    )
