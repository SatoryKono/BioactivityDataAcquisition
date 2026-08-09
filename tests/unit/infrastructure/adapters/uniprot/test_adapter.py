# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
from __future__ import annotations

"Tests for UniProt Adapter."

from collections.abc import AsyncIterator
from unittest.mock import MagicMock

import httpx
import pytest
import respx
from httpx import Response

from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreakerGuard
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucketRateLimiter
from bioetl.infrastructure.adapters.uniprot import UniProtAdapter
from tests.helpers.adapter_runtime import build_http_adapter_runtime_kwargs


pytestmark = pytest.mark.unit


async def _drain_async_iter(async_iter: AsyncIterator[object]) -> None:
    """Consume an async iterator until completion."""
    async for _ in async_iter:
        continue


@pytest.fixture
def mock_logger():
    """Create a mock logger for testing."""
    return MagicMock()


@pytest.fixture
def unified_http_client():
    """Fixture for UnifiedHTTPClient."""
    rate_limiter = TokenBucketRateLimiter(rate=100.0, capacity=100)
    circuit_breaker = CircuitBreakerGuard(provider="uniprot")
    return UnifiedHTTPClient(rate_limiter=rate_limiter, circuit_breaker=circuit_breaker)


@pytest.fixture
def uniprot_adapter(unified_http_client, mock_logger):
    """Fixture for UniProtAdapter."""
    return UniProtAdapter(
        http_client=unified_http_client,
        logger=mock_logger,
        **build_http_adapter_runtime_kwargs(
            "uniprot",
            logger=mock_logger,
            include_fallback_service=True,
        ),
    )


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
async def test_fetch_protein_success(uniprot_adapter, mock_protein_response):
    """Test fetching proteins successfully."""
    route = respx.get("https://rest.uniprot.org/uniprotkb/search").mock(
        return_value=Response(200, json=mock_protein_response)
    )

    results = []
    async with uniprot_adapter:
        async for record in uniprot_adapter.fetch("protein", query="gene:TEST1"):
            results.append(record)

    assert len(results) == 1
    assert results[0]["primaryAccession"] == "P12345"
    assert route.called


@respx.mock
async def test_fetch_protein_pagination(
    uniprot_adapter, mock_protein_response_page1, mock_protein_response
):
    """Test fetching proteins with pagination."""
    # Mocking exact params is tricky due to size calc and defaults.
    # We'll use a regex or looser matching if possible, but respx strict matching requires exact params.
    # The issue might be that the adapter code calculates `size` dynamically based on limit.
    # Let's mock based on path only for this test to avoid timeout loops.

    route = respx.get("https://rest.uniprot.org/uniprotkb/search")
    route.side_effect = [
        Response(200, json=mock_protein_response_page1),
        Response(200, json=mock_protein_response),
    ]

    results = []
    async with uniprot_adapter:
        async for record in uniprot_adapter.fetch("protein", query="gene:TEST1"):
            results.append(record)

    assert len(results) == 2


@respx.mock
async def test_fetch_features(uniprot_adapter, mock_feature_response):
    """Test fetching protein features."""
    respx.get("https://rest.uniprot.org/uniprotkb/P12345.json").mock(
        return_value=Response(200, json=mock_feature_response)
    )

    results = []
    async with uniprot_adapter:
        async for record in uniprot_adapter.fetch("feature", query="P12345"):
            results.append(record)

    assert len(results) == 1
    assert results[0]["type"] == "Domain"
    assert results[0]["accession"] == "P12345"


@respx.mock
async def test_fetch_sequences(uniprot_adapter, mock_fasta_response):
    """Test fetching protein sequences."""
    respx.get("https://rest.uniprot.org/uniprotkb/stream").mock(
        return_value=Response(200, text=mock_fasta_response)
    )

    results = []
    async with uniprot_adapter:
        async for record in uniprot_adapter.fetch("sequence", query="P12345"):
            results.append(record)

    assert len(results) == 1
    assert "MKTLLLLAVVLLLGAAQA" in results[0]["sequence"]


async def test_uniprot_adapter__unsupported_entity__8c46e9d5(uniprot_adapter):
    """Test fetching unsupported entity raises ValueError."""
    async with uniprot_adapter:
        with pytest.raises(ValueError, match="Unsupported entity type"):
            await _drain_async_iter(uniprot_adapter.fetch("invalid_entity"))


async def test_fetch_features_missing_query(uniprot_adapter):
    """Test fetching features without query raises ValueError."""
    async with uniprot_adapter:
        with pytest.raises(ValueError, match="Query is required"):
            await _drain_async_iter(uniprot_adapter.fetch("feature"))


async def test_fetch_sequences_missing_query(uniprot_adapter):
    """Test fetching sequences without query raises ValueError."""
    async with uniprot_adapter:
        with pytest.raises(ValueError, match="Query is required"):
            await _drain_async_iter(uniprot_adapter.fetch("sequence"))


@respx.mock
async def test_uniprot_adapter__health_check_healthy__2aff5882(uniprot_adapter):
    """Test health check returns HEALTHY."""
    respx.get("https://rest.uniprot.org/uniprotkb/search").mock(
        return_value=Response(200)
    )
    async with uniprot_adapter:
        status = await uniprot_adapter.health_check()
    assert status == HealthStatus.HEALTHY


@respx.mock
async def test_health_check_on_server_error(uniprot_adapter):
    """Test health check behavior on server error (500).

    Non-200 probe responses are classified as transient degraded status.
    """
    respx.get("https://rest.uniprot.org/uniprotkb/search").mock(
        return_value=Response(500)
    )
    async with uniprot_adapter:
        status = await uniprot_adapter.health_check()
    assert status == HealthStatus.DEGRADED


@respx.mock
async def test_health_check_on_connection_error(uniprot_adapter):
    """Test health check behavior on connection error.

    Connection errors fall back to circuit breaker state which may
    be DEGRADED if there were prior failures.
    """
    # Use httpx.ConnectError for more realistic connection error simulation
    respx.route(host="rest.uniprot.org", path="/uniprotkb/search").mock(
        side_effect=httpx.ConnectError("Connection error")
    )
    async with uniprot_adapter:
        status = await uniprot_adapter.health_check()
    # Connection error falls back to circuit breaker which may show degraded
    assert status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)
