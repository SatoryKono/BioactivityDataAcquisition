"""Unit tests for adapter provider names."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.infrastructure.adapters.pubchem.client import PubChemAdapter
from bioetl.infrastructure.adapters.uniprot.client import UniProtAdapter


class TestAdapterProviderNames:
    """Test that adapters have correct provider names."""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        return MagicMock()

    def test_pubchem_provider_name(self, mock_logger):
        """Test PubChemAdapter provider name."""
        adapter = PubChemAdapter(logger=mock_logger)
        assert adapter.provider_name == "pubchem"
        assert PubChemAdapter.provider_name == "pubchem"
        adapter.close()

    def test_uniprot_provider_name(self, mock_logger):
        """Test UniProtAdapter provider name."""
        mock_http_client = MagicMock()
        adapter = UniProtAdapter(http_client=mock_http_client, logger=mock_logger)
        assert adapter.provider_name == "uniprot"
        assert UniProtAdapter.provider_name == "uniprot"
