"""Tests for absence of global mutable state in infrastructure.

These tests ensure that the codebase follows the dependency injection pattern
and does not rely on global mutable state for configuration and providers.
"""

from __future__ import annotations

import ast
from pathlib import Path

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
                if f"import {func_name}" in content or "from " in content:
                    violations.append(f"{py_file}: imports deprecated {func_name}")

    assert (
        not violations
    ), "Found global state references in application layer:\n" + "\n".join(violations)


def test_no_global_state_setter_in_bootstrap(bioetl_root: Path) -> None:
    """Verify bootstrap_factory doesn't use global state setters."""
    bootstrap_factory_path = bioetl_root / "interfaces" / "bootstrap_factory.py"

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
        "bootstrap_factory.py still references deprecated functions: "
        f"{violations}. Provider injection via global state is removed."
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


def test_no_global_provider_registry_in_domain(bioetl_root: Path) -> None:
    """Verify domain has no global provider registry state.

    The domain layer should not contain any global mutable state for
    provider registry. All registry access should go through DI
    via CompositionRoot or explicit injection.
    """
    provider_registry_path = bioetl_root / "domain" / "provider_registry.py"

    assert provider_registry_path.exists(), f"File not found: {provider_registry_path}"

    content = provider_registry_path.read_text()

    # Check for global state pattern
    assert "_PROVIDER_REGISTRY" not in content, (
        "domain/provider_registry.py should not contain global "
        "state _PROVIDER_REGISTRY"
    )

    # Check for deprecated functions (as actual function definitions,
    # not in __getattr__). We allow __getattr__ to reference these names
    # for backward-compat error messages.
    tree = ast.parse(content)

    deprecated_functions = {
        "set_provider_registry",
        "get_provider_registry",
        "default_provider_registry",
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in deprecated_functions:
            pytest.fail(
                "domain/provider_registry.py contains deprecated function: "
                f"{node.name}. Global state functions should be removed from "
                "domain layer."
            )


def test_domain_provider_registry_exports_no_deprecated_api(bioetl_root: Path) -> None:
    """Verify domain/provider_registry.py __all__ has no deprecated exports."""
    provider_registry_path = bioetl_root / "domain" / "provider_registry.py"

    content = provider_registry_path.read_text()
    tree = ast.parse(content)

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
        "set_provider_registry",
        "get_provider_registry",
        "default_provider_registry",
        "_PROVIDER_REGISTRY",
    }

    found_deprecated = set(all_exports) & deprecated_exports

    assert not found_deprecated, (
        "domain/provider_registry.py __all__ still exports deprecated: "
        f"{found_deprecated}. Remove deprecated exports from public API."
    )


def test_no_class_level_singleton_holders(bioetl_root: Path) -> None:
    """Verify infrastructure doesn't use class-level singleton holder pattern.

    The _RegistryHolder pattern with class-level _instance attribute
    is an anti-pattern that should be replaced with factory functions.
    """
    violations: list[str] = []

    # Check for _RegistryHolder or similar holder classes
    holder_pattern_names = {"_RegistryHolder", "_Holder", "_InstanceHolder"}

    for py_file in iter_python_files(bioetl_root / "infrastructure"):
        try:
            content = py_file.read_text()
            tree = ast.parse(content)
        except (SyntaxError, UnicodeDecodeError):
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if node.name in holder_pattern_names:
                    violations.append(
                        f"{py_file}: contains singleton holder class {node.name}"
                    )

    assert not violations, (
        "Found singleton holder classes in infrastructure:\n"
        + "\n".join(violations)
        + "\nUse factory functions instead."
    )


def test_no_module_level_context_variable_in_application_context(
    bioetl_root: Path,
) -> None:
    """Verify application_context.py doesn't have module-level _context variable.

    The application_context module should delegate to context_manager.py
    which uses ContextVar for thread-safe context management.
    """
    app_context_path = bioetl_root / "interfaces" / "application_context.py"

    assert app_context_path.exists(), f"File not found: {app_context_path}"

    content = app_context_path.read_text()
    tree = ast.parse(content)

    # Check for module-level _context variable
    for node in tree.body:
        if isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == "_context":
                pytest.fail(
                    "application_context.py should not have module-level _context. "
                    "Context management is delegated to context_manager.py."
                )

        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "_context":
                    pytest.fail(
                        "application_context.py should not have module-level _context. "
                        "Context management is delegated to context_manager.py."
                    )


def test_application_context_delegates_to_context_manager(bioetl_root: Path) -> None:
    """Verify get_application_context delegates to context_manager.

    The application_context module should import and use get_current_context
    from context_manager for the actual context storage.
    """
    app_context_path = bioetl_root / "interfaces" / "application_context.py"

    assert app_context_path.exists(), f"File not found: {app_context_path}"

    content = app_context_path.read_text()

    # Check that get_current_context is imported and used
    assert (
        "get_current_context" in content
    ), "application_context.py should import get_current_context from context_manager"

    # Check that there's no 'global _context' usage
    assert "global _context" not in content, (
        "application_context.py should not use 'global _context'. "
        "Context management is delegated to context_manager.py."
    )


def test_metrics_server_uses_instance_state(bioetl_root: Path) -> None:
    """Verify MetricsServerManager uses instance-level state, not class-level.

    The class should use __init__ to initialize _started and _lock as
    instance attributes, not class attributes.
    """
    server_path = bioetl_root / "infrastructure" / "observability" / "server.py"

    assert server_path.exists(), f"File not found: {server_path}"

    content = server_path.read_text()
    tree = ast.parse(content)

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "MetricsServerManager":
            # Check for class-level attribute assignments (bad)
            for item in node.body:
                if isinstance(item, ast.AnnAssign):
                    if isinstance(item.target, ast.Name):
                        if item.target.id in ("_started", "_lock"):
                            pytest.fail(
                                f"MetricsServerManager has class-level "
                                f"{item.target.id}. "
                                "Use instance-level state in __init__ instead."
                            )

                if isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name):
                            if target.id in ("_started", "_lock"):
                                pytest.fail(
                                    f"MetricsServerManager has class-level "
                                    f"{target.id}. "
                                    "Use instance-level state in __init__ instead."
                                )
