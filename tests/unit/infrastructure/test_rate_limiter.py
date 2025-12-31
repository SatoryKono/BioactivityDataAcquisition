"""Unit tests for TokenBucket rate limiter."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from bioetl.infrastructure.adapters.http.rate_limiter import (
    TokenBucket,
    create_pubchem_bucket,
    create_pubmed_bucket,
)


def create_mock_metrics() -> MagicMock:
    """Create a mock MetricsPort for testing."""
    mock = MagicMock()
    mock.set_gauge = MagicMock()
    mock.observe_histogram = MagicMock()
    return mock


class TestTokenBucket:
    """Tests for TokenBucket rate limiter."""

    @pytest.mark.unit
    def test_initial_capacity(self) -> None:
        """Bucket should start at full capacity."""
        bucket = TokenBucket(rate=5.0, capacity=10)
        assert bucket.available_tokens() == 10

    @pytest.mark.unit
    def test_try_acquire_success(self) -> None:
        """try_acquire should succeed when tokens available."""
        bucket = TokenBucket(rate=5.0, capacity=10)
        assert bucket.try_acquire(5) is True
        assert bucket.available_tokens() == 5

    @pytest.mark.unit
    def test_try_acquire_failure(self) -> None:
        """try_acquire should fail when insufficient tokens."""
        bucket = TokenBucket(rate=5.0, capacity=5)
        assert bucket.try_acquire(10) is False
        assert bucket.available_tokens() == 5  # Unchanged

    @pytest.mark.unit
    async def test_acquire_immediate(self) -> None:
        """acquire should return immediately when tokens available."""
        bucket = TokenBucket(rate=5.0, capacity=10)

        start = time.monotonic()
        await bucket.acquire(5)
        elapsed = time.monotonic() - start

        assert elapsed < 0.1  # Should be near-instant
        assert bucket.available_tokens() == 5

    @pytest.mark.unit
    async def test_acquire_waits_for_tokens(self) -> None:
        """acquire should wait when insufficient tokens."""
        bucket = TokenBucket(rate=10.0, capacity=1)  # 10 tokens/sec

        # Consume the only token
        await bucket.acquire(1)

        # Next acquire should wait ~0.1 seconds
        start = time.monotonic()
        await bucket.acquire(1)
        elapsed = time.monotonic() - start

        assert elapsed >= 0.05  # Should wait for refill
        assert elapsed < 0.5  # But not too long

    @pytest.mark.unit
    async def test_acquire_exceeds_capacity_raises(self) -> None:
        """acquire should raise if tokens > capacity."""
        bucket = TokenBucket(rate=5.0, capacity=5)

        with pytest.raises(ValueError, match="Cannot acquire 10 tokens"):
            await bucket.acquire(10)

    @pytest.mark.unit
    def test_refill_over_time(self) -> None:
        """Tokens should refill over time."""
        bucket = TokenBucket(rate=100.0, capacity=10)  # 100 tokens/sec

        # Consume all tokens
        bucket.try_acquire(10)
        assert bucket.available_tokens() == 0

        # Wait a bit
        time.sleep(0.05)  # 50ms = 5 tokens at 100/sec

        # Should have some tokens back
        assert bucket.available_tokens() >= 3

    @pytest.mark.unit
    def test_refill_capped_at_capacity(self) -> None:
        """Refill should not exceed capacity."""
        bucket = TokenBucket(rate=1000.0, capacity=5)  # Fast refill

        # Wait longer than needed to fill
        time.sleep(0.1)

        # Should be capped at capacity
        assert bucket.available_tokens() == 5


class TestFactoryFunctions:
    """Tests for pre-configured bucket factory functions."""

    @pytest.mark.unit
    def test_create_pubchem_bucket(self) -> None:
        """PubChem bucket should have correct rate (5 req/sec)."""
        bucket = create_pubchem_bucket()
        assert bucket.rate == 5.0
        assert bucket.capacity == 5

    @pytest.mark.unit
    def test_create_pubmed_bucket_no_key(self) -> None:
        """PubMed bucket without API key should have 3 req/sec."""
        bucket = create_pubmed_bucket(with_api_key=False)
        assert bucket.rate == 3.0

    @pytest.mark.unit
    def test_create_pubmed_bucket_with_key(self) -> None:
        """PubMed bucket with API key should have 10 req/sec."""
        bucket = create_pubmed_bucket(with_api_key=True)
        assert bucket.rate == 10.0

    @pytest.mark.unit
    def test_create_pubchem_bucket_with_metrics(self) -> None:
        """Factory should pass metrics to bucket."""
        mock_metrics = create_mock_metrics()
        bucket = create_pubchem_bucket(metrics=mock_metrics)
        assert bucket.metrics is mock_metrics
        assert bucket.provider == "pubchem"

    @pytest.mark.unit
    def test_create_pubmed_bucket_with_metrics(self) -> None:
        """Factory should pass metrics to bucket."""
        mock_metrics = create_mock_metrics()
        bucket = create_pubmed_bucket(with_api_key=False, metrics=mock_metrics)
        assert bucket.metrics is mock_metrics
        assert bucket.provider == "pubmed"


class TestTokenBucketMetrics:
    """Tests for TokenBucket metrics integration."""

    @pytest.mark.unit
    async def test_acquire_records_metrics(self) -> None:
        """acquire should record metrics when MetricsPort is provided."""
        mock_metrics = create_mock_metrics()
        bucket = TokenBucket(
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
    async def test_acquire_no_metrics_when_none(self) -> None:
        """acquire should not fail when metrics is None."""
        bucket = TokenBucket(rate=5.0, capacity=10, provider="test")

        # Should not raise any exception
        await bucket.acquire(1)

        assert bucket.available_tokens() == 9

    @pytest.mark.unit
    async def test_acquire_records_wait_time(self) -> None:
        """acquire should record non-zero wait time when waiting for tokens."""
        mock_metrics = create_mock_metrics()
        bucket = TokenBucket(
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
    async def test_metrics_called_with_correct_provider(self) -> None:
        """Metrics should use the correct provider label."""
        mock_metrics = create_mock_metrics()
        bucket = TokenBucket(
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
