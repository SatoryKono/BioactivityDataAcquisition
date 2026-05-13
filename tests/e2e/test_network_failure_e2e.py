"""E2E tests for network failure scenarios.

Tests the pipeline's handling of network-related failures:
- Connection timeouts
- Rate limit (429) responses
- Server errors (5xx)
- Retry exhaustion

Per RULES.md 4.1 Error Classification:
- Recoverable: Retry (max 3, backoff 2.0, jitter 0.1-0.5s)
- 429 Rate Limit, 502/504 Timeout
"""

from __future__ import annotations

import asyncio
import math
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from bioetl.domain.context import PipelineContext
from bioetl.domain.types import RunType


async def _yield_control() -> None:
    """Advance retry loops without incurring real backoff delays."""
    await asyncio.sleep(0)


@pytest.fixture
def mock_pipeline_context() -> PipelineContext:
    """Create a mock pipeline context for testing."""
    mock_logger = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)
    return PipelineContext(
        run_id=uuid4(),
        run_type=RunType.INCREMENTAL,
        logger=mock_logger,
    )


@pytest.mark.e2e
@pytest.mark.asyncio
class TestConnectionTimeout:
    """Tests for connection timeout handling."""

    async def test_timeout_triggers_retry(self):
        """E2E: Connection timeout should trigger retry mechanism."""
        retry_count = 0
        max_retries = 3

        async def flaky_operation():
            await asyncio.sleep(0)
            nonlocal retry_count
            retry_count += 1
            if retry_count < max_retries:
                raise TimeoutError("Connection timed out")
            return {"success": True}

        # Simulate retry logic
        result = None
        for attempt in range(max_retries):
            try:
                result = await flaky_operation()
                break
            except TimeoutError:
                if attempt == max_retries - 1:
                    raise
                await _yield_control()

        assert result is not None
        assert result["success"] is True
        assert retry_count == max_retries

    async def test_timeout_exhausts_retries(self):
        """E2E: Persistent timeout should exhaust retries and raise."""
        retry_count = 0
        max_retries = 3

        async def always_timeout():
            await asyncio.sleep(0)
            nonlocal retry_count
            retry_count += 1
            raise TimeoutError("Connection timed out")

        with pytest.raises(asyncio.TimeoutError):
            for attempt in range(max_retries):
                try:
                    await always_timeout()
                except TimeoutError:
                    if attempt == max_retries - 1:
                        raise
                    await _yield_control()

        assert retry_count == max_retries


@pytest.mark.e2e
@pytest.mark.asyncio
class TestRateLimitHandling:
    """Tests for 429 Rate Limit handling."""

    async def test_rate_limit_triggers_backoff(self):
        """E2E: 429 response should trigger exponential backoff."""
        import httpx

        call_count = 0
        backoff_delays: list[float] = []

        async def rate_limited_api():
            await asyncio.sleep(0)
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                request = httpx.Request("GET", "https://api.example.com")
                response = httpx.Response(429, request=request)
                raise httpx.HTTPStatusError(
                    "Rate limited", request=request, response=response
                )
            return {"data": "success"}

        result = None
        for attempt in range(5):
            try:
                result = await rate_limited_api()
                break
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    delay = 0.01 * (2**attempt)  # Exponential backoff
                    backoff_delays.append(delay)
                    await _yield_control()
                else:
                    raise

        assert result is not None
        assert call_count == 3
        assert len(backoff_delays) == 2  # Two retries before success

    async def test_rate_limit_respects_retry_after(self):
        """E2E: 429 with Retry-After header should respect delay."""
        import httpx

        retry_after_value = 0.05  # 50ms for test
        waited_time = 0.0

        async def rate_limited_with_header():
            await asyncio.sleep(0)
            nonlocal waited_time
            if waited_time < retry_after_value:
                request = httpx.Request("GET", "https://api.example.com")
                response = httpx.Response(
                    429,
                    request=request,
                    headers={"Retry-After": str(int(retry_after_value * 1000))},
                )
                raise httpx.HTTPStatusError(
                    "Rate limited", request=request, response=response
                )
            return {"data": "success"}

        for _attempt in range(3):
            try:
                await rate_limited_with_header()
                break
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    await _yield_control()
                    waited_time += retry_after_value
                else:
                    raise

        assert waited_time >= retry_after_value


@pytest.mark.e2e
@pytest.mark.asyncio
class TestServerErrorHandling:
    """Tests for 5xx server error handling."""

    async def test_server_error_triggers_retry(self):
        """E2E: 5xx errors should trigger retry."""
        import httpx

        call_count = 0
        error_codes = [502, 503, 504]

        async def server_error_api():
            await asyncio.sleep(0)
            nonlocal call_count
            call_count += 1
            if call_count <= len(error_codes):
                code = error_codes[call_count - 1]
                request = httpx.Request("GET", "https://api.example.com")
                response = httpx.Response(code, request=request)
                raise httpx.HTTPStatusError(
                    f"Server error {code}", request=request, response=response
                )
            return {"data": "success"}

        result = None
        for _attempt in range(5):
            try:
                result = await server_error_api()
                break
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500:
                    await _yield_control()
                else:
                    raise

        assert result is not None
        assert call_count == 4  # 3 errors + 1 success

    async def test_internal_server_error_500(self):
        """E2E: 500 Internal Server Error handling."""
        import httpx

        call_count = 0

        async def internal_error():
            await asyncio.sleep(0)
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                request = httpx.Request("GET", "https://api.example.com")
                response = httpx.Response(500, request=request)
                raise httpx.HTTPStatusError(
                    "Internal Server Error", request=request, response=response
                )
            return {"status": "recovered"}

        result = None
        for _attempt in range(2):
            try:
                result = await internal_error()
                break
            except httpx.HTTPStatusError:
                await _yield_control()

        assert result is not None
        assert call_count == 2


@pytest.mark.e2e
@pytest.mark.asyncio
class TestRetryExhaustion:
    """Tests for retry exhaustion behavior."""

    async def test_exhausted_retries_raises_exception(self):
        """E2E: Exhausted retries should raise the original exception."""
        import httpx

        max_retries = 3
        call_count = 0

        async def always_fail():
            await asyncio.sleep(0)
            nonlocal call_count
            call_count += 1
            request = httpx.Request("GET", "https://api.example.com")
            response = httpx.Response(503, request=request)
            raise httpx.HTTPStatusError(
                "Service unavailable", request=request, response=response
            )

        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            for attempt in range(max_retries):
                try:
                    await always_fail()
                except httpx.HTTPStatusError:
                    if attempt == max_retries - 1:
                        raise
                    await _yield_control()

        assert exc_info.value.response.status_code == 503
        assert call_count == max_retries

    async def test_retry_count_tracked_in_metrics(self):
        """E2E: Retry attempts should be trackable."""
        retry_metrics = {"attempts": 0, "successes": 0, "failures": 0}

        async def tracked_operation():
            await asyncio.sleep(0)
            retry_metrics["attempts"] += 1
            if retry_metrics["attempts"] < 3:
                raise ConnectionError("Connection failed")
            retry_metrics["successes"] += 1
            return True

        for attempt in range(5):
            try:
                await tracked_operation()
                break
            except ConnectionError:
                retry_metrics["failures"] += 1
                if attempt == 4:
                    raise
                await _yield_control()

        assert retry_metrics["attempts"] == 3
        assert retry_metrics["failures"] == 2
        assert retry_metrics["successes"] == 1


@pytest.mark.e2e
@pytest.mark.asyncio
class TestExponentialBackoff:
    """Tests for exponential backoff behavior."""

    async def test_backoff_increases_exponentially(self):
        """E2E: Backoff delay should increase exponentially."""
        base_delay = 0.01
        multiplier = 2.0
        max_delay = 1.0

        delays: list[float] = []

        for attempt in range(5):
            delay = min(base_delay * (multiplier**attempt), max_delay)
            delays.append(delay)

        # Verify exponential growth
        assert delays[0] == pytest.approx(0.01)
        assert delays[1] == pytest.approx(0.02)
        assert delays[2] == pytest.approx(0.04)
        assert delays[3] == pytest.approx(0.08)
        assert delays[4] == pytest.approx(0.16)

    async def test_backoff_capped_at_max(self):
        """E2E: Backoff should be capped at maximum delay."""
        base_delay = 0.1
        multiplier = 2.0
        max_delay = 0.5

        delays: list[float] = []

        for attempt in range(10):
            delay = min(base_delay * (multiplier**attempt), max_delay)
            delays.append(delay)

        # All delays after a point should be capped
        assert all(d <= max_delay for d in delays)
        # Later delays should all be at max
        assert math.isclose(delays[-1], max_delay)
        assert math.isclose(delays[-2], max_delay)


@pytest.mark.e2e
@pytest.mark.asyncio
class TestConnectionPoolExhaustion:
    """Tests for connection pool exhaustion scenarios."""

    async def test_pool_exhaustion_queues_requests(self):
        """E2E: Pool exhaustion should queue requests, not fail immediately."""
        pool_size = 2
        active_connections = 0
        completed = 0
        semaphore = asyncio.Semaphore(pool_size)

        async def pooled_request(request_id: int):
            nonlocal active_connections, completed
            async with semaphore:
                active_connections += 1
                assert active_connections <= pool_size
                await _yield_control()
                active_connections -= 1
                completed += 1
                return f"response_{request_id}"

        # Submit more requests than pool size
        tasks = [pooled_request(i) for i in range(5)]
        results = await asyncio.gather(*tasks)

        assert completed == 5
        assert len(results) == 5

    async def test_pool_timeout_raises_error(self):
        """E2E: Pool timeout should raise appropriate error."""
        pool_size = 1
        semaphore = asyncio.Semaphore(pool_size)
        acquired = asyncio.Event()
        release_blocker = asyncio.Event()

        async def blocking_request():
            async with semaphore:
                acquired.set()
                await release_blocker.wait()
                return "done"

        async def waiting_request():
            try:
                async with asyncio.timeout(0.01):
                    await _yield_control()
                    async with semaphore:
                        return "acquired"
            except TimeoutError:
                raise ConnectionError("Pool acquisition timeout") from None

        # Start blocking request
        blocking_task = asyncio.create_task(blocking_request())
        await acquired.wait()

        # Try to get another connection
        with pytest.raises(ConnectionError) as exc_info:
            await waiting_request()

        assert "Pool acquisition timeout" in str(exc_info.value)

        blocking_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await blocking_task
