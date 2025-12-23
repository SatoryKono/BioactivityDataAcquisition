"""Fixtures for E2E tests with local infrastructure."""

import os
from pathlib import Path

import pytest


@pytest.fixture(scope="session", autouse=True)
def e2e_environment():
    """Set up environment for E2E tests."""
    # Set test environment variables
    os.environ["BIOETL_ENV"] = "dev"
    os.environ["BIOETL_TEST_MODE"] = "true"

    yield

    # Cleanup settings cache after session
    try:
        from bioetl.infrastructure.config import get_settings

        get_settings.cache_clear()
    except ImportError:
        pass


@pytest.fixture
def e2e_temp_storage(tmp_path: Path) -> dict[str, Path]:
    """Create temporary directories for E2E test storage.

    Returns:
        dict: Paths for bronze, silver, gold, checkpoints, and quarantine
    """
    bronze_path = tmp_path / "bronze"
    silver_path = tmp_path / "silver"
    gold_path = tmp_path / "gold"
    checkpoints_path = tmp_path / "checkpoints"
    quarantine_path = tmp_path / "quarantine"

    bronze_path.mkdir()
    silver_path.mkdir()
    gold_path.mkdir()
    checkpoints_path.mkdir()
    quarantine_path.mkdir()

    return {
        "bronze": bronze_path,
        "silver": silver_path,
        "gold": gold_path,
        "checkpoints": checkpoints_path,
        "quarantine": quarantine_path,
    }


@pytest.fixture
def e2e_data_dir(tmp_path: Path, monkeypatch) -> Path:
    """Create a temporary data directory and configure settings."""
    data_dir = tmp_path / "bioetl_data"
    data_dir.mkdir(parents=True, exist_ok=True)

    # Create subdirectories
    (data_dir / "bronze").mkdir()
    (data_dir / "silver").mkdir()
    (data_dir / "gold").mkdir()
    (data_dir / "checkpoints").mkdir()
    (data_dir / "quarantine").mkdir()

    # Set environment variable
    monkeypatch.setenv("BIOETL_DATA_DIR", str(data_dir))

    # Clear settings cache
    try:
        from bioetl.infrastructure.config import get_pipeline_config, get_settings

        get_settings.cache_clear()
        get_pipeline_config.cache_clear()
    except ImportError:
        pass

    yield data_dir

    # Cleanup
    try:
        from bioetl.infrastructure.config import get_pipeline_config, get_settings

        get_settings.cache_clear()
        get_pipeline_config.cache_clear()
    except ImportError:
        pass


@pytest.fixture
def e2e_pipeline_limit() -> int:
    """Limit number of records for E2E tests to keep them fast."""
    return 10


@pytest.fixture
def e2e_vcr_disabled():
    """Ensure VCR is disabled for E2E tests (we want real HTTP calls)."""
    # E2E tests should make real HTTP calls, not use VCR cassettes
    # This fixture serves as a marker/documentation
    pass
