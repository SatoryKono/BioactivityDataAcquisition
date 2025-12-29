"""Tests for PubChem Adapter."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, patch

import pytest

from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.http.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpenError,
)
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket
from bioetl.infrastructure.adapters.pubchem.client import PubChemAdapter


@pytest.fixture
def mock_logger():
    """Create a mock logger for testing."""
    return MagicMock()


@pytest.fixture
def rate_limiter():
    """Create a rate limiter for testing."""
    return TokenBucket(rate=100.0, capacity=200, provider="pubchem")


@pytest.fixture
def circuit_breaker():
    """Create a circuit breaker for testing."""
    return CircuitBreaker(provider="pubchem", failure_threshold=5, recovery_timeout=300)


@pytest.fixture
def thread_pool():
    """Create a thread pool for testing."""
    pool = ThreadPoolExecutor(max_workers=4)
    yield pool
    pool.shutdown(wait=False)


@pytest.fixture
def pubchem_adapter(mock_logger, rate_limiter, circuit_breaker, thread_pool):
    """Create PubChemAdapter with injected dependencies."""
    adapter = PubChemAdapter(
        logger=mock_logger,
        rate_limiter=rate_limiter,
        circuit_breaker=circuit_breaker,
        thread_pool=thread_pool,
    )
    yield adapter
    # Thread pool cleanup is handled by thread_pool fixture


@pytest.fixture
def mock_pcp_compound():
    compound = MagicMock()
    compound.cid = 123
    compound.molecular_formula = "C9H8O4"
    compound.molecular_weight = 180.16
    # connectivity_smiles replaces deprecated canonical_smiles (pubchempy 1.0.5)
    compound.connectivity_smiles = "CC(=O)OC1=CC=CC=C1C(=O)O"
    # smiles replaces deprecated isomeric_smiles (pubchempy 1.0.5)
    compound.smiles = "CC(=O)OC1=CC=CC=C1C(=O)O"
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


async def test_fetch_compound_by_query(pubchem_adapter, mock_pcp_compound):
    """Test fetching compounds by query."""
    with patch("pubchempy.get_compounds", return_value=[mock_pcp_compound]) as mock_get:
        results = []
        async for record in pubchem_adapter.fetch("compound", query="aspirin"):
            results.append(record)

        assert len(results) == 1
        assert results[0]["cid"] == 123
        assert results[0]["iupac_name"] == "2-acetyloxybenzoic acid"
        mock_get.assert_called_with("aspirin", "name")


async def test_fetch_compound_with_limit(pubchem_adapter, mock_pcp_compound):
    """Test fetching compounds with limit."""
    with patch("pubchempy.get_compounds", return_value=[mock_pcp_compound]) as mock_get:
        results = []
        async for record in pubchem_adapter.fetch("compound", query="aspirin", limit=1):
            results.append(record)

        assert len(results) == 1
        assert results[0]["cid"] == 123
        mock_get.assert_called_with("aspirin", "name")


async def test_fetch_substance(pubchem_adapter, mock_pcp_substance):
    """Test fetching substances."""
    with patch(
        "pubchempy.get_substances", return_value=[mock_pcp_substance]
    ) as mock_get:
        results = []
        async for record in pubchem_adapter.fetch("substance", query="aspirin"):
            results.append(record)

        assert len(results) == 1
        assert results[0]["sid"] == 456
        assert results[0]["source_name"] == "MockSource"
        mock_get.assert_called_with("aspirin", "name")


async def test_fetch_assay(pubchem_adapter, mock_pcp_assay):
    """Test fetching assays."""
    with patch("pubchempy.get_assays", return_value=[mock_pcp_assay]) as mock_get:
        results = []
        async for record in pubchem_adapter.fetch("assay", query="12345"):
            results.append(record)

        assert len(results) == 1
        assert results[0]["aid"] == 789
        mock_get.assert_called_with("12345")


async def test_fetch_unsupported_entity(pubchem_adapter):
    """Test fetching unsupported entity raises ValueError."""
    with pytest.raises(ValueError, match="Unsupported entity type"):
        async for _ in pubchem_adapter.fetch("invalid_entity"):
            pass


async def test_fetch_compound_missing_query(pubchem_adapter):
    """Test fetching compound without query raises ValueError."""
    with pytest.raises(ValueError, match="Query is required for compound fetch"):
        async for _ in pubchem_adapter.fetch("compound"):
            pass


async def test_fetch_substance_missing_query(pubchem_adapter):
    """Test fetching substance without query raises ValueError."""
    with pytest.raises(ValueError, match="Query is required"):
        async for _ in pubchem_adapter.fetch("substance"):
            pass


async def test_fetch_assay_missing_query(pubchem_adapter):
    """Test fetching assay without query raises ValueError."""
    with pytest.raises(ValueError, match="Query is required"):
        async for _ in pubchem_adapter.fetch("assay"):
            pass


async def test_health_check_healthy(pubchem_adapter, mock_pcp_compound):
    """Test health check returns HEALTHY."""
    with patch("pubchempy.get_compounds", return_value=[mock_pcp_compound]):
        status = await pubchem_adapter.health_check()
        assert status == HealthStatus.HEALTHY


async def test_health_check_degraded_on_probe_failure(pubchem_adapter):
    """Test health check returns DEGRADED on single probe failure.

    Uses Template Method pattern: exception in _probe_health() triggers
    _fallback_health_status() which uses circuit breaker assessment.
    With 1 failure (<=2 threshold), returns DEGRADED.
    """
    with patch("pubchempy.get_compounds", side_effect=Exception("Connection error")):
        status = await pubchem_adapter.health_check()
        assert status == HealthStatus.DEGRADED


async def test_health_check_unhealthy_after_multiple_failures(pubchem_adapter):
    """Test health check returns UNHEALTHY after multiple failures.

    Circuit breaker records failures, and after threshold (>2),
    assess_health_from_circuit_breaker returns UNHEALTHY.
    """
    # Trigger 3 failures to exceed the threshold (>2 for UNHEALTHY)
    for _ in range(3):
        with patch(
            "pubchempy.get_compounds", side_effect=Exception("Connection error")
        ):
            await pubchem_adapter.health_check()

    # Now health check should return UNHEALTHY
    with patch("pubchempy.get_compounds", side_effect=Exception("Connection error")):
        status = await pubchem_adapter.health_check()
        assert status == HealthStatus.UNHEALTHY


async def test_circuit_breaker(pubchem_adapter):
    """Test circuit breaker opens after failures."""
    # Set low threshold
    pubchem_adapter.circuit_breaker.failure_threshold = 1

    with patch("pubchempy.get_compounds", side_effect=RuntimeError("API Error")):
        # First call fails and increments failure count
        try:
            async for _ in pubchem_adapter.fetch("compound", query="fail"):
                pass
        except RuntimeError:
            pass

        # Second call should raise CircuitBreakerOpenError
        with pytest.raises(CircuitBreakerOpenError):
            async for _ in pubchem_adapter.fetch("compound", query="fail"):
                pass


async def test_rate_limiter_called_once_per_compound_fetch(
    pubchem_adapter, mock_pcp_compound
):
    """Test rate limiter acquire() is called exactly once per fetch (no double limiting).

    Verifies fix for double rate limiting issue where fetch() called acquire()
    and then internal methods called acquire() again, reducing throughput
    from 5 req/sec to ~2.5 req/sec.
    """
    with patch("pubchempy.get_compounds", return_value=[mock_pcp_compound]):
        # Replace rate limiter with a mock to count calls
        original_acquire = pubchem_adapter.rate_limiter.acquire
        call_count = 0

        async def counting_acquire():
            nonlocal call_count
            call_count += 1
            return await original_acquire()

        pubchem_adapter.rate_limiter.acquire = counting_acquire

        # Fetch compounds
        results = []
        async for record in pubchem_adapter.fetch("compound", query="aspirin"):
            results.append(record)

        # Should be exactly 1 acquire() call per logical request
        assert call_count == 1, f"Expected 1 acquire() call, got {call_count}"


async def test_rate_limiter_called_once_per_substance_fetch(
    pubchem_adapter, mock_pcp_substance
):
    """Test rate limiter is called exactly once for substance fetch."""
    with patch("pubchempy.get_substances", return_value=[mock_pcp_substance]):
        original_acquire = pubchem_adapter.rate_limiter.acquire
        call_count = 0

        async def counting_acquire():
            nonlocal call_count
            call_count += 1
            return await original_acquire()

        pubchem_adapter.rate_limiter.acquire = counting_acquire

        results = []
        async for record in pubchem_adapter.fetch("substance", query="aspirin"):
            results.append(record)

        assert call_count == 1, f"Expected 1 acquire() call, got {call_count}"


async def test_rate_limiter_called_once_per_assay_fetch(
    pubchem_adapter, mock_pcp_assay
):
    """Test rate limiter is called exactly once for assay fetch."""
    with patch("pubchempy.get_assays", return_value=[mock_pcp_assay]):
        original_acquire = pubchem_adapter.rate_limiter.acquire
        call_count = 0

        async def counting_acquire():
            nonlocal call_count
            call_count += 1
            return await original_acquire()

        pubchem_adapter.rate_limiter.acquire = counting_acquire

        results = []
        async for record in pubchem_adapter.fetch("assay", query="12345"):
            results.append(record)

        assert call_count == 1, f"Expected 1 acquire() call, got {call_count}"
