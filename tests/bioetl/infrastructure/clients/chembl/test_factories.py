"""Tests for ChEMBL factories."""

from unittest.mock import Mock

import pytest

from bioetl.domain.configs import (
    ChemblSourceConfig,
    HttpClientConfig,
)
from bioetl.domain.observability import LoggingPortABC, MetricsPortABC
from bioetl.domain.ports.parsing import ResponseParserPortABC
from bioetl.infrastructure.clients.chembl.factories import (
    default_chembl_client,
    default_chembl_extraction_service,
)
from bioetl.infrastructure.clients.chembl.impl import (
    ChemblExtractionServiceImpl,
)
from bioetl.infrastructure.clients.chembl.impl.chembl_http_client_impl import (
    ChemblHttpClientImpl,
)
from bioetl.infrastructure.clients.chembl.response_parser import (
    ChemblGenericResponseParser,
)


@pytest.fixture
def mock_logger() -> LoggingPortABC:
    """Create mock logger for tests."""
    return Mock(spec=LoggingPortABC)


@pytest.fixture
def mock_metrics() -> MetricsPortABC:
    """Create mock metrics for tests."""
    return Mock(spec=MetricsPortABC)


@pytest.fixture
def source_config():
    """Create test ChemblSourceConfig with flat structure."""
    return ChemblSourceConfig(
        base_url="https://example.com",
        max_url_length=1000,
        http=HttpClientConfig(
            timeout_sec=30,
            max_retries=3,
            rate_limit_per_sec=5.0,
        ),
    )


def test_default_chembl_client_success(source_config, mock_logger, mock_metrics):
    """Test default ChEMBL client factory with valid config."""
    client = default_chembl_client(source_config, mock_logger, mock_metrics)
    assert isinstance(client, ChemblHttpClientImpl)
    # Check that parameters propagated to request_builder
    assert client.request_builder.base_url == "https://example.com"
    assert client.request_builder.max_url_length == 1000
    # Rate should match source_config.http.rate_limit_per_sec
    assert client.rate_limiter.rate == 5.0


def test_default_chembl_client_overrides(source_config, mock_logger, mock_metrics):
    """Test overriding config parameters via kwargs."""
    client = default_chembl_client(
        source_config,
        mock_logger,
        mock_metrics,
        base_url="https://override.com",
        max_url_length=500,
    )
    assert client.request_builder.base_url == "https://override.com"
    assert client.request_builder.max_url_length == 500


def test_default_chembl_extraction_service(source_config, mock_logger, mock_metrics):
    """Test default extraction service factory."""
    source_config.batch_size = 50
    service = default_chembl_extraction_service(
        source_config, mock_logger, mock_metrics
    )
    assert isinstance(service, ChemblExtractionServiceImpl)
    assert isinstance(service.client, ChemblHttpClientImpl)
    assert service.batch_size == 50


def test_default_chembl_extraction_service_default_batch(
    source_config, mock_logger, mock_metrics
):
    """Test default batch size calculation."""
    service = default_chembl_extraction_service(
        source_config, mock_logger, mock_metrics
    )
    # ChEMBL factory uses hard_cap=1000 for batch_size
    assert service.batch_size == 1000


def test_default_chembl_extraction_service_uses_generic_parser(
    source_config, mock_logger, mock_metrics
):
    """Test that factory creates service with generic parser by default."""
    service = default_chembl_extraction_service(
        source_config, mock_logger, mock_metrics
    )
    assert isinstance(service._parser, ChemblGenericResponseParser)


def test_default_chembl_extraction_service_accepts_custom_parser(
    source_config, mock_logger, mock_metrics
):
    """Test that parser can be injected via factory."""
    custom_parser = Mock(spec=ResponseParserPortABC)

    service = default_chembl_extraction_service(
        source_config, mock_logger, mock_metrics, parser=custom_parser
    )

    assert service._parser is custom_parser
