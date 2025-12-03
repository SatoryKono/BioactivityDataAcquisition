"""
Pytest configuration and shared fixtures.
"""
import socket
from unittest.mock import MagicMock, Mock

import pandas as pd
import pytest

from bioetl.infrastructure.config.models import (
    HashingConfig,
    LoggingConfig,
    PipelineConfig,
    StorageConfig,
)
from bioetl.domain.providers import ProviderId
from bioetl.infrastructure.logging.contracts import LoggerAdapterABC
from bioetl.infrastructure.output.unified_writer import UnifiedOutputWriter
from bioetl.domain.validation.service import ValidationService


@pytest.fixture
def mock_config():
    """Create a mock pipeline configuration."""
    return PipelineConfig(
        provider=ProviderId.CHEMBL,
        entity_name="test_entity",
        logging=LoggingConfig(level="DEBUG"),
        storage=StorageConfig(output_path="./test_out"),
        hashing=HashingConfig(business_key_fields=["id"]),
        pipeline={}
    )


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    logger = MagicMock(spec=LoggerAdapterABC)
    logger.bind.return_value = logger
    return logger


@pytest.fixture
def mock_validation_service():
    """Create a mock validation service."""
    service = MagicMock(spec=ValidationService)
    # Default behavior: return df as is
    service.validate.side_effect = lambda df, **kwargs: df
    return service


@pytest.fixture
def mock_output_writer():
    """Create a mock output writer."""
    writer = MagicMock(spec=UnifiedOutputWriter)
    writer.write_result.return_value = Mock(row_count=10)
    return writer


@pytest.fixture
def sample_df():
    """Create a sample DataFrame."""
    return pd.DataFrame({
        "id": [1, 2, 3],
        "value": ["a", "b", "c"]
    })


@pytest.fixture
def pipeline_test_config(tmp_path_factory: pytest.TempPathFactory) -> PipelineConfig:
    """Pipeline config for integration-style unit tests."""
    output_dir = tmp_path_factory.mktemp("pipeline_output")
    return PipelineConfig(
        provider=ProviderId.CHEMBL,
        entity_name="test_entity",
        logging=LoggingConfig(level="DEBUG"),
        storage=StorageConfig(output_path=str(output_dir)),
        hashing=HashingConfig(business_key_fields=["id"]),
        pipeline={},
    )


@pytest.fixture
def small_pipeline_df() -> pd.DataFrame:
    """Tiny dataset used for pipeline dry-run tests."""
    return pd.DataFrame(
        {
            "id": [101, 202],
            "value": ["alpha", "beta"],
        }
    )


@pytest.fixture(autouse=True)
def disable_network_calls(monkeypatch, request):
    """Block network access unless marked with 'network' or 'integration'."""
    if (
        request.node.get_closest_marker("network") or
        request.node.get_closest_marker("integration")
    ):
        return

    def guard(*_args, **_kwargs):
        raise RuntimeError(
            "Network access disabled. Use @pytest.mark.network or "
            "@pytest.mark.integration to enable. "
            f"Test: {request.node.name}"
        )

    class GuardedSocket:
        """Mock socket that raises error on instantiation."""

        def __init__(self, *_args, **_kwargs):
            guard()

    monkeypatch.setattr(socket, "socket", GuardedSocket)
    monkeypatch.setattr(socket, "create_connection", guard)

# End of conftest
