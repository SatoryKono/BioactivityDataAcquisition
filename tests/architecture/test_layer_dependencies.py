"""Tests for architectural layer dependencies.

These tests verify that the clean architecture layer boundaries are respected:
- Domain layer: No dependencies on infrastructure or external I/O libraries
- Application layer: Can depend on Domain, but not on Infrastructure implementations
- Infrastructure layer: Implements Domain ports, can depend on external libraries

Uses both static analysis and import-linter for comprehensive checks.

Note: Tests for domain purity (frozen dataclasses, I/O checks, complexity) have been
moved to test_domain_purity.py. Adapter contract tests moved to test_adapter_contracts.py.
Forbidden import tests moved to test_forbidden_imports.py.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest

# Infrastructure/I/O libraries that should NOT be in the domain layer
INFRASTRUCTURE_IMPORTS = {
    "httpx",
    "requests",
    "sqlalchemy",
    "psycopg2",
    "deltalake",
    "polars",
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

    REQ-ARCH-005: All port definitions should live in domain/ports/ package
    """
    ports_dir = src_dir / "bioetl" / "domain" / "ports"
    assert ports_dir.exists(), "Domain ports package (domain/ports/) not found"
    assert ports_dir.is_dir(), "domain/ports should be a directory (package)"

    # Verify __init__.py exists (proper package)
    init_file = ports_dir / "__init__.py"
    assert init_file.exists(), "domain/ports/__init__.py not found"

    # Verify Protocol is used in at least one port file
    protocol_found = False
    for port_file in ports_dir.glob("*.py"):
        if port_file.name == "__init__.py":
            continue
        with port_file.open(encoding="utf-8") as f:
            if "Protocol" in f.read():
                protocol_found = True
                break

    assert protocol_found, "Ports should be defined using typing.Protocol"


def test_import_linter_contracts(project_root: Path, src_dir: Path) -> None:
    """Run import-linter to verify all architectural contracts.

    REQ-ARCH-007: All import-linter contracts must pass.
    This provides a secondary layer of validation beyond static checks.
    """
    importlinter_config = project_root / ".importlinter"
    if not importlinter_config.exists():
        pytest.skip(".importlinter config not found")

    # Find lint-imports executable (check venv first, then system)
    import shutil

    lint_imports_cmd = shutil.which("lint-imports")
    if lint_imports_cmd is None:
        venv_lint_imports = project_root / ".venv" / "bin" / "lint-imports"
        if venv_lint_imports.exists():
            lint_imports_cmd = str(venv_lint_imports)
        else:
            pytest.skip("lint-imports executable not found")

    # Override PYTHONPATH to ensure correct project is used
    env = os.environ.copy()
    env["PYTHONPATH"] = str(src_dir)

    result = subprocess.run(
        [lint_imports_cmd, "--config", str(importlinter_config)],
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
        # EXCEPTION: config.py can import PipelineConfig
        if py_file.name == "config.py":
            continue
        errors = _check_imports_in_file(py_file, forbidden)
        all_errors.extend(errors)

    assert not all_errors, "\n".join(all_errors)


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
        # NoOpTracer parameters (required by OpenTelemetry interface)
        "kind",
        "attributes",
        "links",
        "set_status_on_exception",
        "end_on_exit",
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
                elif (
                    in_type_checking
                    and check_line.strip()
                    and not check_line.startswith((" ", "\t"))
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


def test_infrastructure_does_not_import_interfaces(src_dir: Path) -> None:
    """Infrastructure layer must not import from interfaces layer.

    REQ-ARCH-015: Interfaces (Driving Adapters) depend on Infrastructure,
    not the other way around. Prevents circular dependencies.
    """
    infra_path = src_dir / "bioetl" / "infrastructure"
    if not infra_path.exists():
        pytest.skip("Infrastructure layer not found")

    all_errors = []
    forbidden = {"bioetl.interfaces"}

    for py_file in infra_path.rglob("*.py"):
        errors = _check_imports_in_file(py_file, forbidden)
        all_errors.extend(errors)

    assert not all_errors, "\n".join(all_errors)


def test_infrastructure_does_not_import_composition(src_dir: Path) -> None:
    """Infrastructure layer must not import from composition layer.

    REQ-ARCH-017: Composition is the assembly layer. Infrastructure
    must not depend on it to maintain proper dependency direction.
    See CLAUDE.md §2.1 Matrix of Imports.
    """
    infra_path = src_dir / "bioetl" / "infrastructure"
    if not infra_path.exists():
        pytest.skip("Infrastructure layer not found")

    all_errors = []
    forbidden = {"bioetl.composition"}

    for py_file in infra_path.rglob("*.py"):
        errors = _check_imports_in_file(py_file, forbidden)
        all_errors.extend(errors)

    assert not all_errors, "Infrastructure must not import composition.\n" + "\n".join(
        all_errors
    )


def test_no_hasattr_duck_typing_in_application(src_dir: Path) -> None:
    """Application layer should not use hasattr for port method checks.

    REQ-ARCH-017: The application layer should rely on explicit port contracts
    (Protocols) instead of duck-typing with hasattr. Using hasattr to check
    for port methods indicates missing contract definitions.

    Allowed exceptions:
    - TYPE_CHECKING blocks (static analysis only)
    - Checking for dunder methods (__enter__, __aiter__, etc.)
    - Checking for private attributes (_internal)
    - fetch_filtered: Extension method for filterable adapters (ChEMBL-specific)
    """
    import ast

    application_path = src_dir / "bioetl" / "application"
    if not application_path.exists():
        pytest.skip("Application layer not found")

    # Methods that indicate duck-typing on ports (suspicious patterns)
    PORT_METHOD_PATTERNS = (
        "clear_",
        "write_",
        # "fetch_" excluded: fetch_filtered is a documented extension pattern
        "read_",
        "load_",
        "save_",
        "delete_",
        "health_",
        "acquire",
        "release",
    )

    # Explicitly allowed hasattr checks (documented extensions)
    # Note: fetch_filtered is now formalized via FilterableDataSourcePort Protocol
    ALLOWED_HASATTR_CHECKS: set[str] = set()

    violations = []

    for py_file in application_path.rglob("*.py"):
        with py_file.open(encoding="utf-8") as f:
            try:
                tree = ast.parse(f.read(), filename=str(py_file))
            except SyntaxError:
                continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Check for hasattr(obj, "method_name") calls
                if (
                    isinstance(node.func, ast.Name)
                    and node.func.id == "hasattr"
                    and len(node.args) >= 2
                ):
                    # Get the attribute name being checked
                    attr_arg = node.args[1]
                    if isinstance(attr_arg, ast.Constant) and isinstance(
                        attr_arg.value, str
                    ):
                        attr_name = attr_arg.value

                        # Skip dunder methods and private attributes
                        if attr_name.startswith("_"):
                            continue

                        # Skip explicitly allowed extensions
                        if attr_name in ALLOWED_HASATTR_CHECKS:
                            continue

                        # Check if it matches port method patterns
                        if any(
                            attr_name.startswith(pattern)
                            for pattern in PORT_METHOD_PATTERNS
                        ):
                            violations.append(
                                f"{py_file.name}:{node.lineno} - "
                                f"hasattr check for '{attr_name}' suggests missing port contract"
                            )

    assert not violations, (
        "Found hasattr duck-typing in application layer. "
        "Add missing methods to port contracts in domain/ports/ package:\n"
        + "\n".join(f"  - {v}" for v in violations)
    )


# ============================================================================
# Refactoring Tests (added for architecture cleanup)
# ============================================================================


def test_all_bioetl_exceptions_have_error_type(src_dir: Path) -> None:
    """All BioETLError subclasses MUST have explicit error_type attribute.

    REQ-ARCH-020: Deterministic error classification requires explicit mapping.
    This ensures ErrorClassifier uses the error_type attribute instead of
    keyword matching for domain exceptions.
    """
    import ast

    # Support both single file and package structure
    exceptions_dir = src_dir / "bioetl" / "domain" / "exceptions"
    exceptions_file = src_dir / "bioetl" / "domain" / "exceptions.py"

    exception_files: list[Path] = []
    if exceptions_dir.is_dir():
        # New package structure: scan all .py files except __init__.py
        exception_files = [
            f for f in exceptions_dir.glob("*.py") if f.name != "__init__.py"
        ]
    elif exceptions_file.exists():
        # Legacy single file structure
        exception_files = [exceptions_file]
    else:
        pytest.skip("Domain exceptions not found")

    # Parse all exception files and collect AST trees
    trees: list[ast.AST] = []
    for f in exception_files:
        with f.open(encoding="utf-8") as fp:
            content = fp.read()
            trees.append(ast.parse(content))

    # Base classes that don't need error_type (they provide defaults)
    base_classes = {
        "BioETLError",
        "CriticalError",
        "RecoverableError",
        "DataQualityError",
    }

    # Classes that inherit from BioETL exception hierarchy
    exception_bases = {
        "BioETLError",
        "CriticalError",
        "RecoverableError",
        "DataQualityError",
        "StorageError",
        "ApiError",
    }

    missing_error_type = []

    for tree in trees:
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Skip base classes
                if node.name in base_classes:
                    continue

                # Check if inherits from exception hierarchy
                bases = []
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        bases.append(base.id)
                    elif isinstance(base, ast.Attribute):
                        bases.append(base.attr)

                if not any(b in exception_bases for b in bases):
                    continue

                # Check for error_type class attribute
                has_error_type = False
                for stmt in node.body:
                    # Check for error_type assignment
                    if isinstance(stmt, ast.Assign):
                        for target in stmt.targets:
                            if (
                                isinstance(target, ast.Name)
                                and target.id == "error_type"
                            ):
                                has_error_type = True
                                break
                    # Check for annotated assignment
                    if isinstance(stmt, ast.AnnAssign):
                        if (
                            isinstance(stmt.target, ast.Name)
                            and stmt.target.id == "error_type"
                        ):
                            has_error_type = True
                    # Check for Import statement (class-level import for error_type)
                    if isinstance(stmt, ast.ImportFrom):
                        for alias in stmt.names:
                            if alias.name == "ErrorType":
                                # Next statement should be error_type assignment
                                pass

                if not has_error_type:
                    missing_error_type.append(node.name)

    assert not missing_error_type, (
        "BioETLError subclasses must have explicit error_type attribute.\n"
        "Missing error_type:\n" + "\n".join(f"  - {c}" for c in missing_error_type)
    )


def test_observability_ports_have_close_method(src_dir: Path) -> None:
    """MetricsPort and TracingPort MUST define close() method.

    REQ-ARCH-021: Proper lifecycle management for observability resources.
    """
    observability_file = src_dir / "bioetl" / "domain" / "ports" / "observability.py"
    if not observability_file.exists():
        pytest.skip("Domain ports observability file not found")

    with observability_file.open(encoding="utf-8") as f:
        content = f.read()

    import ast

    tree = ast.parse(content)

    required_ports = {"MetricsPort", "TracingPort"}
    found_close: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name in required_ports:
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "close":
                    found_close.add(node.name)

    missing = required_ports - found_close
    assert not missing, f"Observability ports missing close() method: {missing}"


def test_storage_port_has_preview_cleanup(src_dir: Path) -> None:
    """StoragePort MUST define preview_cleanup() for CLI dry-run.

    REQ-ARCH-022: CLI delegates all storage operations to port.
    """
    storage_file = src_dir / "bioetl" / "domain" / "ports" / "storage.py"
    if not storage_file.exists():
        pytest.skip("Domain ports storage file not found")

    with storage_file.open(encoding="utf-8") as f:
        content = f.read()

    assert "def preview_cleanup(" in content, (
        "StoragePort must define preview_cleanup() method for CLI dry-run support"
    )


def test_error_classifier_uses_error_type_attribute(src_dir: Path) -> None:
    """ErrorClassifier SHOULD use error_type attribute for BioETLError.

    REQ-ARCH-024: Deterministic error classification.
    """
    classifier_file = src_dir / "bioetl" / "domain" / "error_classifier.py"
    if not classifier_file.exists():
        pytest.skip("Error classifier not found")

    with classifier_file.open(encoding="utf-8") as f:
        content = f.read()

    # Should have get_error_type() call for domain errors
    assert "get_error_type()" in content or "error_type" in content, (
        "ErrorClassifier should use error_type attribute for domain exceptions"
    )
