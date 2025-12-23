"""Tests for PubChem Client."""

from unittest.mock import MagicMock, patch

import pytest

from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreakerOpenError
from bioetl.infrastructure.adapters.pubchem.client import PubChemClient


@pytest.fixture
def mock_logger():
    """Create a mock logger for testing."""
    return MagicMock()


@pytest.fixture
def pubchem_client(mock_logger):
    client = PubChemClient(logger=mock_logger, rate=100)  # High rate to avoid delays
    yield client
    # Cleanup logic if necessary (though close() calls shutdown on threadpool)
    client.thread_pool.shutdown(wait=False)


@pytest.fixture
def mock_pcp_compound():
    compound = MagicMock()
    compound.cid = 123
    compound.molecular_formula = "C9H8O4"
    compound.molecular_weight = 180.16
    compound.canonical_smiles = "CC(=O)OC1=CC=CC=C1C(=O)O"
    compound.isomeric_smiles = "CC(=O)OC1=CC=CC=C1C(=O)O"
    compound.inchi = (
        "InChI=1S/C9H8O4/c1-6(10)13-8-5-3-2-4-7(8)9(11)12/h2-5H,1H3,(H,11,12)"
    )
    compound.inchikey = "BSYNRYMUTXBXSQ-UHFFFAOYSA-N"
    compound.iupac_name = "2-acetyloxybenzoic acid"
    compound.charge = 0
    compound.complexity = 212
    compound.h_bond_acceptor_count = 4
    compound.h_bond_donor_count = 1
    compound.rotatable_bond_count = 3
    compound.fingerprint = "mock_fingerprint"
    return compound


@pytest.fixture
def mock_pcp_substance():
    substance = MagicMock()
    substance.sid = 456
    substance.source_name = "MockSource"
    substance.source_id = "Source123"
    substance.standardized_cids = [123]
    substance.synonyms = ["Aspirin"]
    return substance


@pytest.fixture
def mock_pcp_assay():
    return {
        "aid": 789,
        "name": "Mock Assay",
        "description": "Test Assay",
        "protocol": "Protocol desc",
        "target": "Target desc",
    }


async def test_fetch_compound_by_query(pubchem_client, mock_pcp_compound):
    """Test fetching compounds by query."""
    with patch("pubchempy.get_compounds", return_value=[mock_pcp_compound]) as mock_get:
        results = []
        async for record in pubchem_client.fetch("compound", query="aspirin"):
            results.append(record)

        assert len(results) == 1
        assert results[0]["cid"] == 123
        assert results[0]["iupac_name"] == "2-acetyloxybenzoic acid"
        mock_get.assert_called_with("aspirin", "name")


async def test_fetch_compound_with_limit(pubchem_client, mock_pcp_compound):
    """Test fetching compounds with limit."""
    with patch("pubchempy.get_compounds", return_value=[mock_pcp_compound]) as mock_get:
        results = []
        async for record in pubchem_client.fetch("compound", query="aspirin", limit=1):
            results.append(record)

        assert len(results) == 1
        assert results[0]["cid"] == 123
        mock_get.assert_called_with("aspirin", "name")


async def test_fetch_substance(pubchem_client, mock_pcp_substance):
    """Test fetching substances."""
    with patch(
        "pubchempy.get_substances", return_value=[mock_pcp_substance]
    ) as mock_get:
        results = []
        async for record in pubchem_client.fetch("substance", query="aspirin"):
            results.append(record)

        assert len(results) == 1
        assert results[0]["sid"] == 456
        assert results[0]["source_name"] == "MockSource"
        mock_get.assert_called_with("aspirin", "name")


async def test_fetch_assay(pubchem_client, mock_pcp_assay):
    """Test fetching assays."""
    with patch("pubchempy.get_assays", return_value=[mock_pcp_assay]) as mock_get:
        results = []
        async for record in pubchem_client.fetch("assay", query="12345"):
            results.append(record)

        assert len(results) == 1
        assert results[0]["aid"] == 789
        mock_get.assert_called_with("12345")


async def test_fetch_unsupported_entity(pubchem_client):
    """Test fetching unsupported entity raises ValueError."""
    with pytest.raises(ValueError, match="Unsupported entity type"):
        async for _ in pubchem_client.fetch("invalid_entity"):
            pass


async def test_fetch_compound_missing_query(pubchem_client):
    """Test fetching compound without query raises ValueError."""
    with pytest.raises(ValueError, match="Query is required for compound fetch"):
        async for _ in pubchem_client.fetch("compound"):
            pass


async def test_fetch_substance_missing_query(pubchem_client):
    """Test fetching substance without query raises ValueError."""
    with pytest.raises(ValueError, match="Query is required"):
        async for _ in pubchem_client.fetch("substance"):
            pass


async def test_fetch_assay_missing_query(pubchem_client):
    """Test fetching assay without query raises ValueError."""
    with pytest.raises(ValueError, match="Query is required"):
        async for _ in pubchem_client.fetch("assay"):
            pass


async def test_health_check_healthy(pubchem_client, mock_pcp_compound):
    """Test health check returns HEALTHY."""
    with patch("pubchempy.get_compounds", return_value=[mock_pcp_compound]):
        status = await pubchem_client.health_check()
        assert status == HealthStatus.HEALTHY


async def test_health_check_unhealthy(pubchem_client):
    """Test health check returns UNHEALTHY on exception."""
    with patch("pubchempy.get_compounds", side_effect=Exception("Connection error")):
        status = await pubchem_client.health_check()
        assert status == HealthStatus.UNHEALTHY


async def test_circuit_breaker(pubchem_client):
    """Test circuit breaker opens after failures."""
    # Set low threshold
    pubchem_client.circuit_breaker.failure_threshold = 1

    with patch("pubchempy.get_compounds", side_effect=Exception("API Error")):
        # First call fails and increments failure count
        try:
            async for _ in pubchem_client.fetch("compound", query="fail"):
                pass
        except Exception:
            pass

        # Second call should raise CircuitBreakerOpenError
        with pytest.raises(CircuitBreakerOpenError):
            async for _ in pubchem_client.fetch("compound", query="fail"):
                pass
