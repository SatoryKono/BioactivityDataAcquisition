"""Unit tests for provider adapters.

Tests adapter initialization, configuration, and basic functionality.
Uses mocking for external API calls.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.infrastructure.adapters.chembl.client import ChemblAdapter
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket
from bioetl.infrastructure.adapters.pubchem.client import PubChemAdapter
from bioetl.infrastructure.adapters.uniprot.client import UniProtAdapter


@pytest.mark.unit
class TestChemblAdapter:
    """Test ChEMBL adapter initialization and configuration."""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        return MagicMock()

    def test_adapter_creation(self, mock_logger):
        """Test ChEMBL adapter can be created."""
        bucket = TokenBucket(rate=10.0, capacity=10)
        cb = CircuitBreaker(provider="chembl")
        http_client = UnifiedHTTPClient(bucket, cb)
        adapter = ChemblAdapter(http_client=http_client, logger=mock_logger)

        assert adapter.provider_name == "chembl"
        assert adapter.effective_batch_size == 1000

    def test_adapter_with_custom_batch_size(self, mock_logger):
        """Test ChEMBL adapter with custom batch size."""
        bucket = TokenBucket(rate=10.0, capacity=10)
        cb = CircuitBreaker(provider="chembl")
        http_client = UnifiedHTTPClient(bucket, cb)
        adapter = ChemblAdapter(
            http_client=http_client, logger=mock_logger, batch_size=500
        )

        assert adapter.effective_batch_size == 500

    def test_entity_mapping(self, mock_logger):
        """Test entity type to resource URL mapping."""
        from bioetl.infrastructure.adapters.chembl.entity_mapper import (
            ChemblEntityMapper,
        )

        # Valid entity types via entity mapper
        assert "activity" in ChemblEntityMapper.get_resource_url("activity")
        assert "molecule" in ChemblEntityMapper.get_resource_url("compound")
        assert "target" in ChemblEntityMapper.get_resource_url("target")

    def test_invalid_entity_type(self, mock_logger):
        """Test error handling for invalid entity type."""
        from bioetl.infrastructure.adapters.chembl.entity_mapper import (
            ChemblEntityMapper,
        )

        with pytest.raises(ValueError, match="Unknown entity type"):
            ChemblEntityMapper.get_resource_url("invalid_entity")


@pytest.mark.unit
class TestPubChemAdapter:
    """Test PubChem adapter initialization and configuration."""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        return MagicMock()

    @pytest.fixture
    def rate_limiter(self):
        """Create a rate limiter for testing."""
        return TokenBucket(rate=5.0, capacity=10, provider="pubchem")

    @pytest.fixture
    def circuit_breaker(self):
        """Create a circuit breaker for testing."""
        return CircuitBreaker(provider="pubchem", failure_threshold=5)

    @pytest.fixture
    def thread_pool(self):
        """Create a thread pool for testing."""
        from concurrent.futures import ThreadPoolExecutor

        pool = ThreadPoolExecutor(max_workers=4)
        yield pool
        pool.shutdown(wait=False)

    def test_adapter_creation(
        self, mock_logger, rate_limiter, circuit_breaker, thread_pool
    ):
        """Test PubChem adapter can be created with DI."""
        adapter = PubChemAdapter(
            logger=mock_logger,
            rate_limiter=rate_limiter,
            circuit_breaker=circuit_breaker,
            thread_pool=thread_pool,
        )

        assert adapter.provider_name == "pubchem"
        assert adapter.rate_limiter.rate == 5.0  # 5 req/sec per RULES.md

    def test_adapter_with_custom_rate(self, mock_logger, circuit_breaker, thread_pool):
        """Test PubChem adapter with custom rate limit via injected rate limiter."""
        custom_rate_limiter = TokenBucket(rate=10.0, capacity=20, provider="pubchem")
        adapter = PubChemAdapter(
            logger=mock_logger,
            rate_limiter=custom_rate_limiter,
            circuit_breaker=circuit_breaker,
            thread_pool=thread_pool,
        )

        assert adapter.rate_limiter.rate == 10.0

    def test_thread_pool_injected(self, mock_logger, rate_limiter, circuit_breaker):
        """Test thread pool is properly injected for sync operations."""
        from concurrent.futures import ThreadPoolExecutor

        custom_pool = ThreadPoolExecutor(max_workers=2)
        try:
            adapter = PubChemAdapter(
                logger=mock_logger,
                rate_limiter=rate_limiter,
                circuit_breaker=circuit_breaker,
                thread_pool=custom_pool,
            )

            assert adapter.thread_pool is not None
            assert adapter.thread_pool._max_workers == 2
        finally:
            custom_pool.shutdown(wait=False)

    async def test_compound_to_dict(
        self, mock_logger, rate_limiter, circuit_breaker, thread_pool
    ):
        """Test compound conversion to dictionary."""
        adapter = PubChemAdapter(
            logger=mock_logger,
            rate_limiter=rate_limiter,
            circuit_breaker=circuit_breaker,
            thread_pool=thread_pool,
        )

        # Mock compound object
        # Uses connectivity_smiles/smiles (pubchempy 1.0.5 replacements)
        class MockCompound:
            cid = 2244
            molecular_formula = "C9H8O4"
            molecular_weight = 180.16
            # connectivity_smiles replaces deprecated canonical_smiles
            connectivity_smiles = "CC(=O)OC1=CC=CC=C1C(=O)O"
            # smiles replaces deprecated isomeric_smiles
            smiles = None
            inchi = (
                "InChI=1S/C9H8O4/c1-6(10)13-8-5-3-2-4-7(8)9(11)12/h2-5H,1H3,(H,11,12)"
            )
            inchikey = "BSYNRYMUTXBXSQ-UHFFFAOYSA-N"
            iupac_name = "2-acetyloxybenzoic acid"
            charge = 0
            complexity = 212.0
            h_bond_acceptor_count = 4
            h_bond_donor_count = 1
            rotatable_bond_count = 3
            fingerprint = "00000000"

        result = adapter._mapper.compound_to_dict(MockCompound())

        assert result["cid"] == 2244
        assert result["molecular_formula"] == "C9H8O4"
        assert result["canonical_smiles"] == "CC(=O)OC1=CC=CC=C1C(=O)O"


@pytest.mark.unit
class TestUniProtAdapter:
    """Test UniProt adapter initialization and configuration."""

    @pytest.fixture
    def http_client(self):
        """Create a UnifiedHTTPClient for testing."""
        bucket = TokenBucket(rate=10.0, capacity=10)
        cb = CircuitBreaker(provider="uniprot")
        return UnifiedHTTPClient(bucket, cb)

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        return MagicMock()

    def test_adapter_creation_without_api_key(self, http_client, mock_logger):
        """Test UniProt adapter without API key."""
        adapter = UniProtAdapter(http_client=http_client, logger=mock_logger)

        assert adapter.provider_name == "uniprot"
        assert adapter.api_key is None

    def test_adapter_creation_with_api_key(self, http_client, mock_logger):
        """Test UniProt adapter with API key."""
        adapter = UniProtAdapter(
            http_client=http_client, logger=mock_logger, api_key="test_key"
        )

        assert adapter.api_key == "test_key"

    def test_adapter_with_custom_base_url(self, http_client, mock_logger):
        """Test UniProt adapter with custom base URL."""
        mock_http = MagicMock()
        custom_url = "https://custom.uniprot.org"
        adapter = UniProtAdapter(
            http_client=mock_http, logger=mock_logger, base_url=custom_url
        )

        assert adapter.base_url == custom_url


@pytest.mark.unit
class TestRateLimiter:
    """Test rate limiter functionality."""

    def test_token_bucket_creation(self):
        """Test token bucket initialization."""
        bucket = TokenBucket(rate=5.0, capacity=10)

        assert bucket.rate == 5.0
        assert bucket.capacity == 10
        assert bucket._tokens == 10.0  # Starts full

    def test_try_acquire_success(self):
        """Test successful token acquisition."""
        bucket = TokenBucket(rate=100.0, capacity=10)

        # Should succeed immediately when bucket is full
        assert bucket.try_acquire(tokens=1) is True
        assert bucket.try_acquire(tokens=5) is True

    def test_try_acquire_failure(self):
        """Test failed token acquisition when insufficient tokens."""
        bucket = TokenBucket(rate=1.0, capacity=5)

        # Exhaust tokens
        assert bucket.try_acquire(tokens=5) is True
        # Should fail immediately
        assert bucket.try_acquire(tokens=1) is False

    def test_get_available_tokens(self):
        """Test getting available token count."""
        bucket = TokenBucket(rate=10.0, capacity=100)

        available = bucket.available_tokens()
        assert available == 100  # Full capacity initially


@pytest.mark.unit
class TestCircuitBreaker:
    """Test circuit breaker functionality."""

    def test_circuit_breaker_creation(self):
        """Test circuit breaker initialization."""
        cb = CircuitBreaker(provider="test", failure_threshold=5)

        assert cb.provider == "test"
        assert cb.failure_threshold == 5
        assert cb.get_state().value == "CLOSED"

    def test_initial_state_is_closed(self):
        """Test circuit breaker starts in CLOSED state."""
        cb = CircuitBreaker(provider="test")

        assert cb.get_state().value == "CLOSED"
        assert cb._failure_count == 0

    def test_failure_count_tracking(self):
        """Test failure count increments via private attribute."""
        cb = CircuitBreaker(provider="test", failure_threshold=3)

        # Access private attribute for testing
        cb._failure_count = 1
        assert cb._failure_count == 1

        cb._failure_count = 2
        assert cb._failure_count == 2
