"""Tests for DataSourceFactory."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from bioetl.composition.factories.data_sources import DataSourceFactory
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.pubchem.client import PubChemAdapter
from bioetl.infrastructure.adapters.uniprot.client import UniProtAdapter


@pytest.fixture
def mock_http_client():
    return Mock(spec=UnifiedHTTPClient)


@pytest.fixture
def mock_logger():
    return Mock()


def test_create_pubchem_adapter(mock_http_client, mock_logger):
    """Test creating PubChem adapter."""
    # PubChem doesn't use http_client, so it should be ignored by the factory logic
    # but we pass it anyway because the factory signature requires it (or allows it).
    # We also mock PubChemAdapter to avoid creating threads/ratelimits during test
    with patch(
        "bioetl.infrastructure.adapters.pubchem.client.PubChemAdapter"
    ) as MockPubChem:
        adapter_mock = Mock(spec=PubChemAdapter)
        MockPubChem.return_value = adapter_mock

        adapter = DataSourceFactory.create(
            "pubchem", http_client=mock_http_client, logger=mock_logger, rate=1.0
        )

        assert adapter == adapter_mock
        MockPubChem.assert_called_once_with(logger=mock_logger, rate=1.0)


def test_create_uniprot_adapter(mock_http_client, mock_logger):
    """Test creating UniProt adapter."""
    # UniProt uses http_client.
    with patch(
        "bioetl.infrastructure.adapters.uniprot.client.UniProtAdapter"
    ) as MockUniProt:
        adapter_mock = Mock(spec=UniProtAdapter)
        MockUniProt.return_value = adapter_mock

        adapter = DataSourceFactory.create(
            "uniprot", http_client=mock_http_client, logger=mock_logger, api_key="test_key"
        )

        assert adapter == adapter_mock
        MockUniProt.assert_called_once_with(
            http_client=mock_http_client, logger=mock_logger, api_key="test_key"
        )


def test_create_unknown_provider(mock_http_client):
    """Test creating unknown provider raises ValueError."""
    with pytest.raises(ValueError, match="Unknown provider: unknown"):
        DataSourceFactory.create("unknown", http_client=mock_http_client)
