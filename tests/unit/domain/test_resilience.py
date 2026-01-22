"""Unit tests for Resilience Domain Objects."""

from __future__ import annotations

import pytest
from bioetl.domain.resilience import RetryConfig

@pytest.mark.unit
class TestRetryConfig:
    """Tests for RetryConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.multiplier == 2.0
        assert config.jitter_range == (0.1, 0.5)
        assert config.retryable_statuses == frozenset({429, 500, 502, 503, 504})
        assert ConnectionError in config.retryable_exceptions
        assert TimeoutError in config.retryable_exceptions

    def test_calculate_delay_first_attempt(self):
        """Test delay calculation for first attempt (no jitter)."""
        config = RetryConfig(base_delay=1.0, multiplier=2.0, jitter_range=(0.0, 0.0))
        delay = config.calculate_delay(0)
        assert delay == 1.0

    def test_calculate_delay_second_attempt(self):
        """Test delay calculation for second attempt (no jitter)."""
        config = RetryConfig(base_delay=1.0, multiplier=2.0, jitter_range=(0.0, 0.0))
        delay = config.calculate_delay(1)
        assert delay == 2.0

    def test_calculate_delay_third_attempt(self):
        """Test delay calculation for third attempt (no jitter)."""
        config = RetryConfig(base_delay=1.0, multiplier=2.0, jitter_range=(0.0, 0.0))
        delay = config.calculate_delay(2)
        assert delay == 4.0

    def test_calculate_delay_respects_max_delay(self):
        """Test that delay is capped at max_delay."""
        config = RetryConfig(
            base_delay=10.0, multiplier=2.0, max_delay=15.0, jitter_range=(0.0, 0.0)
        )
        delay = config.calculate_delay(5)  # Would be 320 without cap
        assert delay == 15.0

    def test_is_retryable_status(self):
        """Test is_retryable_status method."""
        config = RetryConfig()
        assert config.is_retryable_status(429)
        assert config.is_retryable_status(500)  # Internal Server Error is retryable
        assert config.is_retryable_status(502)
        assert config.is_retryable_status(503)
        assert config.is_retryable_status(504)
        assert not config.is_retryable_status(200)
        assert not config.is_retryable_status(400)
        assert not config.is_retryable_status(401)

    def test_is_retryable_exception(self):
        """Test is_retryable_exception method."""
        config = RetryConfig()
        assert config.is_retryable_exception(ConnectionError("test"))
        assert config.is_retryable_exception(TimeoutError("test"))
        assert not config.is_retryable_exception(ValueError("test"))

    def test_custom_retryable_statuses(self):
        """Test custom retryable status codes."""
        config = RetryConfig(retryable_statuses=frozenset({500, 502}))
        assert config.is_retryable_status(500)
        assert config.is_retryable_status(502)
        assert not config.is_retryable_status(429)  # No longer in list

    def test_jitter_same_input_same_output(self):
        """Test jitter produces same delay for same inputs (deterministic)."""
        config = RetryConfig(
            base_delay=10.0,
            jitter_range=(0.1, 0.3),
            jitter_seed=42,
        )
        url = "https://api.example.com/data"

        # Same inputs should produce identical delays
        delay1 = config.calculate_delay(attempt=0, url=url)
        delay2 = config.calculate_delay(attempt=0, url=url)
        delay3 = config.calculate_delay(attempt=0, url=url)

        assert delay1 == delay2 == delay3

        # Different attempt numbers should also be deterministic
        delay_a1 = config.calculate_delay(attempt=1, url=url)
        delay_a1_again = config.calculate_delay(attempt=1, url=url)
        assert delay_a1 == delay_a1_again

    def test_jitter_different_urls_different_output(self):
        """Test jitter produces different delays for different URLs."""
        config = RetryConfig(
            base_delay=10.0,
            jitter_range=(0.1, 0.2),
            jitter_seed=42,
        )

        delay1 = config.calculate_delay(attempt=0, url="https://api.example.com/data1")
        delay2 = config.calculate_delay(attempt=0, url="https://api.example.com/data2")

        # Different URLs should produce different jitter values
        assert delay1 != delay2

        # Both should still be within jitter range: base * (1 + jitter)
        # With jitter_range=(0.1, 0.2), delay should be between 11.0 and 12.0
        assert 11.0 <= delay1 <= 12.0
        assert 11.0 <= delay2 <= 12.0

    def test_jitter_cross_process_stability(self):
        """Test deterministic jitter produces stable values across processes."""
        import hashlib

        config = RetryConfig(
            base_delay=10.0,
            jitter_range=(0.1, 0.2),
            jitter_seed=42,
        )
        url = "https://api.example.com/test"

        # Compute expected delay using MD5 directly (cross-process stable)
        hash_input = f"0:{url}:42"
        digest = hashlib.md5(hash_input.encode(), usedforsecurity=False).hexdigest()
        jitter_factor = int(digest[:8], 16) / 0xFFFFFFFF

        base_delay = 10.0
        jitter_min, jitter_max = 0.1, 0.2
        jitter_span = jitter_max - jitter_min
        jitter_amount = jitter_min + (jitter_span * jitter_factor)
        expected_delay = min(base_delay * (1 + jitter_amount), config.max_delay)

        # Verify implementation matches our expectation
        actual_delay = config.calculate_delay(attempt=0, url=url)

        assert actual_delay == expected_delay
        assert config.calculate_delay(attempt=0, url=url) == expected_delay
        assert config.calculate_delay(attempt=0, url=url) == expected_delay

    def test_is_last_attempt(self):
        """Test is_last_attempt method."""
        config = RetryConfig(max_attempts=3)
        assert not config.is_last_attempt(0)
        assert not config.is_last_attempt(1)
        assert config.is_last_attempt(2)
        assert config.is_last_attempt(3)  # Beyond last
