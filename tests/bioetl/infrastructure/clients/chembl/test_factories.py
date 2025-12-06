"""
Tests for ChEMBL factories.
"""

import pytest

from bioetl.infrastructure.clients.chembl.factories import (
    default_chembl_client,
    default_chembl_extraction_service,
)
from bioetl.infrastructure.clients.chembl.impl import ChemblExtractionServiceImpl
from bioetl.infrastructure.clients.chembl.impl.http_client import (
    ChemblDataClientHTTPImpl,
)
from bioetl.infrastructure.config.models import ChemblSourceConfig


@pytest.fixture
def source_config():
    """Create test ChemblSourceConfig with flat structure."""
    return ChemblSourceConfig(
        base_url="https://example.com",
        max_url_length=1000,
        timeout_sec=30,
        max_retries=3,
        rate_limit_per_sec=5.0,
    )


def test_default_chembl_client_success(source_config):
    """Test default ChEMBL client factory with valid config."""
    client = default_chembl_client(source_config)
    assert isinstance(client, ChemblDataClientHTTPImpl)
    # Check that parameters propagated to request_builder
    assert client.request_builder.base_url == "https://example.com"
    assert client.request_builder.max_url_length == 1000
    assert client.rate_limiter.rate == 5.0


def test_default_chembl_client_overrides(source_config):
    """Test overriding config parameters via kwargs."""
    client = default_chembl_client(
        source_config, base_url="https://override.com", max_url_length=500
    )
    assert client.request_builder.base_url == "https://override.com"
    assert client.request_builder.max_url_length == 500


def test_default_chembl_extraction_service(source_config):
    """Test default extraction service factory."""
    source_config.batch_size = 50
    service = default_chembl_extraction_service(source_config)
    assert isinstance(service, ChemblExtractionServiceImpl)
    assert isinstance(service.client, ChemblDataClientHTTPImpl)
    assert service.batch_size == 50


def test_default_chembl_extraction_service_default_batch(source_config):
    """Test default batch size calculation."""
    service = default_chembl_extraction_service(source_config)
    # ChEMBL factory uses hard_cap=1000 for batch_size
    assert service.batch_size == 1000
