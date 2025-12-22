"""Tests for DataSourceFactory."""

from unittest.mock import Mock, patch

import pytest

from bioetl.composition.factories.data_sources import DataSourceFactory
from bioetl.infrastructure.adapters.chembl.client import ChemblAdapter
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.pubchem.client import PubChemClient
from bioetl.infrastructure.adapters.uniprot.client import UniProtClient


@pytest.fixture
def mock_http_client():
    return Mock(spec=UnifiedHTTPClient)


def test_create_chembl_adapter(mock_http_client):
    """Test creating ChEMBL adapter."""
    adapter = DataSourceFactory.create("chembl", http_client=mock_http_client)
    assert isinstance(adapter, ChemblAdapter)
    assert adapter.http_client == mock_http_client


def test_create_pubchem_adapter(mock_http_client):
    """Test creating PubChem adapter."""
    # PubChem doesn't use http_client, so it should be ignored by the factory logic
    # but we pass it anyway because the factory signature requires it (or allows it).
    # We also mock PubChemClient to avoid creating threads/ratelimits during test
    with patch(
        "bioetl.infrastructure.adapters.pubchem.client.PubChemClient"
    ) as MockPubChem:
        adapter_mock = Mock(spec=PubChemClient)
        MockPubChem.return_value = adapter_mock

        adapter = DataSourceFactory.create(
            "pubchem", http_client=mock_http_client, rate=1.0
        )

        assert adapter == adapter_mock
        MockPubChem.assert_called_once_with(rate=1.0)


def test_create_uniprot_adapter(mock_http_client):
    """Test creating UniProt adapter."""
    # UniProt doesn't use http_client either.
    with patch(
        "bioetl.infrastructure.adapters.uniprot.client.UniProtClient"
    ) as MockUniProt:
        adapter_mock = Mock(spec=UniProtClient)
        MockUniProt.return_value = adapter_mock

        adapter = DataSourceFactory.create(
            "uniprot", http_client=mock_http_client, api_key="test_key"
        )

        assert adapter == adapter_mock
        MockUniProt.assert_called_once_with(api_key="test_key")


def test_create_unknown_provider(mock_http_client):
    """Test creating unknown provider raises ValueError."""
    with pytest.raises(ValueError, match="Unknown provider: unknown"):
        DataSourceFactory.create("unknown", http_client=mock_http_client)
