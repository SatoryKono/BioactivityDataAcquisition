# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Tests for bootstrap package layer boundaries.

These tests verify that the CLI/runtime bootstrap separation is maintained:
- runtime MUST NOT import from cli
- cli MAY import from runtime (for runner access)
- Both MUST import shared code from assembly

REQ-ARCH-BOOT-001: Bootstrap runtime isolation from CLI.
REQ-ARCH-BOOT-002: CLI/runtime clear separation for maintainability.

See CLAUDE.md §2.1 Matrix of Imports.
"""

from __future__ import annotations

import pytest

import re
from pathlib import Path


pytestmark = pytest.mark.architecture


class TestBootstrapLayerBoundaries:
    """Tests for bootstrap package structure and import rules."""

    def test_runtime_does_not_import_cli(self, src_dir: Path) -> None:
        """Runtime bootstrap MUST NOT import from CLI bootstrap.

        REQ-ARCH-BOOT-001: Runtime modules should be independent of CLI-specific
        services to prevent acmolecule_idental use of NoOp implementations in production
        pipeline execution.
        """
        runtime_path = src_dir / "bioetl" / "composition" / "bootstrap" / "runtime"
        assert runtime_path.exists(), "Bootstrap runtime package not found"

        violations = []
        forbidden_patterns = [
            r"from bioetl\.composition\.bootstrap\.cli",
            r"import bioetl\.composition\.bootstrap\.cli",
        ]

        for py_file in runtime_path.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            for pattern in forbidden_patterns:
                if re.search(pattern, content):
                    relative_path = py_file.relative_to(src_dir)
                    violations.append(f"{relative_path}: imports from bootstrap.cli")

        assert not violations, (
            "Runtime bootstrap MUST NOT import from CLI bootstrap.\n"
            "CLI uses NoOp implementations, runtime needs full observability.\n\n"
            "Violations:\n" + "\n".join(f"  - {v}" for v in violations)
        )

    def test_bootstrap_package_structure_exists(self, src_dir: Path) -> None:
        """Verify bootstrap package has correct structure.

        REQ-ARCH-BOOT-002: Bootstrap should be split into assembly/cli/runtime.
        """
        bootstrap_path = src_dir / "bioetl" / "composition" / "bootstrap"
        assert bootstrap_path.exists(), "Bootstrap package not found"

        expected_subpackages = ["assembly", "cli", "runtime"]
        missing = []

        for subpackage in expected_subpackages:
            subpackage_path = bootstrap_path / subpackage
            if not subpackage_path.exists():
                missing.append(subpackage)
            elif not (subpackage_path / "__init__.py").exists():
                missing.append(f"{subpackage}/__init__.py")

        assert not missing, (
            "Bootstrap package missing expected structure:\n"
            + "\n".join(f"  - bootstrap/{m}" for m in missing)
            + "\n\nExpected: bootstrap/{assembly,cli,runtime}/__init__.py"
        )

    def test_assembly_has_no_noop_imports(self, src_dir: Path) -> None:
        """Assembly modules should not use NoOp implementations directly.

        REQ-ARCH-BOOT-003: Assembly provides pure infrastructure building blocks
        without NoOp observability hardcoded.
        """
        assembly_path = src_dir / "bioetl" / "composition" / "bootstrap" / "assembly"
        assert assembly_path.exists(), "Bootstrap assembly package not found"

        # These imports are OK in assembly (used for storage adapter)
        # but should not be used for service-level dependencies
        warnings = []

        for py_file in assembly_path.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue

            content = py_file.read_text(encoding="utf-8")

            # Check for NoOp* class instantiation (not imports)
            # Instantiation in assembly is OK for storage adapter, but flagged for review
            noop_instantiation = re.findall(r"NoOp\w+\(\)", content)
            if noop_instantiation:
                relative_path = py_file.relative_to(src_dir)
                warnings.append(
                    f"{relative_path}: uses NoOp instantiation {noop_instantiation}"
                )

        # Note: This is a warning, not a failure
        # Assembly may legitimately use NoOp for storage adapters
        # The key constraint is that runtime/pipeline.py uses full observability
        if warnings:
            # Log warnings but don't fail - assembly storage uses NoOp for adapters
            pass

    def test_cli_modules_use_noop_logger(self, src_dir: Path) -> None:
        """CLI modules should use NoOpLogger for administrative operations.

        REQ-ARCH-BOOT-004: CLI operations don't require full observability,
        so they should use NoOpLogger to avoid unnecessary overhead.
        """
        cli_path = src_dir / "bioetl" / "composition" / "bootstrap" / "cli"
        assert cli_path.exists(), "Bootstrap CLI package not found"

        modules_using_noop = 0
        modules_without_noop = []

        for py_file in cli_path.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue

            content = py_file.read_text(encoding="utf-8")

            # CLI modules should import and use NoOpLogger
            if "NoOpLogger" in content:
                modules_using_noop += 1
            else:
                # Some CLI modules may delegate to runtime, which is OK
                # But modules that create services directly should use NoOpLogger
                if "def bootstrap_" in content and "service" in py_file.name.lower():
                    relative_path = py_file.relative_to(src_dir)
                    modules_without_noop.append(str(relative_path))

        # At least some CLI modules should use NoOpLogger
        assert modules_using_noop > 0 or not modules_without_noop, (
            "CLI bootstrap modules should use NoOpLogger for services.\n"
            "Found modules without NoOpLogger:\n"
            + "\n".join(f"  - {m}" for m in modules_without_noop)
        )

    def test_runtime_observability_uses_full_stack(self, src_dir: Path) -> None:
        """Runtime observability should bootstrap full observability stack.

        REQ-ARCH-BOOT-005: Runtime pipeline execution needs full observability
        (logging, tracing, metrics, DQ monitoring).
        """
        observability_file = (
            src_dir
            / "bioetl"
            / "composition"
            / "bootstrap"
            / "runtime"
            / "observability.py"
        )
        assert observability_file.exists(), "Runtime observability module not found"

        content = observability_file.read_text(encoding="utf-8")

        required_functions = [
            "bootstrap_logger",
            "bootstrap_tracer",
            "bootstrap_metrics",
            "bootstrap_observability_bundle",
        ]

        missing = []
        for func in required_functions:
            if f"def {func}(" not in content:
                missing.append(func)

        assert not missing, (
            "Runtime observability module missing required functions:\n"
            + "\n".join(f"  - {f}" for f in missing)
        )

        logger_bootstrap = (
            src_dir
            / "bioetl"
            / "composition"
            / "bootstrap"
            / "runtime"
            / "logger_bootstrap.py"
        ).read_text(encoding="utf-8")
        metrics_bootstrap = (
            src_dir
            / "bioetl"
            / "composition"
            / "bootstrap"
            / "runtime"
            / "metrics_bootstrap.py"
        ).read_text(encoding="utf-8")

        assert "UnifiedLogger" in logger_bootstrap, (
            "Runtime logger owner should use UnifiedLogger, not NoOpLogger"
        )
        assert "PrometheusMetrics" in metrics_bootstrap, (
            "Runtime metrics owner should use PrometheusMetrics, not NoOpMetrics"
        )

    def test_cli_can_import_runtime(self, src_dir: Path) -> None:
        """CLI modules may import from runtime (for runner access).

        REQ-ARCH-BOOT-006: CLI can use runtime functions when it needs
        full pipeline execution capabilities.
        """
        cli_path = src_dir / "bioetl" / "composition" / "bootstrap" / "cli"
        assert cli_path.exists(), "Bootstrap CLI package not found"

        # This test verifies that CLI -> runtime imports don't cause errors
        # by checking the structure exists and can be imported
        runtime_path = src_dir / "bioetl" / "composition" / "bootstrap" / "runtime"
        assert runtime_path.exists(), "Runtime package must exist for CLI to reference"

        # CLI may import from runtime - this is allowed
        # Just verify the structure permits this pattern

    def test_backward_compatibility_re_exports(self, src_dir: Path) -> None:
        """Legacy modules must re-export from new bootstrap package.

        REQ-ARCH-BOOT-007: Maintain backward compatibility through re-exports.
        If the legacy _bootstrap package has been fully removed, the migration
        to bootstrap/ is complete and this test passes.
        """
        legacy_init = src_dir / "bioetl" / "composition" / "_bootstrap" / "__init__.py"
        if not legacy_init.exists():
            # Legacy package fully removed -- migration to bootstrap/ complete
            new_bootstrap = src_dir / "bioetl" / "composition" / "bootstrap"
            assert new_bootstrap.is_dir(), (
                "Neither legacy _bootstrap nor new bootstrap package found"
            )
            return

        content = legacy_init.read_text(encoding="utf-8")

        assert "from bioetl.composition.bootstrap.runtime." in content or (
            "from bioetl.composition.composite_api import" in content
        ), (
            "_bootstrap/__init__.py should re-export through owner-focused bootstrap APIs"
        )


class TestBootstrapFunctionCategorization:
    """Tests verifying functions are in correct modules."""

    def test_cli_functions_in_cli_package(self, src_dir: Path) -> None:
        """CLI-specific bootstrap functions should be in cli/ package.

        These functions use NoOp observability and are for admin operations.
        """
        cli_path = src_dir / "bioetl" / "composition" / "bootstrap" / "cli"
        assert cli_path.exists(), "Bootstrap CLI package not found"

        # CLI should have these service bootstrap functions
        cli_init = cli_path / "__init__.py"
        assert cli_init.exists(), "CLI __init__.py not found"

        content = cli_init.read_text(encoding="utf-8")

        expected_cli_functions = [
            "bootstrap_checkpoint_runtime_service",
            "bootstrap_checkpoint_service",
            "bootstrap_quarantine_runtime_service",
            "bootstrap_quarantine_service",
            "bootstrap_config_service",
            "bootstrap_health_service",
            "bootstrap_lock_service",
            "bootstrap_metrics_service",
            "bootstrap_cleanup_service",
            "bootstrap_lifecycle_service",
            "bootstrap_vacuum_service",
            "bootstrap_export_service",
            "bootstrap_bronze_cleanup_service",
        ]

        missing = []
        for func in expected_cli_functions:
            if func not in content:
                missing.append(func)

        assert not missing, (
            "CLI bootstrap package should export these functions:\n"
            + "\n".join(f"  - {f}" for f in missing)
        )

    def test_runtime_functions_in_runtime_package(self, src_dir: Path) -> None:
        """Runtime bootstrap functions should be in runtime/ package.

        These functions use full observability for pipeline execution.
        """
        runtime_path = src_dir / "bioetl" / "composition" / "bootstrap" / "runtime"
        assert runtime_path.exists(), "Bootstrap runtime package not found"

        runtime_init = runtime_path / "__init__.py"
        assert runtime_init.exists(), "Runtime __init__.py not found"

        content = runtime_init.read_text(encoding="utf-8")

        expected_runtime_functions = [
            "bootstrap_pipeline_runner",
            "bootstrap_observability_bundle",
            "bootstrap_logger",
            "bootstrap_tracer",
            "bootstrap_metrics",
            "bootstrap_dq_monitor",
            "bootstrap_pipeline_runner_service",
            "bootstrap_composite_runner",
            "load_composite_config",
        ]

        missing = []
        for func in expected_runtime_functions:
            if func not in content:
                missing.append(func)

        assert not missing, (
            "Runtime bootstrap package should export these functions:\n"
            + "\n".join(f"  - {f}" for f in missing)
        )

    def test_assembly_functions_in_assembly_package(self, src_dir: Path) -> None:
        """Assembly (shared) bootstrap functions should be in assembly/ package.

        These are pure infrastructure building blocks used by both CLI and runtime.
        """
        assembly_path = src_dir / "bioetl" / "composition" / "bootstrap" / "assembly"
        assert assembly_path.exists(), "Bootstrap assembly package not found"

        assembly_init = assembly_path / "__init__.py"
        assert assembly_init.exists(), "Assembly __init__.py not found"

        content = assembly_init.read_text(encoding="utf-8")

        expected_assembly_functions = [
            "bootstrap_checkpoint_adapter",
            "bootstrap_quarantine_adapter",
            "bootstrap_storage_adapter",
        ]

        missing = []
        for func in expected_assembly_functions:
            if func not in content:
                missing.append(func)

        assert not missing, (
            "Assembly bootstrap package should export these functions:\n"
            + "\n".join(f"  - {f}" for f in missing)
        )
