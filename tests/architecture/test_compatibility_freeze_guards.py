"""Compatibility-freeze guardrails for shim imports and symbols."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = ROOT / "src"
TESTS_ROOT = ROOT / "tests"
LEGACY_DATASOURCE_FACTORY_MODULE = "bioetl.composition.factories.datasource.factory"

TRANSFORMER_DEPENDENCY_SHIM = (
    "bioetl.application.core.base_transformer.dependencies"
)
ALLOWED_TRANSFORMER_TEST_FILES = frozenset(
    {
        ROOT
        / "tests"
        / "unit"
        / "application"
        / "core"
        / "test_base_transformer_dependencies_reexport.py",
    }
)

ALLOWED_DATASOURCE_REGISTRY_SRC_FILES = frozenset(
    {
        ROOT / "src" / "bioetl" / "composition" / "factories" / "__init__.py",
        ROOT
        / "src"
        / "bioetl"
        / "composition"
        / "factories"
        / "datasource"
        / "__init__.py",
        ROOT
        / "src"
        / "bioetl"
        / "composition"
        / "factories"
        / "datasource"
        / "_registry_compat.py",
        ROOT
        / "src"
        / "bioetl"
        / "composition"
        / "factories"
        / "datasource"
        / "data_source_factory.py",
        ROOT
        / "src"
        / "bioetl"
        / "composition"
        / "factories"
        / "datasource"
        / "factory.py",
    }
)
ALLOWED_LEGACY_DATASOURCE_FACTORY_SRC_FILES = frozenset()
ALLOWED_LEGACY_DATASOURCE_FACTORY_TEST_FILES = frozenset(
    {
        ROOT / "tests" / "unit" / "composition" / "test_canonical_module_paths.py",
    }
)


def _iter_module_import_violations(
    search_root: Path,
    *,
    module_name: str,
    allowed_files: frozenset[Path],
) -> list[str]:
    violations: list[str] = []
    for py_file in search_root.rglob("*.py"):
        if py_file in allowed_files or "__pycache__" in py_file.parts:
            continue
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        rel_path = py_file.relative_to(ROOT).as_posix()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == module_name:
                violations.append(f"{rel_path}:{node.lineno} imports {module_name}")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == module_name:
                        violations.append(f"{rel_path}:{node.lineno} imports {module_name}")
    return violations


def _iter_symbol_mentions(
    search_root: Path,
    *,
    symbol: str,
    allowed_files: frozenset[Path],
) -> list[str]:
    violations: list[str] = []
    for py_file in search_root.rglob("*.py"):
        if py_file in allowed_files or "__pycache__" in py_file.parts:
            continue
        rel_path = py_file.relative_to(ROOT).as_posix()
        for lineno, line in enumerate(py_file.read_text(encoding="utf-8").splitlines(), 1):
            if symbol in line:
                violations.append(f"{rel_path}:{lineno} mentions {symbol}")
    return violations


def _iter_string_mentions(
    search_root: Path,
    *,
    needle: str,
    allowed_files: frozenset[Path],
) -> list[str]:
    violations: list[str] = []
    for py_file in search_root.rglob("*.py"):
        if py_file in allowed_files or "__pycache__" in py_file.parts:
            continue
        rel_path = py_file.relative_to(ROOT).as_posix()
        for lineno, line in enumerate(py_file.read_text(encoding="utf-8").splitlines(), 1):
            if needle in line:
                violations.append(f"{rel_path}:{lineno} mentions {needle}")
    return violations


@pytest.mark.architecture
def test_transformer_dependency_compat_shim_is_not_used_in_src() -> None:
    """First-party src must use canonical base-transformer dependency types directly."""
    violations = _iter_module_import_violations(
        SRC_ROOT,
        module_name=TRANSFORMER_DEPENDENCY_SHIM,
        allowed_files=frozenset(),
    )
    assert not violations, (
        "base_transformer dependency compatibility shim is still imported from src/:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_transformer_dependency_compat_shim_is_only_used_by_smoke_test() -> None:
    """Ordinary tests must not accumulate new direct imports of dependency shim."""
    violations = _iter_module_import_violations(
        TESTS_ROOT,
        module_name=TRANSFORMER_DEPENDENCY_SHIM,
        allowed_files=ALLOWED_TRANSFORMER_TEST_FILES,
    )
    assert not violations, (
        "base_transformer dependency compatibility shim gained new non-smoke test imports:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_datasource_registry_symbol_is_confined_to_compat_exports_in_src() -> None:
    """New first-party src must use canonical datasource paths, not DataSourceRegistry."""
    violations = _iter_symbol_mentions(
        SRC_ROOT,
        symbol="DataSourceRegistry",
        allowed_files=ALLOWED_DATASOURCE_REGISTRY_SRC_FILES,
    )
    assert not violations, (
        "DataSourceRegistry compatibility surface leaked into first-party src/ beyond "
        "explicit compatibility exports:\n" + "\n".join(violations)
    )


@pytest.mark.architecture
def test_legacy_datasource_factory_module_is_not_used_in_src() -> None:
    """First-party src must use canonical datasource module paths."""
    violations = _iter_module_import_violations(
        SRC_ROOT,
        module_name=LEGACY_DATASOURCE_FACTORY_MODULE,
        allowed_files=ALLOWED_LEGACY_DATASOURCE_FACTORY_SRC_FILES,
    )
    assert not violations, (
        "Legacy datasource.factory module is still imported from src/ beyond the "
        "canonical wrapper:\n" + "\n".join(violations)
    )


@pytest.mark.architecture
def test_legacy_datasource_factory_module_is_only_used_by_compat_tests() -> None:
    """Ordinary tests must not accumulate new direct imports of legacy datasource module."""
    violations = _iter_module_import_violations(
        TESTS_ROOT,
        module_name=LEGACY_DATASOURCE_FACTORY_MODULE,
        allowed_files=ALLOWED_LEGACY_DATASOURCE_FACTORY_TEST_FILES,
    )
    assert not violations, (
        "Legacy datasource.factory module gained new non-compat test imports:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_legacy_datasource_factory_module_string_mentions_are_confined_to_compat_tests() -> None:
    """Ordinary tests must not reintroduce string-based patch targets for legacy datasource module."""
    violations = _iter_string_mentions(
        TESTS_ROOT,
        needle=LEGACY_DATASOURCE_FACTORY_MODULE,
        allowed_files=ALLOWED_LEGACY_DATASOURCE_FACTORY_TEST_FILES
        | frozenset({Path(__file__).resolve()}),
    )
    assert not violations, (
        "Legacy datasource.factory module gained new string-based references in tests:\n"
        + "\n".join(violations)
    )
