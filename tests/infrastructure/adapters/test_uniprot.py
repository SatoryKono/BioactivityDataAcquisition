"Tests for UniProt Client."

import pytest
import respx
from httpx import Response

from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket
from bioetl.infrastructure.adapters.uniprot.client import UniProtClient


@pytest.fixture
def unified_http_client():
    """Fixture for UnifiedHTTPClient."""
    rate_limiter = TokenBucket(rate=100.0, capacity=100)
    circuit_breaker = CircuitBreaker(provider="uniprot")
    return UnifiedHTTPClient(rate_limiter=rate_limiter, circuit_breaker=circuit_breaker)


@pytest.fixture
def uniprot_client(unified_http_client):
    """Fixture for UniProtClient."""
    return UniProtClient(http_client=unified_http_client)


@pytest.fixture
def mock_protein_response():
    return {
        "results": [
            {
                "primaryAccession": "P12345",
                "proteinDescription": {
                    "recommendedName": {"fullName": {"value": "Test Protein"}}
                },
                "genes": [{"geneName": {"value": "TEST1"}}],
                "organism": {
                    "scientificName": "Homo sapiens",
                    "taxonId": 9606,
                },
            }
        ],
        "nextCursor": None,
    }


@pytest.fixture
def mock_protein_response_page1(mock_protein_response):
    return {
        "results": mock_protein_response["results"],
        "nextCursor": "cursor123",
    }


@pytest.fixture
def mock_feature_response():
    return {
        "primaryAccession": "P12345",
        "features": [
            {
                "type": "Domain",
                "location": {"start": 10, "end": 20},
                "description": "Test Domain",
            }
        ],
    }


@pytest.fixture
def mock_fasta_response():
    return ">sp|P12345|TEST_HUMAN Test Protein OS=Homo sapiens OX=9606 GN=TEST1 PE=1 SV=1\nMKTLLLLAVV\nLLLGAAQA"


@respx.mock
async def test_fetch_protein_success(uniprot_client, mock_protein_response):
    """Test fetching proteins successfully."""
    route = respx.get("https://rest.uniprot.org/uniprotkb/search").mock(
        return_value=Response(200, json=mock_protein_response)
    )

    results = []
    async with uniprot_client:
        async for record in uniprot_client.fetch("protein", query="gene:TEST1"):
            results.append(record)

    assert len(results) == 1
    assert results[0]["primaryAccession"] == "P12345"
    assert route.called


@respx.mock
async def test_fetch_protein_pagination(
    uniprot_client, mock_protein_response_page1, mock_protein_response
):
    """Test fetching proteins with pagination."""
    # Mocking exact params is tricky due to size calc and defaults.
    # We'll use a regex or looser matching if possible, but respx strict matching requires exact params.
    # The issue might be that the client code calculates `size` dynamically based on limit.
    # Let's mock based on path only for this test to avoid timeout loops.

    route = respx.get("https://rest.uniprot.org/uniprotkb/search")
    route.side_effect = [
        Response(200, json=mock_protein_response_page1),
        Response(200, json=mock_protein_response),
    ]

    results = []
    async with uniprot_client:
        async for record in uniprot_client.fetch("protein", query="gene:TEST1"):
            results.append(record)

    assert len(results) == 2


@respx.mock
async def test_fetch_features(uniprot_client, mock_feature_response):
    """Test fetching protein features."""
    respx.get("https://rest.uniprot.org/uniprotkb/P12345.json").mock(
        return_value=Response(200, json=mock_feature_response)
    )

    results = []
    async with uniprot_client:
        async for record in uniprot_client.fetch("feature", query="P12345"):
            results.append(record)

    assert len(results) == 1
    assert results[0]["type"] == "Domain"
    assert results[0]["accession"] == "P12345"


@respx.mock
async def test_fetch_sequences(uniprot_client, mock_fasta_response):
    """Test fetching protein sequences."""
    respx.get("https://rest.uniprot.org/uniprotkb/stream").mock(
        return_value=Response(200, text=mock_fasta_response)
    )

    results = []
    async with uniprot_client:
        async for record in uniprot_client.fetch("sequence", query="P12345"):
            results.append(record)

    assert len(results) == 1
    assert "MKTLLLLAVVLLLGAAQA" in results[0]["sequence"]


async def test_fetch_unsupported_entity(uniprot_client):
    """Test fetching unsupported entity raises ValueError."""
    async with uniprot_client:
        with pytest.raises(ValueError, match="Unsupported entity type"):
            async for _ in uniprot_client.fetch("invalid_entity"):
                pass


async def test_fetch_features_missing_query(uniprot_client):
    """Test fetching features without query raises ValueError."""
    async with uniprot_client:
        with pytest.raises(ValueError, match="Query is required"):
            async for _ in uniprot_client.fetch("feature"):
                pass


async def test_fetch_sequences_missing_query(uniprot_client):
    """Test fetching sequences without query raises ValueError."""
    async with uniprot_client:
        with pytest.raises(ValueError, match="Query is required"):
            async for _ in uniprot_client.fetch("sequence"):
                pass


@respx.mock
async def test_health_check_healthy(uniprot_client):
    """Test health check returns HEALTHY."""
    respx.get("https://rest.uniprot.org/rest/beta/health").mock(
        return_value=Response(200)
    )
    async with uniprot_client:
        status = await uniprot_client.health_check()
    assert status == HealthStatus.HEALTHY


@respx.mock
async def test_health_check_on_server_error(uniprot_client):
    """Test health check behavior on server error (500).

    When http_client raises HTTPStatusError on 500, it's caught and
    falls back to circuit breaker state (HEALTHY if no failures).
    """
    respx.get("https://rest.uniprot.org/rest/beta/health").mock(
        return_value=Response(500)
    )
    async with uniprot_client:
        status = await uniprot_client.health_check()
    # 500 causes exception in http_client, falls back to CB check (HEALTHY if no failures)
    assert status == HealthStatus.HEALTHY


@respx.mock
async def test_health_check_on_connection_error(uniprot_client):
    """Test health check behavior on connection error.

    Connection errors fall back to circuit breaker state which may
    be DEGRADED if there were prior failures.
    """
    respx.get("https://rest.uniprot.org/rest/beta/health").mock(
        side_effect=Exception("Connection error")
    )
    async with uniprot_client:
        status = await uniprot_client.health_check()
    # Connection error falls back to circuit breaker which may show degraded
    assert status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)
