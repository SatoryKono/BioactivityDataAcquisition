"""Tests for DataSourceFactory."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from bioetl.composition.factories.data_sources import DataSourceFactory
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient


@pytest.fixture
def mock_http_client():
    return Mock(spec=UnifiedHTTPClient)


@pytest.fixture
def mock_logger():
    return Mock()


def test_create_pubchem_adapter(mock_http_client, mock_logger):
    """Test creating PubChem adapter."""
    # PubChem doesn't use http_client
    adapter = DataSourceFactory.create(
        "pubchem", http_client=mock_http_client, logger=mock_logger, rate=1.0
    )

    # Use class name check to avoid reload issues
    assert adapter.__class__.__name__ == "PubChemAdapter"
    assert adapter.provider_name == "pubchem"


def test_create_uniprot_adapter(mock_http_client, mock_logger):
    """Test creating UniProt adapter."""
    adapter = DataSourceFactory.create(
        "uniprot", http_client=mock_http_client, logger=mock_logger, api_key="test_key"
    )

    # Use class name check to avoid reload issues
    assert adapter.__class__.__name__ == "UniProtAdapter"
    assert adapter.provider_name == "uniprot"
    assert adapter.api_key == "test_key"


def test_create_unknown_provider(mock_http_client):
    """Test creating unknown provider raises ValueError."""
    with pytest.raises(ValueError, match="Unknown provider: unknown"):
        DataSourceFactory.create("unknown", http_client=mock_http_client)
