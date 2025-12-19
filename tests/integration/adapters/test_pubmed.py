# tests/integration/adapters/test_pubmed.py
import pytest
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket
from bioetl.infrastructure.adapters.pubmed.pubmed_client import PubMedAdapter
from bioetl.infrastructure.config import get_settings # Import get_settings

@pytest.fixture
def pubmed_adapter(monkeypatch) -> PubMedAdapter:
    """Fixture to provide a PubMedAdapter instance for testing."""
    monkeypatch.setenv("BIOETL_TEST_MODE", "true")
    get_settings.cache_clear()
    settings = get_settings() # Load settings
    
    # Use actual rate from settings if API key is present
    rate = 10.0 if settings.pubmed_api_key and settings.pubmed_api_key.get_secret_value() else 3.0

    http_client = UnifiedHTTPClient(
        TokenBucket(rate=rate, capacity=rate * 2),
        CircuitBreaker(provider="pubmed_test")
    )
    return PubMedAdapter(
        http_client=http_client,
        email=settings.default_email, # Use email from settings
        api_key=settings.pubmed_api_key.get_secret_value() if settings.pubmed_api_key else None # Use API key from settings
    )

@pytest.mark.integration
@pytest.mark.vcr
async def test_fetch_publications(pubmed_adapter: PubMedAdapter):
    """
    Tests fetching publications from PubMed.
    This test requires a VCR cassette. To record:
    pytest tests/integration/adapters/test_pubmed.py::test_fetch_publications --vcr-record=new_episodes
    """
    async with pubmed_adapter.http_client:
        records = []
        async for record in pubmed_adapter.fetch("publication", search_term="crispr", limit=5):
            records.append(record)
        
        assert len(records) == 5
        for record in records:
            assert "pmid" in record
            assert "article_title" in record
            assert "_raw_xml" in record
            assert record["pmid"] is not None

@pytest.mark.integration
@pytest.mark.vcr
async def test_health_check(pubmed_adapter: PubMedAdapter):
    """
    Tests the health check for the PubMed API.
    This test requires a VCR cassette. To record:
    pytest tests/integration/adapters/test_pubmed.py::test_health_check --vcr-record=new_episodes
    """
    async with pubmed_adapter.http_client:
        status = await pubmed_adapter.health_check()
        assert status == HealthStatus.HEALTHY
