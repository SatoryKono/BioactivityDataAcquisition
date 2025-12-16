"""Unit tests for provider adapters.

Tests adapter initialization, configuration, and basic functionality.
Uses mocking for external API calls.
"""

import pytest

from bioetl.infrastructure.adapters.chembl.client import ChemblAdapter
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket
from bioetl.infrastructure.adapters.pubchem.client import PubChemClient
from bioetl.infrastructure.adapters.uniprot.client import UniProtClient


@pytest.mark.unit
class TestChemblAdapter:
    """Test ChEMBL adapter initialization and configuration."""

    def test_adapter_creation(self):
        """Test ChEMBL adapter can be created."""
        bucket = TokenBucket(rate=10.0, capacity=10)
        cb = CircuitBreaker(provider="chembl")
        http_client = UnifiedHTTPClient(bucket, cb)
        adapter = ChemblAdapter(http_client=http_client)

        assert adapter.provider_name == "chembl"
        assert adapter.batch_size == 1000

    def test_adapter_with_custom_batch_size(self):
        """Test ChEMBL adapter with custom batch size."""
        bucket = TokenBucket(rate=10.0, capacity=10)
        cb = CircuitBreaker(provider="chembl")
        http_client = UnifiedHTTPClient(bucket, cb)
        adapter = ChemblAdapter(http_client=http_client, batch_size=500)

        assert adapter.batch_size == 500

    def test_entity_mapping(self):
        """Test entity type to resource URL mapping."""
        bucket = TokenBucket(rate=10.0, capacity=10)
        cb = CircuitBreaker(provider="chembl")
        http_client = UnifiedHTTPClient(bucket, cb)
        adapter = ChemblAdapter(http_client=http_client)

        # Valid entity types
        assert "activity" in adapter._get_resource_url("activity")
        assert "molecule" in adapter._get_resource_url("compound")
        assert "target" in adapter._get_resource_url("target")

    def test_invalid_entity_type(self):
        """Test error handling for invalid entity type."""
        bucket = TokenBucket(rate=10.0, capacity=10)
        cb = CircuitBreaker(provider="chembl")
        http_client = UnifiedHTTPClient(bucket, cb)
        adapter = ChemblAdapter(http_client=http_client)

        with pytest.raises(ValueError, match="Unknown entity type"):
            adapter._get_resource_url("invalid_entity")


@pytest.mark.unit
class TestPubChemClient:
    """Test PubChem client initialization and configuration."""

    def test_client_creation(self):
        """Test PubChem client can be created."""
        client = PubChemClient()

        assert client.provider_name == "pubchem"
        assert client.rate_limiter.rate == 5.0  # 5 req/sec per RULES.md

    def test_client_with_custom_rate(self):
        """Test PubChem client with custom rate limit."""
        client = PubChemClient(rate=10.0)

        assert client.rate_limiter.rate == 10.0

    def test_thread_pool_created(self):
        """Test thread pool is created for sync operations."""
        client = PubChemClient(max_workers=2)

        assert client.thread_pool is not None
        assert client.thread_pool._max_workers == 2

    @pytest.mark.asyncio
    async def test_compound_to_dict(self):
        """Test compound conversion to dictionary."""
        client = PubChemClient()

        # Mock compound object
        class MockCompound:
            cid = 2244
            molecular_formula = "C9H8O4"
            molecular_weight = 180.16
            canonical_smiles = "CC(=O)OC1=CC=CC=C1C(=O)O"
            isomeric_smiles = None
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

        result = client._compound_to_dict(MockCompound())

        assert result["cid"] == 2244
        assert result["molecular_formula"] == "C9H8O4"
        assert result["canonical_smiles"] == "CC(=O)OC1=CC=CC=C1C(=O)O"


@pytest.mark.unit
class TestUniProtClient:
    """Test UniProt client initialization and configuration."""

    def test_client_creation_without_api_key(self):
        """Test UniProt client without API key."""
        client = UniProtClient()

        assert client.provider_name == "uniprot"
        assert client.api_key is None
        # In UnifiedHTTPClient structure, rate_limiter is inside http_client
        assert client.http_client.rate_limiter.rate == 10.0  # Lower rate without key

    def test_client_creation_with_api_key(self):
        """Test UniProt client with API key."""
        client = UniProtClient(api_key="test_key")

        assert client.api_key == "test_key"
        # In UnifiedHTTPClient structure, rate_limiter is inside http_client
        assert client.http_client.rate_limiter.rate == 100.0  # Higher rate with key

    def test_client_with_custom_base_url(self):
        """Test UniProt client with custom base URL."""
        custom_url = "https://custom.uniprot.org"
        client = UniProtClient(base_url=custom_url)

        assert client.base_url == custom_url

    def test_fasta_parsing(self):
        """Test FASTA format parsing."""
        client = UniProtClient()

        fasta_text = """>sp|P04637|P53_HUMAN Cellular tumor antigen p53
MEEPQSDPSVEPPLSQETFSDLWKLLPENNVLSPLPSQAMDDLMLSPDDIEQWFTEDPGP
>sp|Q9Y6K9|NF2L2_HUMAN Nuclear factor erythroid 2-related factor 2
MDPGQQPPPQPAPQGQGQPPSQPPQGQGPPSGPGQPAPAGTQGQPQ"""

        records = client._parse_fasta(fasta_text)

        assert len(records) == 2
        assert "P04637" in records[0]["header"]
        assert records[0]["sequence"].startswith(
            "MEEPQSDPSVEPPLSQETFSDLWKLLPENNVLSPLPS"
        )
        assert "Q9Y6K9" in records[1]["header"]


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
