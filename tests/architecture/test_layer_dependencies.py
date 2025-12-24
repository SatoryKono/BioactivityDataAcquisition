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
        # ИСКЛЮЧЕНИЕ: config.py может импортировать PipelineConfig
        if py_file.name == "config.py":
            continue
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


def test_domain_value_objects_are_frozen(src_dir: Path) -> None:
    """Domain Value Objects (dataclasses) must be frozen.

    REQ-ARCH-014: Domain entities and value objects must be immutable
    to ensure side-effect-free behavior and thread safety.
    """
    import ast

    domain_path = src_dir / "bioetl" / "domain"
    if not domain_path.exists():
        pytest.skip("Domain layer not found")

    violations = []

    for py_file in domain_path.rglob("*.py"):
        with py_file.open(encoding="utf-8") as f:
            try:
                tree = ast.parse(f.read(), filename=str(py_file))
            except SyntaxError:
                continue

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check for @dataclass decorator
                is_dataclass = False
                is_frozen = False

                for decorator in node.decorator_list:
                    # Case 1: @dataclass
                    if isinstance(decorator, ast.Name) and decorator.id == "dataclass":
                        is_dataclass = True
                        # Default is frozen=False

                    # Case 2: @dataclass(...)
                    elif isinstance(decorator, ast.Call):
                        func = decorator.func
                        if isinstance(func, ast.Name) and func.id == "dataclass":
                            is_dataclass = True
                            # Check keywords for frozen=True
                            for keyword in decorator.keywords:
                                if (
                                    keyword.arg == "frozen"
                                    and isinstance(keyword.value, ast.Constant)
                                    and keyword.value.value is True
                                ):
                                    is_frozen = True

                if is_dataclass and not is_frozen:
                    # Exemptions can be added here if strictly necessary, but default rule is strict
                    violations.append(
                        f"{py_file.name}:{node.lineno} - {node.name} is not frozen"
                    )

    assert (
        not violations
    ), "Found mutable domain dataclasses (must be frozen=True):\n" + "\n".join(
        f"  - {v}" for v in violations
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


def test_no_mutable_defaults_in_frozen_dataclasses(src_dir: Path) -> None:
    """Frozen dataclasses should not have mutable default arguments.

    REQ-ARCH-016: Mutable defaults (list, dict, set) in dataclasses
    cause shared state issues even if the class is frozen.
    """
    import ast

    bioetl_path = src_dir / "bioetl"
    if not bioetl_path.exists():
        pytest.skip("bioetl source not found")

    violations = []

    for py_file in bioetl_path.rglob("*.py"):
        with py_file.open(encoding="utf-8") as f:
            try:
                tree = ast.parse(f.read(), filename=str(py_file))
            except SyntaxError:
                continue

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if it's a dataclass
                is_dataclass = False
                for decorator in node.decorator_list:
                    if (
                        isinstance(decorator, ast.Name) and decorator.id == "dataclass"
                    ) or (
                        isinstance(decorator, ast.Call)
                        and (
                            isinstance(decorator.func, ast.Name)
                            and decorator.func.id == "dataclass"
                        )
                    ):
                        is_dataclass = True

                if not is_dataclass:
                    continue

                # Check fields for mutable defaults
                for item in node.body:
                    if isinstance(item, ast.AnnAssign):
                        if item.value:  # Has a default value
                            is_mutable = False
                            if isinstance(item.value, (ast.List, ast.Dict, ast.Set)):
                                is_mutable = True
                            elif isinstance(item.value, ast.Call):
                                # Check for simple calls like list(), dict(), set()
                                if isinstance(
                                    item.value.func, ast.Name
                                ) and item.value.func.id in ("list", "dict", "set"):
                                    is_mutable = True

                            if is_mutable:
                                violations.append(
                                    f"{py_file.name}:{item.lineno} - Field '{getattr(item.target, 'id', 'unknown')}' "
                                    f"in class '{node.name}' has a mutable default value."
                                )

    assert not violations, (
        "Found mutable defaults in dataclasses (use field(default_factory=...) instead):\n"
        + "\n".join(f"  - {v}" for v in violations)
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
      TODO: Create FilterableDataSourcePort Protocol to formalize this
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
        "Add missing methods to port contracts in domain/ports.py:\n"
        + "\n".join(f"  - {v}" for v in violations)
    )


def test_metrics_server_only_in_composition(src_dir: Path) -> None:
    """Verify start_metrics_server is only called from composition layer.

    REQ-ARCH-OBS-001: Observability initialization should only happen
    in the composition root to ensure single point of responsibility.
    """
    forbidden_layers = ["interfaces", "application", "domain"]
    allowed_patterns = [
        r"def start_metrics_server",  # Definition is allowed
        r"from.*import.*start_metrics_server",  # Import is allowed
        r"#.*start_metrics_server",  # Comments are allowed
        r"\"\"\".*start_metrics_server",  # Docstrings are allowed
    ]

    violations = []

    for layer in forbidden_layers:
        layer_path = src_dir / "bioetl" / layer
        if not layer_path.exists():
            continue

        for py_file in layer_path.rglob("*.py"):
            with py_file.open(encoding="utf-8") as f:
                content = f.read()
                lines = content.splitlines()

            for i, line in enumerate(lines, 1):
                # Check if line contains actual call to start_metrics_server
                if "start_metrics_server(" in line:
                    # Skip if matches allowed patterns
                    if any(re.search(p, line) for p in allowed_patterns):
                        continue

                    relative_path = py_file.relative_to(src_dir)
                    violations.append(f"{relative_path}:{i} - {line.strip()}")

    assert not violations, (
        "start_metrics_server() should only be called from composition layer.\n"
        "Found calls in forbidden layers:\n"
        + "\n".join(f"  - {v}" for v in violations)
    )


def test_no_direct_io_in_domain(src_dir: Path) -> None:
    """Verify domain layer has no direct I/O operations.

    REQ-ARCH-003: Domain layer should be pure business logic without I/O.
    """
    domain_path = src_dir / "bioetl" / "domain"
    if not domain_path.exists():
        pytest.skip("Domain layer not found")

    # Patterns that indicate direct I/O
    io_patterns = [
        (r"\bopen\s*\(", "open() file access"),
        (r"Path\s*\([^)]+\)\s*\.\s*(read|write|mkdir|unlink)", "Path I/O methods"),
        (r"os\.(read|write|mkdir|remove|rename)", "os module I/O"),
        (r"shutil\.(copy|move|rmtree)", "shutil I/O operations"),
    ]

    # Excluded files (test files, __init__.py)
    excluded_files = {"__init__.py"}

    violations = []

    for py_file in domain_path.rglob("*.py"):
        if py_file.name in excluded_files:
            continue

        with py_file.open(encoding="utf-8") as f:
            content = f.read()
            lines = content.splitlines()

        for i, line in enumerate(lines, 1):
            # Skip comments and docstrings
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith('"""'):
                continue

            for pattern, description in io_patterns:
                if re.search(pattern, line):
                    relative_path = py_file.relative_to(src_dir)
                    violations.append(
                        f"{relative_path}:{i} - {description}: {stripped[:60]}..."
                    )

    assert not violations, (
        "Domain layer should not have direct I/O operations.\n"
        "Found violations:\n" + "\n".join(f"  - {v}" for v in violations)
    )


def test_atomic_write_used_in_writers(src_dir: Path) -> None:
    """Verify that storage writers use atomic write patterns.

    REQ-DATA-004: All file writes should be atomic to prevent data corruption.
    """
    storage_path = src_dir / "bioetl" / "infrastructure" / "storage"
    if not storage_path.exists():
        pytest.skip("Storage layer not found")

    # Writers that should use atomic patterns
    writer_files = ["bronze_writer.py", "gold_writer.py"]

    # Patterns indicating non-atomic writes
    non_atomic_patterns = [
        r'with\s+open\s*\([^)]+,\s*["\']w',  # with open(path, 'w')
        r'\.write\s*\([^)]+\)\s*$',  # .write() at end of line (might be in context)
    ]

    # Patterns indicating atomic writes (should be present)
    atomic_indicators = [
        r"atomic_write",
        r"AtomicWriteGroup",
        r"\.replace\s*\(",
        r"tempfile\.mkstemp",
    ]

    findings = []

    for writer_file in writer_files:
        file_path = storage_path / writer_file
        if not file_path.exists():
            continue

        with file_path.open(encoding="utf-8") as f:
            content = f.read()

        # Check for atomic indicators
        has_atomic = any(re.search(p, content) for p in atomic_indicators)

        if not has_atomic:
            findings.append(f"{writer_file} - No atomic write patterns detected")

    assert not findings, (
        "Storage writers should use atomic write patterns (temp file + rename).\n"
        "Files missing atomic patterns:\n" + "\n".join(f"  - {f}" for f in findings)
    )


def test_adapters_have_health_check(src_dir: Path) -> None:
    """All adapters MUST implement health_check() method.

    REQ-OBS-001: Adapters must provide health check for provider monitoring.
    See docs/05-operations/runbooks/observability-checklist.md.
    """
    adapters_path = src_dir / "bioetl" / "infrastructure" / "adapters"
    if not adapters_path.exists():
        pytest.skip("Infrastructure adapters not found")

    # Files that define adapter classes (not __init__.py or base classes)
    # Exclude HTTP infrastructure utilities that are not DataSourcePort adapters
    excluded_files = {
        "base.py",
        "types.py",
        "exceptions.py",
        "client.py",  # HTTP client utility, not a DataSourcePort adapter
        "pagination.py",  # Pagination mixin, not a DataSourcePort adapter
        "rate_limiter.py",  # Rate limiting utility
        "circuit_breaker.py",  # Circuit breaker utility
    }
    adapter_files = []
    for py_file in adapters_path.rglob("*.py"):
        if py_file.name.startswith("_"):
            continue
        if py_file.name in excluded_files:
            continue
        adapter_files.append(py_file)

    missing_health_check = []

    for py_file in adapter_files:
        content = py_file.read_text(encoding="utf-8")

        # Check if file defines a class (likely an adapter)
        if "class " not in content:
            continue

        # Check for health_check method definition
        has_health_check = (
            "def health_check" in content or "async def health_check" in content
        )

        if not has_health_check:
            # Only flag if it looks like an adapter class
            if "Adapter" in content or "Client" in content or "Fetcher" in content:
                relative_path = py_file.relative_to(src_dir)
                missing_health_check.append(str(relative_path))

    assert not missing_health_check, (
        "Adapters must implement health_check() method (REQ-OBS-001).\n"
        "Files missing health_check:\n"
        + "\n".join(f"  - {f}" for f in missing_health_check)
        + "\n\nSee: docs/05-operations/runbooks/observability-checklist.md"
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

    exceptions_file = src_dir / "bioetl" / "domain" / "exceptions.py"
    if not exceptions_file.exists():
        pytest.skip("Domain exceptions file not found")

    with exceptions_file.open(encoding="utf-8") as f:
        content = f.read()
        tree = ast.parse(content)

    # Base classes that don't need error_type (they provide defaults)
    base_classes = {"BioETLError", "CriticalError", "RecoverableError", "DataQualityError"}

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
                        if isinstance(target, ast.Name) and target.id == "error_type":
                            has_error_type = True
                            break
                # Check for annotated assignment
                if isinstance(stmt, ast.AnnAssign):
                    if isinstance(stmt.target, ast.Name) and stmt.target.id == "error_type":
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
    ports_file = src_dir / "bioetl" / "domain" / "ports.py"
    if not ports_file.exists():
        pytest.skip("Domain ports file not found")

    with ports_file.open(encoding="utf-8") as f:
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
    ports_file = src_dir / "bioetl" / "domain" / "ports.py"
    if not ports_file.exists():
        pytest.skip("Domain ports file not found")

    with ports_file.open(encoding="utf-8") as f:
        content = f.read()

    assert "def preview_cleanup(" in content, (
        "StoragePort must define preview_cleanup() method for CLI dry-run support"
    )


def test_interfaces_no_direct_filesystem_traversal(src_dir: Path) -> None:
    """Interfaces layer MUST NOT use direct filesystem traversal.

    REQ-ARCH-023: CLI delegates to StoragePort, not Path.rglob.
    """
    interfaces_path = src_dir / "bioetl" / "interfaces"
    if not interfaces_path.exists():
        pytest.skip("Interfaces layer not found")

    forbidden_patterns = [
        r"\.rglob\(",
        r"\.glob\(",
        r"os\.walk\(",
        r"os\.listdir\(",
    ]

    errors = []
    for py_file in interfaces_path.rglob("*.py"):
        if py_file.name.startswith("_"):
            continue

        with py_file.open(encoding="utf-8") as f:
            content = f.read()

        for pattern in forbidden_patterns:
            if re.search(pattern, content):
                relative_path = py_file.relative_to(src_dir)
                errors.append(f"{relative_path}: contains '{pattern}'")

    assert not errors, (
        "Interfaces layer must not use direct filesystem traversal.\n"
        "Delegate to StoragePort instead.\n"
        "Violations:\n" + "\n".join(f"  - {e}" for e in errors)
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


def test_filterable_adapters_implement_protocol(src_dir: Path) -> None:
    """Adapters with fetch_filtered MUST implement FilterableDataSourcePort.

    REQ-ARCH-025: Replace duck-typing with explicit Protocol for adapters
    that support filtering at API level. This ensures type safety and
    enables isinstance() checks instead of hasattr().
    """
    adapters_path = src_dir / "bioetl" / "infrastructure" / "adapters"
    if not adapters_path.exists():
        pytest.skip("Infrastructure adapters not found")

    violations = []

    for py_file in adapters_path.rglob("*.py"):
        if py_file.name.startswith("_"):
            continue

        content = py_file.read_text(encoding="utf-8")

        # Check if file defines fetch_filtered method
        has_fetch_filtered = (
            "def fetch_filtered" in content or "async def fetch_filtered" in content
        )

        if has_fetch_filtered:
            # Should reference FilterableDataSourcePort in docstring
            has_protocol_ref = "FilterableDataSourcePort" in content

            if not has_protocol_ref:
                relative_path = py_file.relative_to(src_dir)
                violations.append(
                    f"{relative_path}: defines fetch_filtered but doesn't "
                    "reference FilterableDataSourcePort"
                )

    assert not violations, (
        "Adapters with fetch_filtered must implement FilterableDataSourcePort.\n"
        "Update class/method docstrings to reference the Protocol:\n"
        + "\n".join(f"  - {v}" for v in violations)
    )


def test_filtered_data_source_uses_isinstance(src_dir: Path) -> None:
    """FilteredDataSource MUST use isinstance() for Protocol check.

    REQ-ARCH-026: Replace hasattr() duck-typing with isinstance() check
    for FilterableDataSourcePort. This enables proper type checking and
    IDE support.
    """
    filtered_source = (
        src_dir / "bioetl" / "application" / "core" / "filtered_data_source.py"
    )
    if not filtered_source.exists():
        pytest.skip("FilteredDataSource not found")

    content = filtered_source.read_text(encoding="utf-8")

    # Should NOT use hasattr for fetch_filtered
    uses_hasattr = 'hasattr' in content and 'fetch_filtered' in content
    assert not uses_hasattr, (
        "FilteredDataSource should not use hasattr() for fetch_filtered check. "
        "Use isinstance(adapter, FilterableDataSourcePort) instead."
    )

    # Should use isinstance with FilterableDataSourcePort
    uses_isinstance = (
        "isinstance" in content and "FilterableDataSourcePort" in content
    )
    assert uses_isinstance, (
        "FilteredDataSource must use isinstance(adapter, FilterableDataSourcePort) "
        "for type-safe Protocol check."
    )
