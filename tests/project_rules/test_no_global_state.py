"""Tests for absence of global mutable state in infrastructure.

These tests ensure that the codebase follows the dependency injection pattern
and does not rely on global mutable state for configuration and providers.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterable

import pytest

from tests.project_rules.conftest import iter_python_files


def _find_global_provider_state(content: str) -> list[str]:
    """Find global provider state variables in Python source.

    Args:
        content: Python source code.

    Returns:
        List of global state variable names found.
    """
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return []

    violations = []
    for node in ast.walk(tree):
        # Check for annotated assignments like: _PROVIDER: Type | None = None
        if isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                name = node.target.id
                if name.startswith("_") and "PROVIDER" in name.upper():
                    violations.append(name)

        # Check for simple assignments like: _PROVIDER = None
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    name = target.id
                    if name.startswith("_") and "PROVIDER" in name.upper():
                        violations.append(name)

    return violations


def test_no_global_schema_provider_in_infrastructure(bioetl_root: Path) -> None:
    """Verify infrastructure has no global schema provider state."""
    loader_path = bioetl_root / "infrastructure" / "config" / "loader.py"

    assert loader_path.exists(), f"File not found: {loader_path}"

    content = loader_path.read_text()
    violations = _find_global_provider_state(content)

    assert not violations, (
        f"Found global state variables in loader.py: {violations}. "
        "Global state is prohibited - use dependency injection instead."
    )


def test_no_global_provider_references_in_application(bioetl_root: Path) -> None:
    """Verify application layer doesn't use global provider state."""
    application_dir = bioetl_root / "application"

    violations: list[str] = []
    for py_file in iter_python_files(application_dir):
        content = py_file.read_text()

        # Check for direct references to global state
        if "_SCHEMA_CONTRACT_PROVIDER" in content:
            violations.append(f"{py_file}: references _SCHEMA_CONTRACT_PROVIDER")

        # Check for deprecated global state functions
        deprecated_functions = [
            "set_schema_contract_provider",
            "get_schema_contract_provider",
            "clear_schema_contract_provider",
            "reset_schema_contract_provider",
            "_set_provider_internal",
            "_clear_provider_internal",
        ]
        for func_name in deprecated_functions:
            if func_name in content:
                # Skip if it's just a type annotation or comment
                if f"import {func_name}" in content or f"from " in content:
                    violations.append(f"{py_file}: imports deprecated {func_name}")

    assert not violations, (
        f"Found global state references in application layer:\n"
        + "\n".join(violations)
    )


def test_no_global_state_setter_in_bootstrap(bioetl_root: Path) -> None:
    """Verify bootstrap_factory doesn't use global state setters."""
    bootstrap_factory_path = (
        bioetl_root / "interfaces" / "bootstrap_factory.py"
    )

    assert bootstrap_factory_path.exists(), f"File not found: {bootstrap_factory_path}"

    content = bootstrap_factory_path.read_text()

    deprecated_imports = [
        "_set_provider_internal",
        "_clear_provider_internal",
        "set_schema_contract_provider",
    ]

    violations = []
    for func_name in deprecated_imports:
        if func_name in content:
            violations.append(func_name)

    assert not violations, (
        f"bootstrap_factory.py still references deprecated functions: {violations}. "
        "Provider injection via global state is removed."
    )


def test_infrastructure_loader_exports_only_di_api(bioetl_root: Path) -> None:
    """Verify loader.py __all__ contains only DI-based API."""
    loader_path = bioetl_root / "infrastructure" / "config" / "loader.py"

    content = loader_path.read_text()
    tree = ast.parse(content)

    # Find __all__ assignment
    all_exports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    if isinstance(node.value, ast.List):
                        for elt in node.value.elts:
                            if isinstance(elt, ast.Constant):
                                all_exports.append(elt.value)

    deprecated_exports = {
        "set_schema_contract_provider",
        "get_schema_contract_provider",
        "clear_schema_contract_provider",
        "reset_schema_contract_provider",
        "create_schema_contract_loader",
        "_set_provider_internal",
        "_clear_provider_internal",
    }

    found_deprecated = set(all_exports) & deprecated_exports

    assert not found_deprecated, (
        f"loader.py __all__ still exports deprecated functions: {found_deprecated}. "
        "Remove deprecated exports from public API."
    )
