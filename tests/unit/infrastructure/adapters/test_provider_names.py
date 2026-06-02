"""Unit tests for adapter provider names."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock

import pytest

from bioetl.infrastructure.adapters.common.adapter_defaults import (
    create_default_error_handler,
)
from bioetl.infrastructure.adapters.common.api_request_collector import (
    APIRequestCollector,
)
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreakerGuard
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucketRateLimiter
from bioetl.infrastructure.adapters.pubchem import PubChemAdapter
from bioetl.infrastructure.adapters.pubchem.entity_mapper import PubChemEntityMapper
from bioetl.infrastructure.adapters.uniprot import UniProtAdapter
from tests.helpers.adapter_runtime import build_http_adapter_runtime_kwargs


pytestmark = pytest.mark.unit


class TestAdapterProviderNames:
    """Test that adapters have correct provider names."""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        return MagicMock()

    @pytest.fixture
    def pubchem_dependencies(self):
        """Create dependencies for PubChemAdapter."""
        rate_limiter = TokenBucketRateLimiter(rate=5.0, capacity=10, provider="pubchem")
        circuit_breaker = CircuitBreakerGuard(provider="pubchem", failure_threshold=5)
        thread_pool = ThreadPoolExecutor(max_workers=2)
        yield rate_limiter, circuit_breaker, thread_pool
        thread_pool.shutdown(wait=False)

    def test_pubchem_provider_name(self, mock_logger, pubchem_dependencies):
        """Test PubChemAdapter provider name."""
        rate_limiter, circuit_breaker, thread_pool = pubchem_dependencies
        adapter = PubChemAdapter(
            logger=mock_logger,
            rate_limiter=rate_limiter,
            circuit_breaker=circuit_breaker,
            thread_pool=thread_pool,
            error_handler=create_default_error_handler(
                logger=mock_logger,
                metrics=None,
            ),
            request_collector=APIRequestCollector(),
            entity_mapper=PubChemEntityMapper(),
            fetch_strategies=MagicMock(name="fetch_strategies"),
        )
        assert adapter.provider_name == "pubchem"
        assert PubChemAdapter.provider_name == "pubchem"

    def test_uniprot_provider_name(self, mock_logger):
        """Test UniProtAdapter provider name."""
        mock_http_client = MagicMock()
        adapter = UniProtAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
            **build_http_adapter_runtime_kwargs(
                "uniprot",
                logger=mock_logger,
                include_fallback_service=True,
            ),
        )
        assert adapter.provider_name == "uniprot"
        assert UniProtAdapter.provider_name == "uniprot"
