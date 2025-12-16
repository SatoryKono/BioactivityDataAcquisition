"""Tests for architectural layer dependencies.

These tests verify that the clean architecture layer boundaries are respected:
- Domain layer: No dependencies on infrastructure or external I/O libraries
- Application layer: Can depend on Domain, but not on Infrastructure implementations
- Infrastructure layer: Implements Domain ports, can depend on external libraries

Uses both static analysis and import-linter for comprehensive checks.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

# Infrastructure/I/O libraries that should NOT be in the domain layer
INFRASTRUCTURE_IMPORTS = {
    "httpx",
    "requests",
    "boto3",
    "sqlalchemy",
    "psycopg2",
    "deltalake",
    "polars",
    "redis",
    "aioredis",
    "asyncpg",
    "motor",
    "pymongo",
}

# Application-specific imports that should NOT be in the domain layer
APPLICATION_IMPORTS = {
    "bioetl.application",
    "bioetl.infrastructure",
}


def _check_imports_in_file(file_path: Path, disallowed: set[str]) -> list[str]:
    """Check a file for disallowed imports.

    Args:
        file_path: Path to the Python file to check
        disallowed: Set of module names that should not be imported

    Returns:
        List of error messages for any disallowed imports found
    """
    errors = []
    with file_path.open(encoding="utf-8") as f:
        content = f.read()

    for lib in disallowed:
        # Check for 'import lib' or 'from lib import ...'
        if re.search(rf"^\s*import\s+{re.escape(lib)}\b", content, re.MULTILINE):
            errors.append(f"Disallowed import 'import {lib}' in {file_path}")
        if re.search(rf"^\s*from\s+{re.escape(lib)}\b", content, re.MULTILINE):
            errors.append(f"Disallowed import 'from {lib}' in {file_path}")

    return errors


def test_domain_layer_no_infrastructure_imports(src_dir: Path) -> None:
    """Domain layer must not import infrastructure/I/O libraries.

    REQ-ARCH-001: The domain layer should contain only pure business logic
    with no dependencies on external I/O libraries.
    """
    domain_path = src_dir / "bioetl" / "domain"
    if not domain_path.exists():
        pytest.skip("Domain layer not found")

    all_errors = []
    for py_file in domain_path.rglob("*.py"):
        errors = _check_imports_in_file(py_file, INFRASTRUCTURE_IMPORTS)
        all_errors.extend(errors)

    assert not all_errors, "\n".join(all_errors)


def test_domain_layer_no_application_imports(src_dir: Path) -> None:
    """Domain layer must not import from application layer.

    REQ-ARCH-002: Domain layer should be independent of application layer
    to maintain proper dependency direction (inward).
    """
    domain_path = src_dir / "bioetl" / "domain"
    if not domain_path.exists():
        pytest.skip("Domain layer not found")

    all_errors = []
    for py_file in domain_path.rglob("*.py"):
        errors = _check_imports_in_file(py_file, APPLICATION_IMPORTS)
        all_errors.extend(errors)

    assert not all_errors, "\n".join(all_errors)


def test_domain_layer_no_infrastructure_layer_imports(src_dir: Path) -> None:
    """Domain layer must not import from infrastructure layer.

    REQ-ARCH-003: Domain layer should not depend on infrastructure
    implementations, only define ports (interfaces).
    """
    domain_path = src_dir / "bioetl" / "domain"
    if not domain_path.exists():
        pytest.skip("Domain layer not found")

    all_errors = []
    for py_file in domain_path.rglob("*.py"):
        errors = _check_imports_in_file(py_file, {"bioetl.infrastructure"})
        all_errors.extend(errors)

    assert not all_errors, "\n".join(all_errors)


def test_application_layer_no_infrastructure_implementation_imports(
    src_dir: Path,
) -> None:
    """Application layer should not import infrastructure implementations at module level.

    REQ-ARCH-004: Application layer should depend on domain ports,
    not concrete infrastructure implementations at module level.

    Note: Local imports within functions (for lazy loading or type hints)
    and imports in docstrings are allowed.
    """
    application_path = src_dir / "bioetl" / "application"
    if not application_path.exists():
        pytest.skip("Application layer not found")

    # These are specific implementation modules that should not be imported
    # Application can import from bioetl.infrastructure for dependency injection
    # but should not import specific adapter implementations directly in business logic
    implementation_imports = {
        "bioetl.infrastructure.adapters.chembl",
        "bioetl.infrastructure.adapters.pubchem",
    }

    all_errors = []
    for py_file in application_path.rglob("*.py"):
        # Skip __init__.py and dependency injection files
        if py_file.name in ("__init__.py", "container.py", "bootstrap.py"):
            continue
        # Skip pipeline files - they may have legitimate local imports for lazy loading
        if "pipeline" in str(py_file):
            continue
        errors = _check_imports_in_file(py_file, implementation_imports)
        all_errors.extend(errors)

    assert not all_errors, "\n".join(all_errors)


def test_ports_defined_in_domain_layer(src_dir: Path) -> None:
    """Ports (interfaces) must be defined in the domain layer.

    REQ-ARCH-005: All port definitions should live in domain/ports.py
    """
    ports_file = src_dir / "bioetl" / "domain" / "ports.py"
    assert ports_file.exists(), "Domain ports file (domain/ports.py) not found"

    with ports_file.open(encoding="utf-8") as f:
        content = f.read()

    # Verify Protocol is used for port definitions
    assert "Protocol" in content, "Ports should be defined using typing.Protocol"


def test_infrastructure_imports_domain_ports(src_dir: Path) -> None:
    """Infrastructure adapters should import from domain layer.

    REQ-ARCH-006: Infrastructure implementations should implement domain ports.
    """
    adapters_path = src_dir / "bioetl" / "infrastructure" / "adapters"
    if not adapters_path.exists():
        pytest.skip("Infrastructure adapters not found")

    found_domain_import = False
    for py_file in adapters_path.rglob("*.py"):
        if py_file.name == "__init__.py":
            continue
        with py_file.open(encoding="utf-8") as f:
            content = f.read()
        if "bioetl.domain" in content:
            found_domain_import = True
            break

    assert found_domain_import, (
        "Infrastructure adapters should import from domain layer "
        "(e.g., to implement ports)"
    )


def test_import_linter_contracts(project_root: Path, src_dir: Path) -> None:
    """Run import-linter to verify all architectural contracts.

    REQ-ARCH-007: All import-linter contracts must pass.
    This provides a secondary layer of validation beyond static checks.
    """
    importlinter_config = project_root / ".importlinter"
    if not importlinter_config.exists():
        pytest.skip(".importlinter config not found")

    # Override PYTHONPATH to ensure correct project is used
    env = os.environ.copy()
    env["PYTHONPATH"] = str(src_dir)

    result = subprocess.run(
        ["lint-imports", "--config", str(importlinter_config)],
        capture_output=True,
        text=True,
        cwd=str(project_root),
        env=env,
    )

    if result.returncode != 0:
        pytest.fail(
            f"import-linter contracts violated:\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )


def test_infrastructure_does_not_import_application(src_dir: Path) -> None:
    """Infrastructure layer must not import from application layer.

    REQ-ARCH-008: Infrastructure is at the outer layer and should only
    implement domain ports, not depend on application services.
    """
    infra_path = src_dir / "bioetl" / "infrastructure"
    if not infra_path.exists():
        pytest.skip("Infrastructure layer not found")

    all_errors = []
    forbidden = {"bioetl.application"}

    for py_file in infra_path.rglob("*.py"):
        errors = _check_imports_in_file(py_file, forbidden)
        all_errors.extend(errors)

    assert not all_errors, "\n".join(all_errors)


def test_domain_layer_uses_protocol_for_ports(src_dir: Path) -> None:
    """Domain layer should use Protocol for defining ports.

    REQ-ARCH-009: Ports should be defined using typing.Protocol
    for structural subtyping (duck typing with type safety).
    """
    ports_file = src_dir / "bioetl" / "domain" / "ports.py"
    if not ports_file.exists():
        pytest.skip("ports.py not found")

    with ports_file.open(encoding="utf-8") as f:
        content = f.read()

    # Check for Protocol usage
    assert (
        "from typing" in content and "Protocol" in content
    ), "Domain ports should use typing.Protocol for interface definitions"

    # Check that Protocol classes are defined
    assert (
        "class" in content and "(Protocol)" in content
    ), "Port interfaces should be classes inheriting from Protocol"


def test_cyclomatic_complexity_domain_layer(src_dir: Path) -> None:
    """Domain layer functions should have low cyclomatic complexity.

    REQ-ARCH-010: Domain logic should be simple and testable.
    Maximum CC = 5 for domain layer functions.
    """
    try:
        from radon.complexity import cc_visit
    except ImportError:
        pytest.skip("radon not installed")

    domain_path = src_dir / "bioetl" / "domain"
    if not domain_path.exists():
        pytest.skip("Domain layer not found")

    violations = []
    max_cc = 5  # Strict threshold for domain layer

    for py_file in domain_path.rglob("*.py"):
        if py_file.name.startswith("__"):
            continue

        with py_file.open(encoding="utf-8") as f:
            content = f.read()

        try:
            results = cc_visit(content)
            for item in results:
                if item.complexity > max_cc:
                    violations.append(
                        f"{py_file}:{item.lineno} - {item.name}() "
                        f"has CC={item.complexity} (max={max_cc})"
                    )
        except SyntaxError:
            continue

    assert (
        not violations
    ), f"Domain layer has functions with CC > {max_cc}:\n" + "\n".join(violations)
