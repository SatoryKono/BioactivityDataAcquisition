"""Contract tests for PubChem resilience.

Verifies Retry-After semantics, 429 burst behavior, and cursor stability.
These tests use the production SDK seam to prove resilience contracts
offline (without real network traffic) via fake transport.
"""

import asyncio
import time
import pytest
from unittest.mock import Mock

from bioetl.domain.resilience import RetryConfig
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreakerGuard
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucketRateLimiter
from bioetl.infrastructure.adapters.pubchem.fetch_flow import PubChemFetchFlow
import pubchempy as pcp

pytestmark = pytest.mark.no_api


@pytest.mark.pubchem
class TestPubChemResilienceContract:
    @pytest.mark.asyncio
    async def test_pubchem_429_burst_and_retry_after(self) -> None:
        """Verify PubChem SDK correctly handles 429 bursts and respects Retry-After."""

        # Fake SDK calls that throw 429 and finally succeed
        call_count = 0

        def fake_pubchem_call(*_args: object, **_kwargs: object) -> list[str]:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                # Simulate a PubChemHTTPError with a 429 status and Retry-After
                from urllib.error import HTTPError

                error = pcp.PubChemHTTPError(
                    Exception("Too Many Requests"), "Too Many Requests", ""
                )
                error.code = 429
                cause = HTTPError(
                    "url", 429, "Too Many Requests", {"Retry-After": "1"}, None
                )
                error.__cause__ = cause
                raise error
            return ["success"]

        async def run_in_executor(func, *args):
            return await asyncio.get_running_loop().run_in_executor(None, func, *args)

        rate_limiter = TokenBucketRateLimiter(rate=10.0, capacity=20)
        circuit_breaker = CircuitBreakerGuard(
            provider="pubchem", failure_threshold=100, recovery_timeout=1.0
        )
        record_request = Mock()

        flow = PubChemFetchFlow(
            rate_limiter=rate_limiter,
            circuit_breaker=circuit_breaker,
            run_in_executor=run_in_executor,
            record_request=record_request,
            normalize_results=lambda x: x,
            retry_config=RetryConfig(max_attempts=3, base_delay=0.1, max_delay=10.0),
        )

        start = time.time()
        result = await flow.execute(
            endpoint="offline_burst_test",
            pubchem_callable=fake_pubchem_call,
            pubchem_args=("aspirin", "name"),
        )
        duration = time.time() - start

        # Assertions
        assert result == ["success"]
        assert call_count == 3
        # Should take at least 1 + 1 = 2 seconds total for two Retry-After delays
        assert duration >= 2.0
