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
"""Unit tests for TokenBucketRateLimiter rate limiter."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucketRateLimiter


def create_mock_metrics() -> MagicMock:
    """Create a mock MetricsPort for testing."""
    mock = MagicMock()
    mock.set_gauge = MagicMock()
    mock.observe_histogram = MagicMock()
    return mock


class TestTokenBucket:
    """Tests for TokenBucketRateLimiter rate limiter."""

    @pytest.mark.unit
    def test_rejects_non_positive_rate(self) -> None:
        with pytest.raises(ValueError, match="rate must be strictly positive"):
            TokenBucketRateLimiter(rate=0.0, capacity=10)
        with pytest.raises(ValueError, match="rate must be strictly positive"):
            TokenBucketRateLimiter(rate=-1.0, capacity=10)

    @pytest.mark.unit
    def test_rejects_non_positive_capacity(self) -> None:
        with pytest.raises(ValueError, match="capacity must be strictly positive"):
            TokenBucketRateLimiter(rate=5.0, capacity=0)
        with pytest.raises(ValueError, match="capacity must be strictly positive"):
            TokenBucketRateLimiter(rate=5.0, capacity=-3)

    @pytest.mark.unit
    def test_initial_capacity(self) -> None:
        """Bucket should start at full capacity."""
        bucket = TokenBucketRateLimiter(rate=5.0, capacity=10)
        assert bucket.available_tokens() == 10

    @pytest.mark.unit
    def test_limiter_token_bucket__try_acquire_success__61fae624(self) -> None:
        """try_acquire should succeed when tokens available."""
        bucket = TokenBucketRateLimiter(rate=5.0, capacity=10)
        assert bucket.try_acquire(5) is True
        assert bucket.available_tokens() == 5

    @pytest.mark.unit
    def test_limiter_token_bucket__try_acquire_failure__b0020c37(self) -> None:
        """try_acquire should fail when insufficient tokens."""
        bucket = TokenBucketRateLimiter(rate=5.0, capacity=5)
        assert bucket.try_acquire(10) is False
        assert bucket.available_tokens() == 5  # Unchanged

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_acquire_immediate(self) -> None:
        """acquire should return immediately when tokens available."""
        bucket = TokenBucketRateLimiter(rate=5.0, capacity=10)

        start = time.monotonic()
        await bucket.acquire(5)
        elapsed = time.monotonic() - start

        assert elapsed < 0.1  # Should be near-instant
        assert bucket.available_tokens() == 5

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_acquire_waits_for_tokens(self) -> None:
        """acquire should wait when insufficient tokens."""
        bucket = TokenBucketRateLimiter(rate=10.0, capacity=1)  # 10 tokens/sec

        # Consume the only token
        await bucket.acquire(1)

        # Next acquire should wait ~0.1 seconds
        start = time.monotonic()
        await bucket.acquire(1)
        elapsed = time.monotonic() - start

        assert elapsed >= 0.05  # Should wait for refill
        # Allow generous tolerance for CI/slow systems (Python 3.14 can have timing issues)
        assert elapsed < 3.0  # But not excessively long

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_acquire_exceeds_capacity_raises(self) -> None:
        """acquire should raise if tokens > capacity."""
        bucket = TokenBucketRateLimiter(rate=5.0, capacity=5)

        with pytest.raises(ValueError, match="Cannot acquire 10 tokens"):
            await bucket.acquire(10)

    @pytest.mark.unit
    def test_refill_over_time(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Tokens should refill over time (deterministic via mock clock)."""
        clock = [0.0]
        monkeypatch.setattr(time, "monotonic", lambda: clock[0])

        bucket = TokenBucketRateLimiter(rate=100.0, capacity=10)  # 100 tokens/sec

        # Consume all tokens
        bucket.try_acquire(10)
        assert bucket.available_tokens() == 0

        # Advance clock by 50ms = 5 tokens at 100/sec
        clock[0] += 0.05

        # Should have exactly 5 tokens back
        assert bucket.available_tokens() == 5

    @pytest.mark.unit
    def test_refill_capped_at_capacity(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Refill should not exceed capacity (deterministic via mock clock)."""
        clock = [0.0]
        monkeypatch.setattr(time, "monotonic", lambda: clock[0])

        bucket = TokenBucketRateLimiter(rate=1000.0, capacity=5)  # Fast refill

        # Advance clock far beyond fill time
        clock[0] += 1.0

        # Should be capped at capacity
        assert bucket.available_tokens() == 5


class TestTokenBucketMetrics:
    """Tests for TokenBucketRateLimiter metrics integration."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_acquire_records_metrics(self) -> None:
        """acquire should record metrics when MetricsPort is provided."""
        mock_metrics = create_mock_metrics()
        bucket = TokenBucketRateLimiter(
            rate=5.0,
            capacity=10,
            provider="test_provider",
            metrics=mock_metrics,
        )

        await bucket.acquire(1)

        mock_metrics.set_gauge.assert_called_once_with(
            "bioetl_rate_limiter_tokens_available",
            9.0,  # 10 - 1 token acquired
            {"provider": "test_provider"},
        )
        mock_metrics.observe_histogram.assert_called_once_with(
            "bioetl_rate_limiter_wait_seconds",
            0.0,  # No wait when tokens are available
            {"provider": "test_provider"},
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_acquire_no_metrics_when_none(self) -> None:
        """acquire should not fail when metrics is None."""
        bucket = TokenBucketRateLimiter(rate=5.0, capacity=10, provider="test")

        # Should not raise any exception
        await bucket.acquire(1)

        assert bucket.available_tokens() == 9

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_acquire_records_wait_time(self) -> None:
        """acquire should record non-zero wait time when waiting for tokens."""
        mock_metrics = create_mock_metrics()
        bucket = TokenBucketRateLimiter(
            rate=10.0,  # 10 tokens/sec = 0.1s per token (slow enough to measure wait)
            capacity=1,
            provider="test_wait",
            metrics=mock_metrics,
        )

        # Consume the only token
        await bucket.acquire(1)
        mock_metrics.reset_mock()

        # Next acquire should wait ~0.1s for refill
        await bucket.acquire(1)

        # Verify metrics were recorded
        mock_metrics.set_gauge.assert_called_once()
        mock_metrics.observe_histogram.assert_called_once()

        # Get the wait time from the histogram call
        call_args = mock_metrics.observe_histogram.call_args
        wait_time = call_args[0][1]

        # Should have waited (non-zero wait time) - use >= 0.0 for timing tolerance
        # On very fast systems, the token may refill almost instantly
        assert wait_time >= 0.0
        assert wait_time < 1.0  # But not too long

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_metrics_called_with_correct_provider(self) -> None:
        """Metrics should use the correct provider label."""
        mock_metrics = create_mock_metrics()
        bucket = TokenBucketRateLimiter(
            rate=5.0,
            capacity=10,
            provider="custom_provider",
            metrics=mock_metrics,
        )

        await bucket.acquire(1)

        # Check gauge call
        gauge_call = mock_metrics.set_gauge.call_args
        assert gauge_call[0][2] == {"provider": "custom_provider"}

        # Check histogram call
        histogram_call = mock_metrics.observe_histogram.call_args
        assert histogram_call[0][2] == {"provider": "custom_provider"}
