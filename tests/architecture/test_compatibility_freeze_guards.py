"""Compatibility-freeze guardrails for shim imports and symbols."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = ROOT / "src"
TESTS_ROOT = ROOT / "tests"
LEGACY_DATASOURCE_FACTORY_MODULE = "bioetl.composition.factories.datasource.factory"
INTERNAL_COMPOSITION_ENTRYPOINT_MODULES = (
    "bioetl.composition._pipeline_execution",
    "bioetl.composition._resource_management",
    "bioetl.composition._services",
)

TRANSFORMER_DEPENDENCY_SHIM = "bioetl.application.core.base_transformer.dependencies"
TRANSFORMER_DEPENDENCY_SHIM_PATH = (
    ROOT
    / "src"
    / "bioetl"
    / "application"
    / "core"
    / "base_transformer"
    / "dependencies.py"
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
ALLOWED_DATASOURCE_REGISTRY_TEST_FILES = frozenset(
    {
        ROOT
        / "tests"
        / "architecture"
        / "test_registry_contracts.py",
        ROOT
        / "tests"
        / "unit"
        / "composition"
        / "factories"
        / "datasource"
        / "test_data_source_registry.py",
        ROOT
        / "tests"
        / "unit"
        / "composition"
        / "test_canonical_module_paths.py",
        ROOT
        / "tests"
        / "unit"
        / "composition"
        / "test_registry_protocol.py",
    }
)
ALLOWED_LEGACY_DATASOURCE_FACTORY_SRC_FILES: frozenset[Path] = frozenset()
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
            if isinstance(node, ast.ImportFrom) and node.module is not None:
                is_absolute_match = node.module == module_name
                is_relative_match = False
                if node.level > 0:
                    module_parts = list(py_file.relative_to(ROOT).with_suffix("").parts)
                    current_package_parts = (
                        module_parts if py_file.stem == "__init__" else module_parts[:-1]
                    )
                    anchor_length = len(current_package_parts) - (node.level - 1)
                    if anchor_length > 0:
                        absolute_module = ".".join(
                            [
                                *current_package_parts[:anchor_length],
                                *node.module.split("."),
                            ]
                        )
                        is_relative_match = absolute_module == module_name
                if is_absolute_match or is_relative_match:
                    violations.append(f"{rel_path}:{node.lineno} imports {module_name}")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == module_name:
                        violations.append(
                            f"{rel_path}:{node.lineno} imports {module_name}"
                        )
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
        for lineno, line in enumerate(
            py_file.read_text(encoding="utf-8").splitlines(), 1
        ):
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
        for lineno, line in enumerate(
            py_file.read_text(encoding="utf-8").splitlines(), 1
        ):
            if needle in line:
                violations.append(f"{rel_path}:{lineno} mentions {needle}")
    return violations


def _iter_imported_symbol_violations(
    search_root: Path,
    *,
    module_names: frozenset[str],
    symbol: str,
    allowed_files: frozenset[Path],
) -> list[str]:
    violations: list[str] = []
    for py_file in search_root.rglob("*.py"):
        if py_file in allowed_files or "__pycache__" in py_file.parts:
            continue
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        rel_path = py_file.relative_to(ROOT).as_posix()
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            if node.module not in module_names:
                continue
            for alias in node.names:
                if alias.name != symbol:
                    continue
                violations.append(
                    f"{rel_path}:{node.lineno} imports {symbol} from {node.module}"
                )
    return violations


@pytest.mark.architecture
def test_transformer_dependency_compat_shim_file_has_been_removed() -> None:
    """Legacy base-transformer dependency shim should no longer exist."""
    assert not TRANSFORMER_DEPENDENCY_SHIM_PATH.exists(), (
        "Legacy base-transformer dependency shim must stay removed: "
        "src/bioetl/application/core/base_transformer/dependencies.py"
    )


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
def test_transformer_dependency_compat_shim_is_not_used_in_tests() -> None:
    """Tests must not keep importing the removed dependency shim."""
    violations = _iter_module_import_violations(
        TESTS_ROOT,
        module_name=TRANSFORMER_DEPENDENCY_SHIM,
        allowed_files=frozenset(),
    )
    assert not violations, (
        "base_transformer dependency compatibility shim must stay removed from tests:\n"
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
def test_datasource_registry_symbol_is_confined_to_compat_tests() -> None:
    """Ordinary tests must not treat DataSourceRegistry as a normal factory API."""
    violations = _iter_imported_symbol_violations(
        TESTS_ROOT,
        module_names=frozenset(
            {
                "bioetl.composition.factories",
                "bioetl.composition.factories.datasource",
                "bioetl.composition.factories.datasource.data_source_factory",
            }
        ),
        symbol="DataSourceRegistry",
        allowed_files=ALLOWED_DATASOURCE_REGISTRY_TEST_FILES,
    )
    assert not violations, (
        "DataSourceRegistry compatibility surface leaked into ordinary tests beyond "
        "explicit compat/contract coverage:\n" + "\n".join(violations)
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
def test_legacy_datasource_factory_module_string_mentions_are_confined_to_compat_tests() -> (
    None
):
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


@pytest.mark.architecture
@pytest.mark.parametrize("module_name", INTERNAL_COMPOSITION_ENTRYPOINT_MODULES)
def test_internal_composition_entrypoint_modules_are_not_imported_in_unit_tests(
    module_name: str,
) -> None:
    """Unit tests must patch public composition.entrypoints instead of internals."""
    violations = _iter_module_import_violations(
        TESTS_ROOT / "unit",
        module_name=module_name,
        allowed_files=frozenset(),
    )
    assert not violations, (
        "Internal composition entrypoint module gained new unit-test imports:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
@pytest.mark.parametrize("module_name", INTERNAL_COMPOSITION_ENTRYPOINT_MODULES)
def test_internal_composition_entrypoint_module_strings_are_not_used_in_unit_tests(
    module_name: str,
) -> None:
    """Unit tests must not reintroduce string patch targets for internal entrypoints."""
    violations = _iter_string_mentions(
        TESTS_ROOT / "unit",
        needle=module_name,
        allowed_files=frozenset(),
    )
    assert not violations, (
        "Internal composition entrypoint module gained new string references in unit tests:\n"
        + "\n".join(violations)
    )
