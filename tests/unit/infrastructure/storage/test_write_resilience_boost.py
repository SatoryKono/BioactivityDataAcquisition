"""Coverage boost tests for delta/resilience.py.

Targets uncovered lines: 41, 77, 83, 90, 135.
"""

from __future__ import annotations


import pytest

from bioetl.infrastructure.storage.delta.resilience import (
    AdaptiveRetryPolicy,
    SilverMergeResiliencePolicy,
    _deterministic_jitter_seconds,
    build_default_atomic_replace_retry_policy,
    build_default_silver_merge_policy,
)


def _fixed_jitter(_lo: float, _hi: float) -> float:
    """Return a deterministic jitter value for test coverage."""
    return 0.1


def _negative_jitter(_lo: float, _hi: float) -> float:
    """Return a negative jitter value to exercise clamping."""
    return -99.0


@pytest.mark.unit
class TestDeterministicJitter:
    """Tests for _deterministic_jitter_seconds (line 41)."""

    def test_zero_max_returns_zero(self) -> None:
        """Line 41: max_jitter_seconds <= 0 returns 0.0."""
        assert _deterministic_jitter_seconds(0, 0.0) == pytest.approx(0.0)
        assert _deterministic_jitter_seconds(1, -1.0) == pytest.approx(0.0)

    def test_positive_max_returns_bounded_value(self) -> None:
        """Returns value in (0, max_jitter_seconds]."""
        result = _deterministic_jitter_seconds(0, 1.0)
        assert 0.0 < result <= 1.0

    def test_phase_cycle(self) -> None:
        """Jitter cycles over 4 phases."""
        max_j = 1.0
        results = [_deterministic_jitter_seconds(i, max_j) for i in range(4)]
        assert len(set(results)) == 4

    def test_negative_retry_count_clamped(self) -> None:
        """max(0, retry_count) clamps negative values."""
        # retry_count=-1 => phase=(0%4)+1=1 => 1/4 * max
        result = _deterministic_jitter_seconds(-1, 1.0)
        assert result == pytest.approx(0.25)


@pytest.mark.unit
class TestAdaptiveRetryPolicyCalculateDelay:
    """Tests for AdaptiveRetryPolicy.calculate_delay — targets lines 77, 83, 90."""

    def test_zero_base_delay_returns_zero(self) -> None:
        """Line 77: base_delay_seconds <= 0 returns 0.0."""
        policy = AdaptiveRetryPolicy(
            enabled=True,
            max_retries=3,
            base_delay_seconds=0.0,
            max_delay_seconds=1.0,
        )
        assert policy.calculate_delay(0) == pytest.approx(0.0)
        assert policy.calculate_delay(2) == pytest.approx(0.0)

    def test_zero_max_delay_returns_zero(self) -> None:
        """Line 77: max_delay_seconds <= 0 returns 0.0."""
        policy = AdaptiveRetryPolicy(
            enabled=True,
            max_retries=3,
            base_delay_seconds=0.1,
            max_delay_seconds=0.0,
        )
        assert policy.calculate_delay(0) == pytest.approx(0.0)

    def test_non_adaptive_linear_delay(self) -> None:
        """Line 83: adaptive=False uses linear delay formula."""
        policy = AdaptiveRetryPolicy(
            enabled=True,
            max_retries=5,
            base_delay_seconds=0.1,
            max_delay_seconds=10.0,
            jitter_seconds=0.0,
            adaptive=False,
        )
        # Linear: base * (retry_count + 1)
        assert policy.calculate_delay(0) == pytest.approx(0.1)
        assert policy.calculate_delay(1) == pytest.approx(0.2)
        assert policy.calculate_delay(2) == pytest.approx(0.3)

    def test_adaptive_exponential_delay(self) -> None:
        """adaptive=True uses exponential backoff."""
        policy = AdaptiveRetryPolicy(
            enabled=True,
            max_retries=5,
            base_delay_seconds=0.1,
            max_delay_seconds=10.0,
            jitter_seconds=0.0,
            adaptive=True,
        )
        # Exponential: base * 2^retry_count
        assert policy.calculate_delay(0) == pytest.approx(0.1)
        assert policy.calculate_delay(1) == pytest.approx(0.2)
        assert policy.calculate_delay(2) == pytest.approx(0.4)

    def test_delay_bounded_by_max(self) -> None:
        """Delay is capped at max_delay_seconds."""
        policy = AdaptiveRetryPolicy(
            enabled=True,
            max_retries=10,
            base_delay_seconds=1.0,
            max_delay_seconds=2.0,
            jitter_seconds=0.0,
            adaptive=True,
        )
        # After many retries, should be capped
        assert policy.calculate_delay(10) == pytest.approx(2.0)

    def test_jitter_with_custom_jitter_fn(self) -> None:
        """Line 90: custom jitter_fn is called when provided."""
        policy = AdaptiveRetryPolicy(
            enabled=True,
            max_retries=3,
            base_delay_seconds=0.1,
            max_delay_seconds=10.0,
            jitter_seconds=0.5,
            adaptive=True,
        )
        delay = policy.calculate_delay(0, jitter_fn=_fixed_jitter)
        assert delay == pytest.approx(0.2)  # 0.1 (base) + 0.1 (jitter)

    def test_jitter_without_custom_fn_uses_deterministic(self) -> None:
        """Default jitter uses _deterministic_jitter_seconds."""
        policy = AdaptiveRetryPolicy(
            enabled=True,
            max_retries=3,
            base_delay_seconds=0.1,
            max_delay_seconds=10.0,
            jitter_seconds=0.5,
            adaptive=True,
        )
        # Should not raise, returns some value
        delay = policy.calculate_delay(0)
        assert delay >= 0.0

    def test_negative_jitter_fn_returns_zero(self) -> None:
        """Negative jitter result is clamped to 0."""
        policy = AdaptiveRetryPolicy(
            enabled=True,
            max_retries=3,
            base_delay_seconds=0.1,
            max_delay_seconds=10.0,
            jitter_seconds=0.5,
            adaptive=True,
        )
        delay = policy.calculate_delay(0, jitter_fn=_negative_jitter)
        assert delay >= 0.0

    def test_should_retry_disabled_policy(self) -> None:
        """should_retry returns False when enabled=False."""
        policy = AdaptiveRetryPolicy(
            enabled=False,
            max_retries=10,
            base_delay_seconds=0.1,
            max_delay_seconds=1.0,
        )
        assert policy.should_retry(0) is False

    def test_should_retry_exhausted(self) -> None:
        """should_retry returns False when count >= max_retries."""
        policy = AdaptiveRetryPolicy(
            enabled=True,
            max_retries=3,
            base_delay_seconds=0.1,
            max_delay_seconds=1.0,
        )
        assert policy.should_retry(2) is True
        assert policy.should_retry(3) is False


@pytest.mark.unit
class TestBuildDefaultAtomicReplaceRetryPolicy:
    """Tests for build_default_atomic_replace_retry_policy (line 135)."""

    def test_windows_returns_windows_policy(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Line 133-134: on Windows (nt) returns WINDOWS policy."""
        monkeypatch.setattr(
            "bioetl.infrastructure.storage.delta.resilience.os.name", "nt"
        )
        policy = build_default_atomic_replace_retry_policy()
        assert policy.max_retries == 20
        assert policy.base_delay_seconds == pytest.approx(0.01)

    def test_non_windows_returns_non_windows_policy(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Line 135: on non-Windows returns NON_WINDOWS policy."""
        monkeypatch.setattr(
            "bioetl.infrastructure.storage.delta.resilience.os.name", "posix"
        )
        policy = build_default_atomic_replace_retry_policy()
        assert policy.max_retries == 3
        assert policy.base_delay_seconds == pytest.approx(0.002)


@pytest.mark.unit
class TestSilverMergeResiliencePolicy:
    """Tests for SilverMergeResiliencePolicy construction."""

    def test_can_construct_with_components(self) -> None:
        """SilverMergeResiliencePolicy is a dataclass that holds sub-policies."""
        commit_retry = AdaptiveRetryPolicy(
            enabled=True,
            max_retries=2,
            base_delay_seconds=0.1,
            max_delay_seconds=1.0,
        )
        timeout_retry = AdaptiveRetryPolicy(
            enabled=True,
            max_retries=1,
            base_delay_seconds=0.2,
            max_delay_seconds=2.0,
        )
        policy = SilverMergeResiliencePolicy(
            execution_timeout_seconds=30.0,
            commit_retry=commit_retry,
            timeout_retry=timeout_retry,
        )
        assert policy.execution_timeout_seconds == pytest.approx(30.0)
        assert policy.commit_retry is commit_retry
        assert policy.timeout_retry is timeout_retry

    def test_default_policy_has_expected_values(self) -> None:
        """build_default_silver_merge_policy returns valid policy."""
        policy = build_default_silver_merge_policy()
        assert policy.execution_timeout_seconds > 0
        assert policy.commit_retry.enabled is True
        assert policy.timeout_retry.enabled is True
