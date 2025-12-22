"""Unit tests for adapter provider names."""

from unittest.mock import MagicMock

from bioetl.infrastructure.adapters.pubchem.client import PubChemClient
from bioetl.infrastructure.adapters.uniprot.client import UniProtClient


class TestAdapterProviderNames:
    """Test that adapters have correct provider names."""

    def test_pubchem_provider_name(self):
        """Test PubChemClient provider name."""
        client = PubChemClient()
        assert client.provider_name == "pubchem"
        assert PubChemClient.provider_name == "pubchem"
        client.close()

    def test_uniprot_provider_name(self):
        """Test UniProtClient provider name."""
        mock_http_client = MagicMock()
        client = UniProtClient(http_client=mock_http_client)
        assert client.provider_name == "uniprot"
        assert UniProtClient.provider_name == "uniprot"
