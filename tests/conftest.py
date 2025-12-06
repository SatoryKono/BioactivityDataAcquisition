"""
Pytest configuration and shared fixtures.
"""

import socket
from typing import cast
from unittest.mock import MagicMock, Mock

import pandas as pd
import pytest
from pydantic import AnyHttpUrl

from bioetl.config.pipeline_config_schema import (
    HashingConfig,
    LoggingConfig,
    PipelineConfig,
    StorageConfig,
)
from bioetl.domain.validation.service import ValidationService
from bioetl.infrastructure.config.models import ChemblSourceConfig
from bioetl.infrastructure.logging.contracts import LoggerAdapterABC
from bioetl.infrastructure.output.unified_writer import UnifiedOutputWriter

# Workaround for Hypothesis issue with Python 3.13 and SimpleNamespace modules
# Hypothesis tries to create a set from sys.modules.values(), but some modules
# are SimpleNamespace objects which are not hashable.
# This patch is applied early via pytest_configure hook.


def pytest_configure(config):
    """Apply Hypothesis compatibility patch for Python 3.13."""
    try:
        # Import and patch before Hypothesis is used
        from hypothesis.internal.conjecture import providers as hypothesis_providers

        _original_get_local_constants = hypothesis_providers._get_local_constants

        def _patched_get_local_constants():
            """Patched version that filters out unhashable modules."""
            try:
                return _original_get_local_constants()
            except TypeError as e:
                if "unhashable type" in str(e):
                    # Filter out SimpleNamespace modules before creating set
                    # This is a workaround for Python 3.13 compatibility
                    import sys
                    from types import SimpleNamespace

                    # Create filtered modules dict
                    filtered_modules = {
                        k: v
                        for k, v in sys.modules.items()
                        if not isinstance(v, SimpleNamespace)
                    }

                    # Temporarily replace sys.modules
                    original_modules = dict(sys.modules)
                    try:
                        sys.modules.clear()
                        sys.modules.update(filtered_modules)
                        return _original_get_local_constants()
                    finally:
                        # Restore original
                        sys.modules.clear()
                        sys.modules.update(original_modules)
                raise

        hypothesis_providers._get_local_constants = _patched_get_local_constants
    except (ImportError, AttributeError):
        # Hypothesis not available or structure changed, skip patch
        pass


@pytest.fixture
def mock_config():
    """Create a mock pipeline configuration."""
    return PipelineConfig(
        id="chembl.test_entity",
        provider="chembl",
        entity="test_entity",
        input_mode="auto_detect",
        input_path=None,
        output_path="./test_out",
        batch_size=10,
        provider_config=ChemblSourceConfig(
            base_url=cast(AnyHttpUrl, "https://www.ebi.ac.uk/chembl/api/data"),
            timeout_sec=30,
            max_retries=3,
            rate_limit_per_sec=10.0,
        ),
        logging=LoggingConfig(level="DEBUG"),
        storage=StorageConfig(output_path="./test_out"),
        hashing=HashingConfig(business_key_fields=["id"]),
        pipeline={},
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
    service.get_schema_columns.return_value = []
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
    return pd.DataFrame({"id": [1, 2, 3], "value": ["a", "b", "c"]})


@pytest.fixture
def pipeline_test_config(tmp_path_factory: pytest.TempPathFactory) -> PipelineConfig:
    """Pipeline config for integration-style unit tests."""
    output_dir = tmp_path_factory.mktemp("pipeline_output")
    return PipelineConfig(
        id="chembl.test_entity",
        provider="chembl",
        entity="test_entity",
        input_mode="auto_detect",
        input_path=None,
        output_path=str(output_dir),
        batch_size=10,
        provider_config=ChemblSourceConfig(
            base_url=cast(AnyHttpUrl, "https://www.ebi.ac.uk/chembl/api/data"),
            timeout_sec=30,
            max_retries=3,
            rate_limit_per_sec=10.0,
        ),
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
    if request.node.get_closest_marker("network") or request.node.get_closest_marker(
        "integration"
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
