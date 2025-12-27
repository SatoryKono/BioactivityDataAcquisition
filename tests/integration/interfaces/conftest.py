"""Fixtures for CLI integration tests.

Provides common fixtures for testing CLI commands with in-memory fakes.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import patch
from uuid import uuid4

import pytest
from click.testing import CliRunner

from bioetl.composition.factories.storage import StorageAdapter, StorageContext
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.observability.noop_metrics import NoOpMetrics
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.delta_writer import DeltaWriter
from bioetl.infrastructure.storage.gold_writer import GoldWriter
from tests.fakes.checkpoint_fake import InMemoryCheckpoint
from tests.fakes.quarantine_fake import InMemoryQuarantine

if TYPE_CHECKING:
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a Click CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def run_id():
    """Generate a unique run ID for tests."""
    return uuid4()


@pytest.fixture
def fake_checkpoint() -> InMemoryCheckpoint:
    """Create an in-memory checkpoint store."""
    return InMemoryCheckpoint()


@pytest.fixture
def fake_quarantine() -> InMemoryQuarantine:
    """Create an in-memory quarantine store."""
    return InMemoryQuarantine()


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
            from bioetl.infrastructure.config import get_pipeline_config, get_settings

            get_settings.cache_clear()
            get_pipeline_config.cache_clear()
        except (ImportError, AttributeError):
            pass

        yield env_vars

        # Clear cache after test
        try:
            from bioetl.infrastructure.config import get_pipeline_config, get_settings

            get_settings.cache_clear()
            get_pipeline_config.cache_clear()
        except (ImportError, AttributeError):
            pass


def create_local_storage_context(
    storage_paths: dict[str, Path],
    config: PipelineYamlConfig,
    logger: Any = None,
) -> StorageContext:
    """Create a StorageContext pointing to local temp paths."""
    if logger is None:
        logger = NoOpLogger()

    bronze_config = config.sink.get("bronze")
    save_json = bronze_config.save_json if bronze_config else False

    adapter = StorageAdapter(
        bronze_writer=BronzeWriter(
            base_path=str(storage_paths["bronze"]),
            logger=logger,
            metrics=NoOpMetrics(),
            save_json=save_json,
            json_path=str(storage_paths["json"]) if save_json else None,
        ),
        silver_writer=DeltaWriter(
            base_path=str(storage_paths["silver"]),
            logger=logger,
            csv_exporter=None,
        ),
        gold_writer=GoldWriter(
            base_path=str(storage_paths["gold"]),
            logger=logger,
            csv_exporter=None,
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
    """Patch bootstrap_checkpoint to return fake checkpoint."""
    with patch(
        "bioetl.composition.bootstrap.bootstrap_checkpoint",
        return_value=fake_checkpoint,
    ):
        yield fake_checkpoint


@pytest.fixture
def patch_quarantine(fake_quarantine: InMemoryQuarantine):
    """Patch bootstrap_quarantine to return fake quarantine."""
    with patch(
        "bioetl.composition.bootstrap.bootstrap_quarantine",
        return_value=fake_quarantine,
    ):
        yield fake_quarantine


@pytest.fixture(scope="module")
def vcr_cassette_dir(request: pytest.FixtureRequest, project_root: Path) -> Path:
    """Return the directory for VCR cassettes based on test module."""
    cassette_dir = (
        project_root / "tests" / "fixtures" / "vcr" / "integration" / "interfaces"
    )
    cassette_dir.mkdir(parents=True, exist_ok=True)
    return cassette_dir


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Returns the root directory of the project."""
    return Path(__file__).parent.parent.parent.parent
