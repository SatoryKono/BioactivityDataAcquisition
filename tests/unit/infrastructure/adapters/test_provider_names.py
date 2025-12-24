"""Unit tests for adapter provider names."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.infrastructure.adapters.pubchem.client import PubChemClient
from bioetl.infrastructure.adapters.uniprot.client import UniProtClient


class TestAdapterProviderNames:
    """Test that adapters have correct provider names."""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        return MagicMock()

    def test_pubchem_provider_name(self, mock_logger):
        """Test PubChemClient provider name."""
        client = PubChemClient(logger=mock_logger)
        assert client.provider_name == "pubchem"
        assert PubChemClient.provider_name == "pubchem"
        client.close()

    def test_uniprot_provider_name(self, mock_logger):
        """Test UniProtClient provider name."""
        mock_http_client = MagicMock()
        client = UniProtClient(http_client=mock_http_client, logger=mock_logger)
        assert client.provider_name == "uniprot"
        assert UniProtClient.provider_name == "uniprot"
