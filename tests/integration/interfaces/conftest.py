"""Fixtures for CLI integration tests.

Provides common fixtures for testing CLI commands with in-memory fakes.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import patch
from tests.helpers.deterministic_ids import deterministic_uuid_from_callsite

import pytest

if TYPE_CHECKING:
    from click.testing import CliRunner

    from bioetl.composition.factories.storage import StorageContext
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig
    from tests.fakes.checkpoint_fake import InMemoryCheckpoint
    from tests.fakes.quarantine_fake import InMemoryQuarantine


def _create_cli_runner() -> CliRunner:
    from click.testing import CliRunner

    return CliRunner()


def _create_in_memory_checkpoint() -> InMemoryCheckpoint:
    from tests.fakes.checkpoint_fake import InMemoryCheckpoint

    return InMemoryCheckpoint()


def _create_in_memory_quarantine() -> InMemoryQuarantine:
    from tests.fakes.quarantine_fake import InMemoryQuarantine

    return InMemoryQuarantine()


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a Click CLI runner for testing."""
    return _create_cli_runner()


@pytest.fixture
def cli_entrypoint():
    """Import the Click CLI lazily so collect-only avoids command bootstrap."""
    from bioetl.interfaces.cli import cli

    return cli


@pytest.fixture
def run_id():
    """Generate a unique run ID for tests."""
    return deterministic_uuid_from_callsite("interfaces.conftest")


@pytest.fixture
def fake_checkpoint() -> InMemoryCheckpoint:
    """Create an in-memory checkpoint store."""
    return _create_in_memory_checkpoint()


@pytest.fixture
def fake_quarantine() -> InMemoryQuarantine:
    """Create an in-memory quarantine store."""
    return _create_in_memory_quarantine()


@pytest.fixture
def storage_paths(tmp_path: Path) -> dict[str, Path]:
    """Create temporary storage paths for testing."""
    paths = {
        "bronze": tmp_path / "bronze",
        "silver": tmp_path / "silver",
        "gold": tmp_path / "gold",
        "checkpoints": tmp_path / "checkpoints",
        "json": tmp_path / "json",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


@pytest.fixture
def temp_env(storage_paths: dict[str, Path]):
    """Set up temporary environment variables for testing."""
    env_vars = {
        "BIOETL_ENV": "dev",
        "BIOETL_BRONZE_PATH": str(storage_paths["bronze"]),
        "BIOETL_SILVER_PATH": str(storage_paths["silver"]),
        "BIOETL_GOLD_PATH": str(storage_paths["gold"]),
        "BIOETL_CHECKPOINT_PATH": str(storage_paths["checkpoints"]),
    }

    with patch.dict(os.environ, env_vars, clear=False):
        # Clear settings cache to pick up new env vars
        try:
            from bioetl.infrastructure.config._base import (
                get_pipeline_config,
                get_settings,
            )

            get_settings.cache_clear()
            get_pipeline_config.cache_clear()
        except (ImportError, AttributeError):
            pass

        yield env_vars

        # Clear cache after test
        try:
            from bioetl.infrastructure.config._base import (
                get_pipeline_config,
                get_settings,
            )

            get_settings.cache_clear()
            get_pipeline_config.cache_clear()
        except (ImportError, AttributeError):
            pass


@pytest.fixture(autouse=True)
def disable_detached_observability_backend_for_cli_integration_tests():
    """Keep CLI integration tests free from detached backend side effects."""
    from bioetl.interfaces.cli.commands.domains.health.observability_backend_runtime import (
        ObservabilityBackendEnsureResult,
    )

    disabled_result = ObservabilityBackendEnsureResult(
        status="disabled",
        health_url="http://127.0.0.1:8081/health",
        message="Disabled for CLI integration tests.",
    )

    with (
        patch(
            "bioetl.interfaces.cli.commands.run.ensure_observability_backend_started",
            return_value=disabled_result,
        ),
        patch(
            "bioetl.interfaces.cli.commands.run_all.ensure_observability_backend_started",
            return_value=disabled_result,
        ),
        patch(
            "bioetl.interfaces.cli.commands.run_composite.ensure_observability_backend_started",
            return_value=disabled_result,
        ),
        patch(
            "bioetl.interfaces.cli.commands.workflow.ensure_observability_backend_started",
            return_value=disabled_result,
        ),
    ):
        yield


def create_local_storage_context(
    storage_paths: dict[str, Path],
    config: PipelineYamlConfig,
    logger: Any = None,
) -> StorageContext:
    """Create a StorageContext pointing to local temp paths."""
    from bioetl.composition.factories.storage import StorageBundle, StorageContext
    from bioetl.domain.ports.noop import NoOpMetrics
    from bioetl.infrastructure.observability.noop_logger import NoOpLogger
    from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
    from bioetl.infrastructure.storage.gold_writer import GoldWriter
    from bioetl.infrastructure.storage.silver_writer import SilverWriter

    if logger is None:
        logger = NoOpLogger()

    bronze_config = config.sink.get("bronze")
    save_json = bronze_config.save_json if bronze_config else False

    adapter = StorageBundle(
        bronze_writer=BronzeWriter(
            base_path=str(storage_paths["bronze"]),
            logger=logger,
            metrics=NoOpMetrics(),
            save_json=save_json,
            json_path=str(storage_paths["json"]) if save_json else None,
            # Lock validation at Application layer
        ),
        silver_writer=SilverWriter(
            base_path=str(storage_paths["silver"]),
            logger=logger,
            # Lock validation at Application layer
        ),
        gold_writer=GoldWriter(
            base_path=str(storage_paths["gold"]),
            logger=logger,
            # Lock validation at Application layer
        ),
    )

    return StorageContext(
        adapter=adapter,
        bronze_path=str(storage_paths["bronze"]),
        silver_path=str(storage_paths["silver"]),
        gold_path=str(storage_paths["gold"]),
        checkpoints_path=str(storage_paths["checkpoints"]),
    )


@pytest.fixture
def patch_storage_factory(storage_paths: dict[str, Path]):
    """Patch StorageFactory to use local temp paths."""

    def _create_storage(
        settings: Any, config: PipelineYamlConfig, logger: Any
    ) -> StorageContext:
        return create_local_storage_context(storage_paths, config, logger)

    with patch(
        "bioetl.composition.factories.storage.StorageFactory.create",
        side_effect=_create_storage,
    ):
        yield


@pytest.fixture
def patch_checkpoint(fake_checkpoint: InMemoryCheckpoint):
    """Patch bootstrap_checkpoint_adapter to return fake checkpoint."""
    with patch(
        "bioetl.composition.bootstrap.bootstrap_checkpoint_adapter",
        return_value=fake_checkpoint,
    ):
        yield fake_checkpoint


@pytest.fixture
def patch_quarantine(fake_quarantine: InMemoryQuarantine):
    """Patch bootstrap_quarantine_adapter to return fake quarantine."""
    with patch(
        "bioetl.composition.bootstrap.bootstrap_quarantine_adapter",
        return_value=fake_quarantine,
    ):
        yield fake_quarantine


@pytest.fixture
def registered_pipelines() -> None:
    """Register pipelines lazily for tests that exercise CLI run commands."""
    # Lazy import to avoid timeout on Windows during test collection
    from bioetl.composition.factories.pipeline.registry import register_all_pipelines

    register_all_pipelines()


@pytest.fixture(scope="module")
def vcr_cassette_dir(request: pytest.FixtureRequest, project_root: Path) -> Path:
    """Return the directory for VCR cassettes based on test module."""
    cassette_dir = (
        project_root / "tests" / "fixtures" / "vcr" / "integration" / "interfaces"
    )
    cassette_dir.mkdir(parents=True, exist_ok=True)
    return cassette_dir
