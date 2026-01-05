"""Architecture tests for interfaces layer dependencies.

Ensures that CLI and other interfaces don't directly import from infrastructure,
enforcing proper dependency flow through Application layer services.

Per RULES.md §1.1, interfaces should use Application services for administrative
operations, not access infrastructure adapters directly.
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
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)

    return imports


@pytest.mark.architecture
class TestInterfacesNoDIrectInfrastructure:
    """Test that interfaces don't directly import infrastructure."""

    def test_cli_no_infrastructure_imports(self):
        """Test that CLI doesn't import from infrastructure directly."""
        # CLI is now in a package structure: interfaces/cli/main.py
        cli_path = SRC_PATH / "interfaces" / "cli" / "main.py"

        if not cli_path.exists():
            pytest.skip("CLI main.py not found")

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

        if not cli_path.exists():
            pytest.skip("CLI main.py not found")

        imports = get_imports_from_file(cli_path)

        bootstrap_imports = [imp for imp in imports if "composition._bootstrap" in imp]

        assert bootstrap_imports == [], (
            f"CLI should not import from _bootstrap. "
            f"Found: {bootstrap_imports}. "
            f"Use composition.entrypoints instead."
        )

    def test_all_cli_commands_no_infrastructure_imports(self):
        """Test that ALL CLI command files don't import infrastructure.

        Per RULES.md §1.1 layer matrix, interfaces should not directly
        access infrastructure adapters. CLI commands should use
        Application services or Composition entrypoints instead.

        Note: While the architecture matrix technically allows interfaces → infrastructure,
        we prefer routing through Application services for consistency and testability.
        """
        commands_dir = SRC_PATH / "interfaces" / "cli" / "commands"

        if not commands_dir.exists():
            pytest.skip("CLI commands directory not found")

        # Known legacy violations - these should be addressed in future refactoring
        # but are allowed for now to prevent regression in new code
        allowed_legacy_files = {
            # quarantine.py uses infrastructure config and quarantine directly
            # TODO: Route through QuarantineService
            "quarantine.py",
            # health.py uses health_monitor and prometheus_metrics directly
            # TODO: Route through HealthService
            "health.py",
            # config.py uses infrastructure config directly
            # TODO: Route through ConfigService or Composition
            "config.py",
        }

        violations = []

        for py_file in commands_dir.glob("*.py"):
            # Skip __init__.py as it typically just re-exports
            if py_file.name == "__init__.py":
                continue

            # Skip known legacy files (documented above)
            if py_file.name in allowed_legacy_files:
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

        if not commands_dir.exists():
            pytest.skip("CLI commands directory not found")

        # Expected legacy violations - keep in sync with test above
        expected_violations = {
            "quarantine.py": [
                "bioetl.infrastructure.config",
                "bioetl.infrastructure.quarantine.unified",
            ],
            "health.py": [
                "bioetl.infrastructure.adapters.http.health_monitor",
                "bioetl.infrastructure.observability.prometheus_metrics",
            ],
            "config.py": ["bioetl.infrastructure.config"],
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

        if not init_path.exists():
            pytest.skip("interfaces __init__ not found")

        imports = get_imports_from_file(init_path)

        infrastructure_imports = [
            imp for imp in imports if "bioetl.infrastructure" in imp
        ]

        # Note: observability.py may still import from infrastructure
        # as per the architecture matrix (interfaces → infrastructure is allowed)
        # but we want to track this for awareness
        if infrastructure_imports:
            pytest.xfail(
                f"interfaces/__init__ imports from infrastructure: {infrastructure_imports}"
            )

    def test_observability_allowed_infrastructure(self):
        """Document that observability.py is allowed infrastructure imports.

        Per architecture matrix, interfaces → infrastructure is technically allowed,
        but we prefer routing through Application layer for consistency.
        This test documents the current state.
        """
        obs_path = SRC_PATH / "interfaces" / "observability.py"

        if not obs_path.exists():
            pytest.skip("observability.py not found")

        imports = get_imports_from_file(obs_path)

        infrastructure_imports = [
            imp for imp in imports if "bioetl.infrastructure" in imp
        ]

        # This is allowed but documented for future refactoring consideration
        if infrastructure_imports:
            # Just pass - this is expected and allowed
            pass


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
class TestEntrypointsExportServices:
    """Test that entrypoints exports the new services."""

    def test_entrypoints_exports_services(self):
        """Test that entrypoints exports getter functions for services."""
        from bioetl.composition import entrypoints

        # Check that getter functions exist
        assert hasattr(
            entrypoints, "get_checkpoint_service"
        ), "entrypoints should export get_checkpoint_service"
        assert hasattr(
            entrypoints, "get_quarantine_service"
        ), "entrypoints should export get_quarantine_service"
        assert hasattr(
            entrypoints, "get_bronze_cleanup_service"
        ), "entrypoints should export get_bronze_cleanup_service"

    def test_entrypoints_all_includes_services(self):
        """Test that __all__ includes service getters."""
        from bioetl.composition import entrypoints

        assert "get_checkpoint_service" in entrypoints.__all__
        assert "get_quarantine_service" in entrypoints.__all__
        assert "get_bronze_cleanup_service" in entrypoints.__all__
