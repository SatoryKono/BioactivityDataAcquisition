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
"""Unit tests for RetryConfig."""

from __future__ import annotations

import hashlib

import pytest

from bioetl.domain.resilience import RetryConfig


@pytest.mark.unit
class TestRetryConfig:
    """Tests for RetryConfig."""

    def test_config_retry_config__default_values__0e25d664(self) -> None:
        """Test default configuration values."""
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.retry_budget_per_request is None
        assert config.base_delay == pytest.approx(1.0)
        assert config.max_delay == pytest.approx(60.0)
        assert config.max_retry_after_seconds is None
        assert config.multiplier == pytest.approx(2.0)
        assert config.jitter_range == (0.1, 0.5)
        assert config.retryable_statuses == frozenset({429, 500, 502, 503, 504})
        assert ConnectionError in config.retryable_exceptions
        assert TimeoutError in config.retryable_exceptions

    def test_calculate_delay_first_attempt(self) -> None:
        """Test delay calculation for first attempt (no jitter)."""
        config = RetryConfig(base_delay=1.0, multiplier=2.0, jitter_range=(0.0, 0.0))
        delay = config.calculate_delay(0)
        assert delay == pytest.approx(1.0)

    def test_calculate_delay_second_attempt(self) -> None:
        """Test delay calculation for second attempt (no jitter)."""
        config = RetryConfig(base_delay=1.0, multiplier=2.0, jitter_range=(0.0, 0.0))
        delay = config.calculate_delay(1)
        assert delay == pytest.approx(2.0)

    def test_calculate_delay_third_attempt(self) -> None:
        """Test delay calculation for third attempt (no jitter)."""
        config = RetryConfig(base_delay=1.0, multiplier=2.0, jitter_range=(0.0, 0.0))
        delay = config.calculate_delay(2)
        assert delay == pytest.approx(4.0)

    def test_calculate_delay_respects_max_delay(self) -> None:
        """Test that delay is capped at max_delay."""
        config = RetryConfig(
            base_delay=10.0, multiplier=2.0, max_delay=15.0, jitter_range=(0.0, 0.0)
        )
        delay = config.calculate_delay(5)
        assert delay == pytest.approx(15.0)

    def test_is_retryable_status(self) -> None:
        """Test is_retryable_status method."""
        config = RetryConfig()
        assert config.is_retryable_status(429)
        assert config.is_retryable_status(500)
        assert config.is_retryable_status(502)
        assert config.is_retryable_status(503)
        assert config.is_retryable_status(504)
        assert not config.is_retryable_status(200)
        assert not config.is_retryable_status(400)
        assert not config.is_retryable_status(401)

    def test_is_retryable_exception(self) -> None:
        """Test is_retryable_exception method."""
        config = RetryConfig()
        assert config.is_retryable_exception(ConnectionError("test"))
        assert config.is_retryable_exception(TimeoutError("test"))
        assert not config.is_retryable_exception(ValueError("test"))

    def test_custom_retryable_statuses(self) -> None:
        """Test custom retryable status codes."""
        config = RetryConfig(retryable_statuses=frozenset({500, 502}))
        assert config.is_retryable_status(500)
        assert config.is_retryable_status(502)
        assert not config.is_retryable_status(429)

    def test_jitter_same_input_same_output(self) -> None:
        """Test jitter produces same delay for same inputs (deterministic)."""
        config = RetryConfig(
            base_delay=10.0,
            jitter_range=(0.1, 0.3),
            jitter_seed=42,
        )
        url = "https://api.example.com/data"

        delay1 = config.calculate_delay(attempt=0, url=url)
        delay2 = config.calculate_delay(attempt=0, url=url)
        delay3 = config.calculate_delay(attempt=0, url=url)

        assert delay1 == delay2 == delay3

        delay_a1 = config.calculate_delay(attempt=1, url=url)
        delay_a1_again = config.calculate_delay(attempt=1, url=url)
        assert delay_a1 == delay_a1_again

    def test_jitter_different_urls_different_output(self) -> None:
        """Test jitter produces different delays for different URLs."""
        config = RetryConfig(
            base_delay=10.0,
            jitter_range=(0.1, 0.2),
            jitter_seed=42,
        )

        delay1 = config.calculate_delay(attempt=0, url="https://api.example.com/data1")
        delay2 = config.calculate_delay(attempt=0, url="https://api.example.com/data2")

        assert delay1 != delay2
        assert 11.0 <= delay1 <= 12.0
        assert 11.0 <= delay2 <= 12.0

    def test_jitter_cross_process_stability(self) -> None:
        """Test deterministic jitter produces stable values across processes."""
        config = RetryConfig(
            base_delay=10.0,
            jitter_range=(0.1, 0.2),
            jitter_seed=42,
        )
        url = "https://api.example.com/test"

        hash_input = f"0:{url}:42"
        digest = hashlib.md5(hash_input.encode(), usedforsecurity=False).hexdigest()
        jitter_factor = int(digest[:8], 16) / 0xFFFFFFFF

        base_delay = 10.0
        jitter_min, jitter_max = 0.1, 0.2
        jitter_span = jitter_max - jitter_min
        jitter_amount = jitter_min + (jitter_span * jitter_factor)
        expected_delay = min(base_delay * (1 + jitter_amount), config.max_delay)

        actual_delay = config.calculate_delay(attempt=0, url=url)

        assert actual_delay == pytest.approx(expected_delay), (
            f"Jitter calculation mismatch. Expected {expected_delay}, got {actual_delay}. "
            "This may indicate the implementation uses Python's hash() instead of MD5."
        )
        assert config.calculate_delay(attempt=0, url=url) == pytest.approx(
            expected_delay
        )
        assert config.calculate_delay(attempt=0, url=url) == pytest.approx(
            expected_delay
        )

    def test_is_last_attempt(self) -> None:
        """Test is_last_attempt method."""
        config = RetryConfig(max_attempts=3)
        assert not config.is_last_attempt(0)
        assert not config.is_last_attempt(1)
        assert config.is_last_attempt(2)
        assert config.is_last_attempt(3)

    def test_effective_retry_budget(self) -> None:
        """Test effective retry budget resolution."""
        default_config = RetryConfig(max_attempts=4)
        assert default_config.effective_retry_budget() == 3

        budgeted_config = RetryConfig(max_attempts=4, retry_budget_per_request=1)
        assert budgeted_config.effective_retry_budget() == 1

        oversized_budget = RetryConfig(max_attempts=3, retry_budget_per_request=10)
        assert oversized_budget.effective_retry_budget() == 2

    def test_clamp_retry_after(self) -> None:
        """Test Retry-After clamping behavior."""
        config = RetryConfig(max_delay=30.0)
        assert config.clamp_retry_after(120.0) == pytest.approx(30.0)

        custom_cap = RetryConfig(max_delay=60.0, max_retry_after_seconds=10.0)
        assert custom_cap.clamp_retry_after(25.0) == pytest.approx(10.0)
