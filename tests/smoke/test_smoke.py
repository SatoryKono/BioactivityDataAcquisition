"""Smoke tests for quick sanity checks during local development.

These tests verify that:
1. Core modules import successfully
2. Basic domain objects work correctly
3. CLI is loadable
4. Layer boundaries are not violated

Run with: make test-smoke
"""

from __future__ import annotations

import subprocess
import sys
import pytest


@pytest.mark.smoke
class TestRuntimeDependencies:
    """Verify critical runtime dependencies are installed and importable."""

    @staticmethod
    def check_module_importable_isolated(module_name: str) -> None:
        command = [
            sys.executable,
            "-c",
            f"import importlib; importlib.import_module({module_name!r})",
        ]
        try:
            proc = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=60,  # Increased timeout for heavy dependencies (polars, pandas, etc.)
            )
        except subprocess.TimeoutExpired as err:
            pytest.fail(
                f"Timed out importing runtime dependency {module_name} after 60s in an"
                f" isolated process.\n{err}"
            )
        assert proc.returncode == 0, (
            f"Failed to import runtime dependency {module_name}: {proc.stdout}"
            f"{proc.stderr}"
        )

    @pytest.mark.parametrize(
        "module_name",
        [
            "pandas",
            "pandera",
            "polars",
            "deltalake",
            "pyarrow",
            "httpx",
            "pydantic",
            "pydantic_settings",
            "yaml",
            "structlog",
            "click",
            "orjson",
            "prometheus_client",
            "zstandard",
            "pubchempy",
        ],
    )
    def test_runtime_dependency_importable(self, module_name: str) -> None:
        """Each critical dependency must be importable."""
        self.check_module_importable_isolated(module_name)


@pytest.mark.smoke
class TestDevDependencies:
    """Verify critical development dependencies are installed and importable."""

    @pytest.mark.parametrize(
        "module_name",
        [
            # "detect_secrets",  # Temporarily disabled due to installation issues
            "pytest",
            "hypothesis",
            "vcr",
            "psutil",
        ],
    )
    def test_dev_dependency_importable(self, module_name: str) -> None:
        """Each critical dev dependency must be importable."""
        import importlib

        module = importlib.import_module(module_name)
        assert module is not None

    @pytest.mark.parametrize(
        "module_name",
        [
            "mypy",
            "importlinter",
            "radon",
            "xenon",
        ],
    )
    def test_dev_only_dependency_importable(self, module_name: str) -> None:
        """Dev-only dependencies (from [dev] extra) must be importable when installed."""
        module = pytest.importorskip(
            module_name,
            reason=f"{module_name} requires [dev] extra",
        )
        assert module is not None


@pytest.mark.smoke
class TestCoreImports:
    """Verify core modules import without errors."""

    def test_domain_imports(self) -> None:
        """Domain layer imports successfully."""
        from bioetl.domain import config, ports, types

        assert config is not None
        assert ports is not None
        assert types is not None

    def test_application_imports(self) -> None:
        """Application layer imports successfully."""
        from bioetl.application.core import base_transformer
        from bioetl.application.core import runner

        assert base_transformer is not None
        assert runner is not None

    @pytest.mark.timeout(120)  # Extended timeout for polars import
    def test_infrastructure_imports(self) -> None:
        """Infrastructure layer imports successfully."""
        from bioetl.infrastructure.storage import bronze_writer
        from bioetl.infrastructure.storage import silver_writer

        assert bronze_writer is not None
        assert silver_writer is not None

    def test_composition_imports(self) -> None:
        """Composition layer imports successfully."""
        from bioetl.composition import bootstrap
        from bioetl.composition import entrypoints

        assert bootstrap is not None
        assert entrypoints is not None

    def test_cli_imports(self) -> None:
        """CLI module imports successfully."""
        import bioetl.interfaces.cli

        assert bioetl.interfaces.cli is not None


@pytest.mark.smoke
class TestDomainTypes:
    """Verify domain types work correctly."""

    def test_run_type_enum(self) -> None:
        """RunType enum has expected values."""
        from bioetl.domain.types import RunType

        assert RunType.INCREMENTAL.value == "incremental"
        assert RunType.BACKFILL.value == "backfill"
        assert RunType.REBUILD.value == "rebuild"

    def test_health_status_enum(self) -> None:
        """HealthStatus enum has expected values."""
        from bioetl.domain.types import HealthStatus

        assert HealthStatus.HEALTHY.to_metric_value() == 2
        assert HealthStatus.DEGRADED.to_metric_value() == 1
        assert HealthStatus.UNHEALTHY.to_metric_value() == 0

    def test_error_type_classification(self) -> None:
        """ErrorType enum classifies errors correctly."""
        from bioetl.domain.types import ErrorType

        assert ErrorType.RATE_LIMIT.is_recoverable()
        assert ErrorType.NETWORK_ERROR.is_recoverable()
        assert not ErrorType.AUTH_FAILURE.is_recoverable()
        assert ErrorType.AUTH_FAILURE.is_critical()


@pytest.mark.smoke
class TestDomainConfig:
    """Verify domain configuration works."""

    def test_dq_config_defaults(self) -> None:
        """DQConfig has expected default thresholds."""
        from bioetl.domain.config import DQConfig

        config = DQConfig()
        assert config.soft_fail_threshold == pytest.approx(0.05)
        assert config.hard_fail_threshold == pytest.approx(0.20)

    def test_runtime_config_defaults(self) -> None:
        """RuntimeConfig has expected defaults."""
        from bioetl.domain.config import RuntimeConfig
        from bioetl.domain.types import RunType

        config = RuntimeConfig(run_type=RunType.INCREMENTAL)
        assert config.heartbeat_interval == 30
        assert config.lock_ttl == 90
        assert config.dry_run is False


@pytest.mark.smoke
class TestPortsExist:
    """Verify core ports are defined."""

    def test_storage_ports(self) -> None:
        """Narrow storage protocols exist."""
        from bioetl.domain.ports import (
            BronzeStoragePort,
            GoldStoragePort,
            SilverStoragePort,
            StorageMaintenancePort,
        )

        assert hasattr(BronzeStoragePort, "write_bronze")
        assert hasattr(SilverStoragePort, "write_silver")
        assert hasattr(GoldStoragePort, "write_gold")
        assert hasattr(StorageMaintenancePort, "preview_cleanup")

    def test_lock_port(self) -> None:
        """LockPort protocol exists."""
        from bioetl.domain.ports import LockPort

        assert hasattr(LockPort, "acquire")
        assert hasattr(LockPort, "release")

    def test_checkpoint_port(self) -> None:
        """CheckpointPort protocol exists."""
        from bioetl.domain.ports import CheckpointPort

        assert hasattr(CheckpointPort, "load")
        assert hasattr(CheckpointPort, "save")


@pytest.mark.smoke
class TestLayerBoundaries:
    """Quick layer boundary sanity checks."""

    def test_domain_has_no_httpx(self) -> None:
        """Domain layer does not import httpx."""
        import sys

        import bioetl.domain  # noqa: F401 - import for side effect
        import bioetl.domain as domain  # noqa: F401

        domain_modules = [
            name for name in sys.modules if name.startswith("bioetl.domain")
        ]
        for mod_name in domain_modules:
            mod = sys.modules.get(mod_name)
            if mod and hasattr(mod, "__file__") and mod.__file__:
                # Check the module doesn't have httpx in its namespace
                assert not hasattr(mod, "httpx"), f"{mod_name} imports httpx"

    def test_domain_has_no_polars(self) -> None:
        """Domain layer does not import polars directly."""
        import sys

        import bioetl.domain  # noqa: F401 - import for side effect
        import bioetl.domain as domain  # noqa: F401

        domain_modules = [
            name for name in sys.modules if name.startswith("bioetl.domain")
        ]
        for mod_name in domain_modules:
            mod = sys.modules.get(mod_name)
            if mod and hasattr(mod, "__file__") and mod.__file__:
                assert not hasattr(mod, "polars"), f"{mod_name} imports polars"


@pytest.mark.smoke
class TestCLILoadable:
    """Verify CLI is loadable and has expected commands."""

    def test_cli_main_exists(self) -> None:
        """CLI main function exists."""
        from bioetl.interfaces.cli import main

        assert callable(main)

    def test_cli_is_click_group(self) -> None:
        """CLI group is a Click group."""
        import click

        from bioetl.interfaces.cli import cli

        assert isinstance(cli, click.core.Group)
