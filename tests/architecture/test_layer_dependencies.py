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


def test_no_empty_source_files(src_dir: Path) -> None:
    """Source tree must not contain empty Python files (except __init__.py).

    REQ-ARCH-011: Empty files indicate dead code or incomplete implementation.
    Only __init__.py files are allowed to be empty (for package markers).
    """
    bioetl_path = src_dir / "bioetl"
    if not bioetl_path.exists():
        pytest.skip("bioetl source not found")

    empty_files = []
    for py_file in bioetl_path.rglob("*.py"):
        # Skip __init__.py - allowed to be empty for package markers
        if py_file.name == "__init__.py":
            continue

        # Check if file is empty or contains only whitespace/comments
        with py_file.open(encoding="utf-8") as f:
            content = f.read().strip()

        # Remove comments and docstrings for content check
        lines = [
            line.strip()
            for line in content.split("\n")
            if line.strip() and not line.strip().startswith("#")
        ]

        if not lines:
            empty_files.append(str(py_file.relative_to(src_dir)))

    assert not empty_files, (
        f"Found {len(empty_files)} empty source file(s) "
        "(excluding __init__.py):\n" + "\n".join(f"  - {f}" for f in empty_files)
    )


def test_no_orphan_directories(src_dir: Path) -> None:
    """Source tree must not contain orphan directories with only empty files.

    REQ-ARCH-012: Directories with only __init__.py or empty files are dead code.
    Directories that have subdirectories with content are not considered orphan.
    """
    bioetl_path = src_dir / "bioetl"
    if not bioetl_path.exists():
        pytest.skip("bioetl source not found")

    def has_content_in_subtree(dir_path: Path) -> bool:
        """Check if directory or any subdirectory has real Python content."""
        for py_file in dir_path.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue
            with py_file.open(encoding="utf-8") as f:
                if f.read().strip():
                    return True
        return False

    orphan_dirs = []
    for dir_path in bioetl_path.rglob("*"):
        if not dir_path.is_dir():
            continue

        # Skip if this directory has content anywhere in its subtree
        if has_content_in_subtree(dir_path):
            continue

        # Check if this is a leaf directory with only __init__.py
        py_files = list(dir_path.glob("*.py"))
        subdirs = [d for d in dir_path.iterdir() if d.is_dir()]

        # Only flag leaf directories (no subdirs) with only __init__.py
        if not subdirs and py_files:
            init_file = dir_path / "__init__.py"
            if init_file.exists() and len(py_files) == 1:
                with init_file.open(encoding="utf-8") as f:
                    init_content = f.read().strip()
                # Allow if __init__.py re-exports or has __all__
                if not init_content or (
                    "__all__" not in init_content and "import" not in init_content
                ):
                    orphan_dirs.append(str(dir_path.relative_to(src_dir)))

    assert not orphan_dirs, (
        f"Found {len(orphan_dirs)} orphan directory(s) with no real content:\n"
        + "\n".join(f"  - {d}" for d in orphan_dirs)
    )


def test_dead_code_vulture(src_dir: Path) -> None:
    """Detect dead code using vulture static analysis.

    REQ-ARCH-013: No unused code should exist in the codebase.
    """
    try:
        from vulture import Vulture
    except ImportError:
        pytest.skip("vulture not installed - run: pip install vulture")

    bioetl_path = src_dir / "bioetl"
    if not bioetl_path.exists():
        pytest.skip("bioetl source not found")

    v = Vulture()
    v.scavenge([str(bioetl_path)])

    # Filter results - ignore certain patterns
    ignored_names = {
        # Common false positives
        "__init__",
        "__str__",
        "__repr__",
        "__hash__",
        "__eq__",
        "__lt__",
        "__le__",
        "__gt__",
        "__ge__",
        "__aenter__",
        "__aexit__",
        "__enter__",
        "__exit__",
        # Context manager parameters (required by signature)
        "exc_type",
        "exc_val",
        "exc_tb",
        # Protocol methods (interfaces implemented elsewhere)
        "fetch",
        "write_bronze",
        "write_silver",
        "write_gold",
        "acquire",
        "release",
        "save_checkpoint",
        "load_checkpoint",
        "delete_checkpoint",
        "quarantine_record",
        # Pydantic/dataclass fields
        "model_config",
        # Click CLI
        "main",
        # Prefect task decorators
        "execute",
    }

    # Get unused code with confidence threshold
    # Note: TYPE_CHECKING imports often have 90% confidence but are not dead code
    unused = [
        item
        for item in v.get_unused_code(min_confidence=80)
        if item.name not in ignored_names
        and not item.name.startswith("_")  # Ignore private
        and "test" not in str(item.filename).lower()  # Ignore test files
        # Imports at 90% confidence in TYPE_CHECKING blocks are often false positives
        and not (item.typ == "import" and item.confidence < 100)
    ]

    if unused:
        messages = [
            f"{item.filename}:{item.first_lineno} - unused {item.typ} '{item.name}' "
            f"(confidence: {item.confidence}%)"
            for item in unused[:20]  # Limit output
        ]
        if len(unused) > 20:
            messages.append(f"... and {len(unused) - 20} more")

        pytest.fail(
            f"Found {len(unused)} potentially dead code item(s):\n"
            + "\n".join(messages)
        )


def test_application_layer_no_orchestration_imports(src_dir: Path) -> None:
    """Application layer must not import orchestration frameworks directly.

    REQ-ARCH-APP-001: Prefect, Celery, Airflow etc. должны быть изолированы
    в отдельном слое (bioetl/interfaces/orchestration/).
    """
    application_path = src_dir / "bioetl" / "application"
    if not application_path.exists():
        pytest.skip("Application layer not found")

    disallowed = ["prefect", "celery", "airflow", "dagster"]
    violations = []

    for py_file in application_path.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        for lib in disallowed:
            if f"from {lib}" in content or f"import {lib}" in content:
                violations.append(f"{py_file.relative_to(src_dir)}: imports {lib}")

    assert not violations, (
        "Application layer has direct orchestration imports:\n"
        + "\n".join(f"  - {v}" for v in violations)
        + "\n\nMove orchestration code to bioetl/interfaces/orchestration/"
    )


def test_application_layer_no_infrastructure_imports(src_dir: Path) -> None:
    """Application layer must not import from infrastructure.

    REQ-ARCH-APP-002: Application layer depends on domain ports,
    not concrete infrastructure implementations.
    """
    application_path = src_dir / "bioetl" / "application"
    if not application_path.exists():
        pytest.skip("Application layer not found")

    violations = []

    for py_file in application_path.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        for i, line in enumerate(content.splitlines(), 1):
            stripped = line.strip()

            # Skip docstring examples (>>> prefix)
            if stripped.startswith(">>>"):
                continue

            # Skip comments
            if stripped.startswith("#"):
                continue

            if "from bioetl.infrastructure" not in line:
                continue

            # Check if inside TYPE_CHECKING block (allowed for type hints)
            lines = content.splitlines()
            in_type_checking = False
            for j, check_line in enumerate(lines):
                if "if TYPE_CHECKING:" in check_line:
                    in_type_checking = True
                elif in_type_checking and check_line.strip() and not check_line.startswith(
                    (" ", "\t")
                ):
                    in_type_checking = False
                if j + 1 == i and in_type_checking:
                    break
            else:
                violations.append(f"{py_file.relative_to(src_dir)}:{i}: {stripped}")

    assert not violations, (
        "Application layer imports infrastructure directly:\n"
        + "\n".join(f"  - {v}" for v in violations)
        + "\n\nUse dependency injection via domain ports instead."
    )
