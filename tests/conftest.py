"""
Pytest configuration and shared fixtures.
"""
from unittest.mock import MagicMock, Mock

import pandas as pd
import pytest

from bioetl.config.models import LoggingConfig, PipelineConfig, StorageConfig
from bioetl.logging.contracts import LoggerAdapterABC
from bioetl.output.unified_writer import UnifiedOutputWriter
from bioetl.validation.service import ValidationService


@pytest.fixture
def mock_config():
    """Create a mock pipeline configuration."""
    return PipelineConfig(
        provider="test_provider",
        entity_name="test_entity",
        logging=LoggingConfig(level="DEBUG"),
        storage=StorageConfig(output_path="./test_out"),
        business_key=["id"],
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
