"""
Tests for ChEMBL factories.
"""
from bioetl.infrastructure.clients.chembl.factories import (
    default_chembl_client,
    default_chembl_extraction_service
)
from bioetl.infrastructure.clients.chembl.impl.http_client import ChemblDataClientHTTPImpl
from bioetl.application.pipelines.chembl.extraction import ChemblExtractionService


def test_default_chembl_client():
    """Test default ChEMBL client factory."""
    client = default_chembl_client()
    assert isinstance(client, ChemblDataClientHTTPImpl)
    assert client.rate_limiter.rate == 5.0


def test_default_chembl_extraction_service():
    """Test default extraction service factory."""
    service = default_chembl_extraction_service()
    assert isinstance(service, ChemblExtractionService)
    assert isinstance(service.client, ChemblDataClientHTTPImpl)
