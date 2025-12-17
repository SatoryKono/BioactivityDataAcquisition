"""Unit tests for TokenBucket rate limiter."""

from __future__ import annotations

import time

import pytest

from bioetl.infrastructure.adapters.http.rate_limiter import (
    TokenBucket,
    create_pubchem_bucket,
    create_pubmed_bucket,
)


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
