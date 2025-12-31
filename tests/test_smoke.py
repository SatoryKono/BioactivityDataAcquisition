"""Smoke tests for quick sanity checks.

These tests verify critical paths work correctly and should complete in < 30s total.
Run with: make smoke
"""

from __future__ import annotations

import pytest


@pytest.mark.smoke
class TestCriticalImports:
    """Verify all critical modules can be imported."""

    def test_import_domain(self) -> None:
        """Domain layer imports successfully."""
        from bioetl import domain

        assert domain is not None

    def test_import_application(self) -> None:
        """Application layer imports successfully."""
        from bioetl import application

        assert application is not None

    def test_import_infrastructure(self) -> None:
        """Infrastructure layer imports successfully."""
        from bioetl import infrastructure

        assert infrastructure is not None

    def test_import_composition(self) -> None:
        """Composition layer imports successfully."""
        from bioetl import composition

        assert composition is not None

    def test_import_interfaces(self) -> None:
        """Interfaces layer imports successfully."""
        from bioetl import interfaces

        assert interfaces is not None


@pytest.mark.smoke
class TestCriticalPorts:
    """Verify critical ports are accessible."""

    def test_storage_port_exists(self) -> None:
        """StoragePort protocol is importable."""
        from bioetl.domain.ports import StoragePort

        assert StoragePort is not None

    def test_lock_port_exists(self) -> None:
        """LockPort protocol is importable."""
        from bioetl.domain.ports import LockPort

        assert LockPort is not None

    def test_metrics_port_exists(self) -> None:
        """MetricsPort protocol is importable."""
        from bioetl.domain.ports import MetricsPort

        assert MetricsPort is not None


@pytest.mark.smoke
class TestCriticalTypes:
    """Verify critical types work correctly."""

    def test_run_id_type(self) -> None:
        """RunID type is defined."""
        from uuid import uuid4

        from bioetl.domain.types import RunID

        # RunID is a NewType wrapper around UUID
        run_id = RunID(uuid4())
        assert run_id is not None
        assert len(str(run_id)) > 0

    def test_content_hash_type(self) -> None:
        """ContentHash type is defined."""
        from bioetl.domain.types import ContentHash

        # ContentHash is a NewType wrapper around str
        hash_val = ContentHash("test_hash_value")
        assert hash_val is not None

    def test_run_type_enum(self) -> None:
        """RunType enum values exist."""
        from bioetl.domain.types import RunType

        assert RunType.INCREMENTAL.value == "incremental"
        assert RunType.BACKFILL.value == "backfill"
        assert RunType.REBUILD.value == "rebuild"


@pytest.mark.smoke
class TestCLI:
    """Verify CLI entry point works."""

    def test_cli_main_importable(self) -> None:
        """CLI main function is importable."""
        from bioetl.interfaces.cli import main

        assert callable(main)

    def test_cli_group_importable(self) -> None:
        """CLI click group is importable."""
        from bioetl.interfaces.cli.main import cli

        assert cli is not None

    def test_cli_help(self) -> None:
        """CLI --help works without errors."""
        from click.testing import CliRunner

        from bioetl.interfaces.cli.main import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Usage:" in result.output


@pytest.mark.smoke
class TestBootstrap:
    """Verify bootstrap functions are accessible."""

    def test_bootstrap_pipeline_importable(self) -> None:
        """bootstrap_pipeline function is importable."""
        from bioetl.composition.bootstrap import bootstrap_pipeline

        assert callable(bootstrap_pipeline)

    def test_pipeline_registry_importable(self) -> None:
        """PipelineRegistry is importable."""
        from bioetl.composition.registry import PipelineRegistry

        assert PipelineRegistry is not None
