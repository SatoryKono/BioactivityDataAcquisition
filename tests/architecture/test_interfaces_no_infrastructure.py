"""Architecture tests for interfaces layer dependencies.

Ensures that CLI and other interfaces do not directly import infrastructure.
In project policy, interfaces should route through application services or
composition entrypoints rather than bind themselves to infrastructure modules.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

# Base path for source files
SRC_PATH = Path(__file__).parent.parent.parent / "src" / "bioetl"


def get_imports_from_file(file_path: Path) -> list[str]:
    """Extract all import statements from a Python file.

    Args:
        file_path: Path to Python file.

    Returns:
        List of imported module paths.
    """
    with open(file_path) as f:
        try:
            tree = ast.parse(f.read(), filename=str(file_path))
        except SyntaxError:
            return []

    imports = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)

    return imports


def _parsed_import_tree(file_path: Path) -> ast.AST | None:
    with open(file_path) as f:
        try:
            return ast.parse(f.read(), filename=str(file_path))
        except SyntaxError:
            return None


def _type_checking_import_lines(tree: ast.AST) -> set[int]:
    type_checking_imports: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        if isinstance(node.test, ast.Name) and node.test.id == "TYPE_CHECKING":
            for stmt in ast.walk(node):
                if isinstance(stmt, (ast.Import, ast.ImportFrom)):
                    type_checking_imports.add(stmt.lineno)
    return type_checking_imports


def _runtime_import_from_node(
    node: ast.AST,
    *,
    type_checking_imports: set[int],
) -> list[str]:
    if getattr(node, "lineno", None) in type_checking_imports:
        return []
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if isinstance(node, ast.ImportFrom) and node.module:
        return [node.module]
    return []


@pytest.mark.architecture
class TestInterfacesNoDIrectInfrastructure:
    """Test that interfaces don't directly import infrastructure."""

    def test_cli_no_infrastructure_imports(self):
        """Test that CLI doesn't import from infrastructure directly."""
        # CLI is now in a package structure: interfaces/cli/main.py
        cli_path = SRC_PATH / "interfaces" / "cli" / "main.py"
        assert cli_path.exists(), "CLI main.py not found"

        imports = get_imports_from_file(cli_path)

        infrastructure_imports = [
            imp for imp in imports if "bioetl.infrastructure" in imp
        ]

        assert infrastructure_imports == [], (
            f"CLI should not import directly from infrastructure. "
            f"Found: {infrastructure_imports}. "
            f"Use Application services or Composition entrypoints instead."
        )

    def test_cli_no_bootstrap_internal_imports(self):
        """Test that CLI doesn't import from _bootstrap internal module.

        CLI should use composition.entrypoints, not _bootstrap directly.
        """
        # CLI is now in a package structure: interfaces/cli/main.py
        cli_path = SRC_PATH / "interfaces" / "cli" / "main.py"
        assert cli_path.exists(), "CLI main.py not found"

        imports = get_imports_from_file(cli_path)

        bootstrap_imports = [imp for imp in imports if "composition._bootstrap" in imp]

        assert bootstrap_imports == [], (
            f"CLI should not import from _bootstrap. "
            f"Found: {bootstrap_imports}. "
            f"Use composition.entrypoints instead."
        )

    def test_all_cli_commands_no_infrastructure_imports(self):
        """Test that ALL CLI command files don't import infrastructure.

        CLI commands should use Application services or Composition entrypoints
        instead of importing infrastructure modules directly.
        """
        commands_dir = SRC_PATH / "interfaces" / "cli" / "commands"
        assert commands_dir.exists(), "CLI commands directory not found"

        violations = []

        for py_file in commands_dir.glob("*.py"):
            # Skip __init__.py as it typically just re-exports
            if py_file.name == "__init__.py":
                continue

            imports = get_imports_from_file(py_file)
            infrastructure_imports = [
                imp for imp in imports if "bioetl.infrastructure" in imp
            ]

            if infrastructure_imports:
                violations.append(f"{py_file.name}: {infrastructure_imports}")

        assert violations == [], (
            "CLI commands should not import from infrastructure directly. "
            "Found violations:\n  - " + "\n  - ".join(violations) + "\n"
            "Use Application services or Composition entrypoints instead."
        )

    def test_legacy_cli_infrastructure_imports_documented(self):
        """Document and track legacy infrastructure imports in CLI commands.

        This test tracks known violations that are allowed temporarily.
        As violations are fixed, remove them from the allowlist.
        If all are fixed, this test can be removed.
        """
        commands_dir = SRC_PATH / "interfaces" / "cli" / "commands"
        assert commands_dir.exists(), "CLI commands directory not found"

        # Expected legacy violations - keep in sync with test above
        # Note: quarantine.py was fixed in IF-002 refactoring to use QuarantineService
        # Note: health.py was fixed to use composition entrypoints for DI
        expected_violations: dict[str, list[str]] = {
            # All CLI commands now properly use composition entrypoints
        }

        actual_violations = {}

        for py_file in commands_dir.glob("*.py"):
            if py_file.name == "__init__.py":
                continue

            imports = get_imports_from_file(py_file)
            infrastructure_imports = sorted(
                {imp for imp in imports if "bioetl.infrastructure" in imp}
            )

            if infrastructure_imports:
                actual_violations[py_file.name] = infrastructure_imports

        # Check that we're tracking all known violations
        for filename, expected_imports in expected_violations.items():
            actual = actual_violations.get(filename, [])
            for expected_import in expected_imports:
                assert expected_import in actual, (
                    f"Expected violation in {filename}: {expected_import} "
                    f"was fixed! Remove from allowed_legacy_files."
                )

        # Check for new violations not in our allowlist
        for filename, imports in actual_violations.items():
            if filename not in expected_violations:
                pytest.fail(
                    f"New infrastructure import in {filename}: {imports}. "
                    f"Either fix it or add to expected_violations with justification."
                )

    def test_interfaces_module_no_infrastructure_imports(self):
        """Test that interfaces __init__ doesn't import infrastructure."""
        init_path = SRC_PATH / "interfaces" / "__init__.py"
        assert init_path.exists(), "interfaces __init__ not found"

        imports = get_imports_from_file(init_path)

        infrastructure_imports = [
            imp for imp in imports if "bioetl.infrastructure" in imp
        ]

        assert infrastructure_imports == [], (
            "interfaces/__init__ should not import infrastructure directly. "
            f"Found: {infrastructure_imports}"
        )

    def test_observability_no_infrastructure_imports(self):
        """Observability interface should route through composition, not infrastructure."""
        obs_path = SRC_PATH / "interfaces" / "observability.py"
        assert obs_path.exists(), "observability.py not found"

        imports = get_imports_from_file(obs_path)

        infrastructure_imports = [
            imp for imp in imports if "bioetl.infrastructure" in imp
        ]

        assert infrastructure_imports == [], (
            "interfaces/observability.py should not import infrastructure directly. "
            f"Found: {infrastructure_imports}"
        )


@pytest.mark.architecture
class TestApplicationServicesExist:
    """Test that Application services exist for administrative operations."""

    def test_checkpoint_service_exists(self):
        """Test CheckpointService exists."""
        service_path = SRC_PATH / "application" / "services" / "checkpoint_service.py"
        assert service_path.exists(), "CheckpointService should exist"

    def test_quarantine_service_exists(self):
        """Test QuarantineService exists."""
        service_path = SRC_PATH / "application" / "services" / "quarantine_service.py"
        assert service_path.exists(), "QuarantineService should exist"

    def test_lock_service_exists(self):
        """Test LockService exists."""
        service_path = SRC_PATH / "application" / "services" / "lock_service.py"
        assert service_path.exists(), "LockService should exist"

    def test_bronze_cleanup_service_exists(self):
        """Test BronzeCleanupService exists."""
        service_path = (
            SRC_PATH / "application" / "services" / "bronze_cleanup_service.py"
        )
        assert service_path.exists(), "BronzeCleanupService should exist"


@pytest.mark.architecture
class TestEntrypointsLegacyServiceCompatibility:
    """Test service getter compatibility behavior in composition entrypoints."""

    def test_entrypoints_exports_services(self):
        """Test that entrypoints exports getter functions for services."""
        from bioetl.composition import entrypoints

        entrypoint_names = set(dir(entrypoints))
        assert "get_checkpoint_service" in entrypoint_names, (
            "entrypoints should expose get_checkpoint_service for legacy discovery"
        )
        assert "get_quarantine_service" in entrypoint_names, (
            "entrypoints should expose get_quarantine_service for legacy discovery"
        )
        assert "get_bronze_cleanup_service" in entrypoint_names, (
            "entrypoints should expose get_bronze_cleanup_service for legacy discovery"
        )

    def test_entrypoints_all_excludes_legacy_service_getters(self):
        """Legacy service getters should be accessible but excluded from __all__."""
        from bioetl.composition import entrypoints, services_api

        assert "get_checkpoint_service" not in entrypoints.__all__
        assert "get_quarantine_service" not in entrypoints.__all__
        assert "get_bronze_cleanup_service" not in entrypoints.__all__

        assert hasattr(services_api, "get_checkpoint_service")
        assert hasattr(services_api, "get_quarantine_service")
        assert hasattr(services_api, "get_bronze_cleanup_service")


def get_runtime_imports_from_file(file_path: Path) -> list[str]:
    """Extract only runtime import statements from a Python file.

    Excludes imports inside TYPE_CHECKING blocks.

    Args:
        file_path: Path to Python file.

    Returns:
        List of imported module paths (runtime only).
    """
    tree = _parsed_import_tree(file_path)
    if tree is None:
        return []

    imports: list[str] = []
    type_checking_imports = _type_checking_import_lines(tree)
    for node in ast.walk(tree):
        imports.extend(
            _runtime_import_from_node(
                node,
                type_checking_imports=type_checking_imports,
            )
        )
    return imports


def _runtime_infrastructure_imports(py_file: Path) -> list[str]:
    imports = get_runtime_imports_from_file(py_file)
    return [imp for imp in imports if "bioetl.infrastructure" in imp]


def _http_runtime_infrastructure_violations(http_dir: Path) -> list[str]:
    violations: list[str] = []
    for py_file in http_dir.glob("*.py"):
        if py_file.name == "__init__.py":
            continue
        infrastructure_imports = _runtime_infrastructure_imports(py_file)
        if infrastructure_imports:
            violations.append(f"{py_file.name}: {infrastructure_imports}")
    return violations


@pytest.mark.architecture
class TestHttpInterfaceNoInfrastructure:
    """Test that HTTP interface module doesn't have runtime infrastructure imports."""

    def test_http_init_no_runtime_infrastructure_imports(self):
        """Test that http/__init__.py doesn't import infrastructure at runtime."""
        init_path = SRC_PATH / "interfaces" / "http" / "__init__.py"
        assert init_path.exists(), "http/__init__.py not found"

        imports = get_runtime_imports_from_file(init_path)

        infrastructure_imports = [
            imp for imp in imports if "bioetl.infrastructure" in imp
        ]

        assert infrastructure_imports == [], (
            f"http/__init__.py should not import from infrastructure at runtime. "
            f"Found: {infrastructure_imports}. "
            f"Use TYPE_CHECKING for type hints or Application services instead."
        )

    def test_http_types_no_runtime_infrastructure_imports(self):
        """Test that http/types.py doesn't import infrastructure at runtime."""
        types_path = SRC_PATH / "interfaces" / "http" / "types.py"
        assert types_path.exists(), "http/types.py not found"

        imports = get_runtime_imports_from_file(types_path)

        infrastructure_imports = [
            imp for imp in imports if "bioetl.infrastructure" in imp
        ]

        assert infrastructure_imports == [], (
            f"http/types.py should not import from infrastructure at runtime. "
            f"Found: {infrastructure_imports}. "
            f"Types should be independent of infrastructure layer."
        )

    def test_health_server_no_runtime_infrastructure_imports(self):
        """Test that health_server.py doesn't import infrastructure at runtime.

        TYPE_CHECKING imports are allowed for type hints, but runtime imports
        from infrastructure should go through Application services.
        """
        server_path = SRC_PATH / "interfaces" / "http" / "health_server.py"
        assert server_path.exists(), "health_server.py not found"

        imports = get_runtime_imports_from_file(server_path)

        infrastructure_imports = [
            imp for imp in imports if "bioetl.infrastructure" in imp
        ]

        assert infrastructure_imports == [], (
            f"health_server.py should not import from infrastructure at runtime. "
            f"Found: {infrastructure_imports}. "
            f"Use TYPE_CHECKING for type hints or Application services instead."
        )

    def test_all_http_files_no_runtime_infrastructure_imports(self):
        """Test that ALL files in http/ don't import infrastructure at runtime.

        Per architecture best practices, interfaces should not directly
        access infrastructure adapters at runtime. TYPE_CHECKING imports
        for type hints are allowed.
        """
        http_dir = SRC_PATH / "interfaces" / "http"
        assert http_dir.exists(), "http/ directory not found"

        violations = _http_runtime_infrastructure_violations(http_dir)

        assert violations == [], (
            "HTTP interface files should not import from infrastructure at runtime. "
            "Found violations:\n  - " + "\n  - ".join(violations) + "\n"
            "Use TYPE_CHECKING for type hints or Application services instead."
        )

    def test_http_type_checking_uses_domain_ports(self):
        """Verify http/ uses domain ports, not infrastructure imports.

        After refactoring (PR #1542), health_server.py imports from
        domain ports instead of infrastructure adapters.
        This is the correct architectural approach.
        """
        server_path = SRC_PATH / "interfaces" / "http" / "health_server.py"
        assert server_path.exists(), "health_server.py not found"

        with open(server_path) as f:
            content = f.read()

        # Verify domain port imports are used (correct architecture)
        assert "from bioetl.domain.ports import" in content, (
            "health_server.py should import from domain ports, not infrastructure"
        )
        assert "HealthMonitorPort" in content, (
            "health_server.py should use HealthMonitorPort from domain"
        )

        # Verify no infrastructure imports remain
        assert "bioetl.infrastructure.adapters.http.health_monitor" not in content, (
            "health_server.py should not import from infrastructure. "
            "Use domain ports instead."
        )
