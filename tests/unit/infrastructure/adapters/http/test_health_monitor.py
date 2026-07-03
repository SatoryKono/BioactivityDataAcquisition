"""Tests for ProviderHealthMonitor (RULES.md §3.5).

Verifies health state transitions and metric emission.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from bioetl.domain.types import HealthStatus
from bioetl.domain.ports import HealthCheckResult
from bioetl.infrastructure.adapters.http._health_monitor_support import (
    emit_health_check_observability,
)
from bioetl.infrastructure.adapters.http.health_monitor import (
    ProviderHealthMonitor,
    ProviderHealthState,
)

pytestmark = pytest.mark.unit

if TYPE_CHECKING:
    from bioetl.infrastructure.adapters.http.health_monitor import (
        ProviderHealthTracker,
    )


@pytest.fixture
def mock_metrics() -> MagicMock:
    """Create mock MetricsPort."""
    return MagicMock()


@pytest.fixture
def monitor(mock_metrics: MagicMock) -> ProviderHealthMonitor:
    """Create ProviderHealthMonitor with mock metrics."""
    return ProviderHealthMonitor(metrics=mock_metrics)


class TestProviderHealthState:
    """Tests for ProviderHealthState dataclass."""

    def test_default_state(self) -> None:
        """Test default state is HEALTHY with no errors."""
        state = ProviderHealthState(provider="chembl")

        assert state.provider == "chembl"
        assert state.status == HealthStatus.HEALTHY
        assert state.consecutive_errors == 0
        assert state.last_success is None
        assert state.last_check is None

    def test_thresholds(self) -> None:
        """Test threshold constants from RULES.md §3.5."""
        assert ProviderHealthState.DEGRADED_THRESHOLD == 1
        assert ProviderHealthState.UNHEALTHY_THRESHOLD == 3
        assert ProviderHealthState.CLEAR_WINDOW_SECONDS == pytest.approx(300.0)


class TestProviderHealthMonitorStateTransitions:
    """Tests for health state transitions per RULES.md §3.5."""

    def test_healthy_to_degraded_on_first_error(
        self, monitor: ProviderHealthMonitor
    ) -> None:
        """Test transition: Healthy → Degraded on 1 error."""
        status = monitor.record_error("chembl")

        assert status == HealthStatus.DEGRADED
        state = monitor.get_state("chembl")
        assert state.consecutive_errors == 1

    def test_degraded_after_two_errors(self, monitor: ProviderHealthMonitor) -> None:
        """Test status remains DEGRADED with 2 consecutive errors."""
        monitor.record_error("chembl")  # 1st error -> DEGRADED
        status = monitor.record_error("chembl")  # 2nd error

        assert status == HealthStatus.DEGRADED
        state = monitor.get_state("chembl")
        assert state.consecutive_errors == 2

    def test_degraded_to_unhealthy_on_third_error(
        self, monitor: ProviderHealthMonitor
    ) -> None:
        """Test transition: Degraded → Unhealthy on 3rd error."""
        monitor.record_error("chembl")  # 1st -> DEGRADED
        monitor.record_error("chembl")  # 2nd -> DEGRADED
        status = monitor.record_error("chembl")  # 3rd -> UNHEALTHY

        assert status == HealthStatus.UNHEALTHY
        state = monitor.get_state("chembl")
        assert state.consecutive_errors == 3

    def test_unhealthy_to_degraded_on_success(
        self, monitor: ProviderHealthMonitor
    ) -> None:
        """Test recovery: Unhealthy → Degraded on 1 success."""
        # Get to UNHEALTHY
        monitor.record_error("chembl")
        monitor.record_error("chembl")
        monitor.record_error("chembl")
        assert monitor.get_state("chembl").status == HealthStatus.UNHEALTHY

        # Record success
        status = monitor.record_success("chembl")

        assert status == HealthStatus.DEGRADED
        state = monitor.get_state("chembl")
        assert state.consecutive_errors == 0

    def test_degraded_to_healthy_after_success(
        self, monitor: ProviderHealthMonitor
    ) -> None:
        """Test recovery: Degraded → Healthy after success and clear window.

        Note: This test mocks time to simulate 5 min window passing.
        """
        # Get to DEGRADED
        monitor.record_error("chembl")
        assert monitor.get_state("chembl").status == HealthStatus.DEGRADED

        # First success clears errors but stays DEGRADED (window not passed yet)
        monitor.record_success("chembl")
        state = monitor.get_state("chembl")
        assert state.consecutive_errors == 0
        assert (
            state.status == HealthStatus.DEGRADED
        )  # Still degraded (window not passed)

        # Simulate 5 minutes passing by setting last_success in the past
        # This simulates that the previous success happened 5+ minutes ago
        state.last_success = time.monotonic() - 301  # 5 min + 1 sec ago

        # Next success should check the window BEFORE updating last_success
        # Since last_success is 5+ min in the past, _check_clear_window returns True
        status = monitor.record_success("chembl")

        # Now should be HEALTHY since 5 min window passed
        assert status == HealthStatus.HEALTHY

    def test_success_resets_error_count(self, monitor: ProviderHealthMonitor) -> None:
        """Test that success resets consecutive error count."""
        monitor.record_error("chembl")
        monitor.record_error("chembl")
        assert monitor.get_state("chembl").consecutive_errors == 2

        monitor.record_success("chembl")
        assert monitor.get_state("chembl").consecutive_errors == 0

    def test_independent_provider_states(self, monitor: ProviderHealthMonitor) -> None:
        """Test that each provider has independent state."""
        monitor.record_error("chembl")
        monitor.record_error("chembl")
        monitor.record_error("chembl")  # chembl -> UNHEALTHY

        monitor.record_error("uniprot")  # uniprot -> DEGRADED

        assert monitor.get_state("chembl").status == HealthStatus.UNHEALTHY
        assert monitor.get_state("uniprot").status == HealthStatus.DEGRADED
        assert (
            monitor.get_state("pubchem").status == HealthStatus.HEALTHY
        )  # Never errored


class TestProviderHealthMonitorHealthCheck:
    """Tests for health check result recording."""

    def test_unhealthy_health_check_transitions_to_unhealthy(
        self, monitor: ProviderHealthMonitor
    ) -> None:
        """Test that UNHEALTHY health check immediately transitions to UNHEALTHY."""
        # Provider starts HEALTHY
        assert monitor.get_state("chembl").status == HealthStatus.HEALTHY

        status = monitor.record_health_check_result("chembl", HealthStatus.UNHEALTHY)

        assert status == HealthStatus.UNHEALTHY
        state = monitor.get_state("chembl")
        assert state.consecutive_errors == ProviderHealthState.UNHEALTHY_THRESHOLD

    def test_healthy_health_check_recovers_from_unhealthy(
        self, monitor: ProviderHealthMonitor
    ) -> None:
        """Test that HEALTHY health check starts recovery from UNHEALTHY."""
        # Get to UNHEALTHY
        monitor.record_error("chembl")
        monitor.record_error("chembl")
        monitor.record_error("chembl")

        status = monitor.record_health_check_result("chembl", HealthStatus.HEALTHY)

        assert status == HealthStatus.DEGRADED  # Recovery path
        assert monitor.get_state("chembl").consecutive_errors == 0

    def test_healthy_health_check_recovers_from_degraded(
        self, monitor: ProviderHealthMonitor
    ) -> None:
        """Test that HEALTHY health check recovers from DEGRADED to HEALTHY."""
        # Get to DEGRADED
        monitor.record_error("chembl")

        status = monitor.record_health_check_result("chembl", HealthStatus.HEALTHY)

        assert status == HealthStatus.HEALTHY
        assert monitor.get_state("chembl").consecutive_errors == 0

    def test_degraded_health_check_maintains_state(
        self, monitor: ProviderHealthMonitor
    ) -> None:
        """Test that DEGRADED health check maintains current state."""
        # Get to DEGRADED
        monitor.record_error("chembl")

        status = monitor.record_health_check_result("chembl", HealthStatus.DEGRADED)

        assert status == HealthStatus.DEGRADED


class TestProviderHealthMonitorMetrics:
    """Tests for metric emission."""

    DEGRADED_METRIC = 1
    HEALTHY_METRIC = 2
    UNHEALTHY_METRIC = 0

    def test_emits_metric_on_error(
        self, monitor: ProviderHealthMonitor, mock_metrics: MagicMock
    ) -> None:
        """Test that error emits provider_health_status metric."""
        monitor.record_error("chembl")

        mock_metrics.set_gauge.assert_called_with(
            "bioetl_provider_health_status",
            self.DEGRADED_METRIC,
            labels={"provider": "chembl"},
        )

    def test_emits_metric_on_success(
        self, monitor: ProviderHealthMonitor, mock_metrics: MagicMock
    ) -> None:
        """Test that success emits provider_health_status metric."""
        monitor.record_success("chembl")

        mock_metrics.set_gauge.assert_called_with(
            "bioetl_provider_health_status",
            self.HEALTHY_METRIC,
            labels={"provider": "chembl"},
        )

    def test_emits_metric_on_health_check(
        self, monitor: ProviderHealthMonitor, mock_metrics: MagicMock
    ) -> None:
        """Test that health check result emits metric."""
        monitor.record_health_check_result("chembl", HealthStatus.UNHEALTHY)

        mock_metrics.set_gauge.assert_called_with(
            "bioetl_provider_health_status",
            self.UNHEALTHY_METRIC,
            labels={"provider": "chembl"},
        )

    def test_metric_values_match_rules_md(
        self, monitor: ProviderHealthMonitor, mock_metrics: MagicMock
    ) -> None:
        """Test metric values match RULES.md §3.5 spec.

        0=Unhealthy, 1=Degraded, 2=Healthy
        """
        # Test each status value
        assert HealthStatus.UNHEALTHY.to_metric_value() == 0
        assert HealthStatus.DEGRADED.to_metric_value() == 1
        assert HealthStatus.HEALTHY.to_metric_value() == 2


class TestHealthCheckObservabilityCounters:
    """Tests for status-aware health-check outcome counters."""

    def test_emit_health_check_observability_counts_degraded_separately(
        self, mock_metrics: MagicMock
    ) -> None:
        """DEGRADED probe outcomes must not be folded into success counters."""
        emit_health_check_observability(
            metrics=mock_metrics,
            result=HealthCheckResult(
                status=HealthStatus.DEGRADED,
                latency_ms=12.5,
                provider="chembl",
                endpoint="/health",
            ),
        )

        degraded_call = next(
            (
                c
                for c in mock_metrics.increment_counter.call_args_list
                if c[0][0] == "bioetl_health_check_degraded_total"
            ),
            None,
        )
        success_call = next(
            (
                c
                for c in mock_metrics.increment_counter.call_args_list
                if c[0][0] == "bioetl_health_check_success_total"
            ),
            None,
        )

        assert degraded_call is not None
        assert success_call is None

    def test_emit_health_check_observability_counts_unhealthy_as_failure(
        self, mock_metrics: MagicMock
    ) -> None:
        """UNHEALTHY probe outcomes must increment the failure counter."""
        emit_health_check_observability(
            metrics=mock_metrics,
            result=HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                latency_ms=7.0,
                provider="chembl",
                endpoint="/health",
            ),
        )

        failure_call = next(
            (
                c
                for c in mock_metrics.increment_counter.call_args_list
                if c[0][0] == "bioetl_health_check_failures_total"
            ),
            None,
        )

        assert failure_call is not None

    def test_emit_health_check_observability_uses_seconds_histogram(
        self, mock_metrics: MagicMock
    ) -> None:
        """Health-check latency must use the canonical seconds metric family."""
        emit_health_check_observability(
            metrics=mock_metrics,
            result=HealthCheckResult(
                status=HealthStatus.HEALTHY,
                latency_ms=45.5,
                provider="chembl",
                endpoint="/health",
            ),
        )

        mock_metrics.observe_histogram.assert_called_with(
            "bioetl_health_check_latency_seconds",
            0.0455,
            labels={"provider": "chembl"},
        )
        observed_metric_names = [
            call.args[0] for call in mock_metrics.observe_histogram.call_args_list
        ]
        assert "bioetl_health_check_latency_ms" not in observed_metric_names


class TestProviderHealthMonitorAdaptiveParams:
    """Tests for adaptive timeout/batch_size parameters."""

    def test_healthy_returns_normal_params(
        self, monitor: ProviderHealthMonitor
    ) -> None:
        """Test HEALTHY state returns normal parameters."""
        timeout_mult, batch_div = monitor.get_adaptive_params("chembl")

        assert timeout_mult == pytest.approx(1.0)
        assert batch_div == 1

    def test_degraded_returns_doubled_timeout_halved_batch(
        self, monitor: ProviderHealthMonitor
    ) -> None:
        """Test DEGRADED state: Timeout ×2, batch_size ÷2."""
        monitor.record_error("chembl")  # -> DEGRADED

        timeout_mult, batch_div = monitor.get_adaptive_params("chembl")

        assert timeout_mult == pytest.approx(2.0)
        assert batch_div == 2

    def test_unhealthy_returns_aggressive_throttling(
        self, monitor: ProviderHealthMonitor
    ) -> None:
        """Test UNHEALTHY state returns aggressive throttling params."""
        monitor.record_error("chembl")
        monitor.record_error("chembl")
        monitor.record_error("chembl")  # -> UNHEALTHY

        timeout_mult, batch_div = monitor.get_adaptive_params("chembl")

        assert timeout_mult == pytest.approx(4.0)
        assert batch_div == 4


class TestProviderHealthMonitorGetAllStates:
    """Tests for get_all_states() method."""

    def test_get_all_states_empty(self, monitor: ProviderHealthMonitor) -> None:
        """Test get_all_states returns empty dict initially."""
        states = monitor.get_all_states()
        assert states == {}

    def test_get_all_states_multiple_providers(
        self, monitor: ProviderHealthMonitor
    ) -> None:
        """Test get_all_states returns all tracked providers."""
        monitor.record_error("chembl")
        monitor.record_success("uniprot")
        monitor.get_state("pubchem")  # Just get state, don't record

        states = monitor.get_all_states()

        assert "chembl" in states
        assert "uniprot" in states
        assert "pubchem" in states
        assert len(states) == 3


class TestHealthAdjustedConfig:
    """Tests for HealthAdjustedConfig dataclass."""

    def test_apply_timeout_multiplies(self) -> None:
        """Test apply_timeout multiplies base timeout."""
        from bioetl.infrastructure.adapters.http.health_monitor import (
            HealthAdjustedConfig,
        )

        config = HealthAdjustedConfig(
            timeout_multiplier=2.0,
            batch_size_divisor=2,
            status=HealthStatus.DEGRADED,
        )

        assert config.apply_timeout(30.0) == pytest.approx(60.0)

    def test_apply_batch_size_divides(self) -> None:
        """Test apply_batch_size divides base batch size."""
        from bioetl.infrastructure.adapters.http.health_monitor import (
            HealthAdjustedConfig,
        )

        config = HealthAdjustedConfig(
            timeout_multiplier=2.0,
            batch_size_divisor=2,
            status=HealthStatus.DEGRADED,
        )

        assert config.apply_batch_size(1000) == 500

    def test_apply_batch_size_respects_minimum(self) -> None:
        """Test apply_batch_size respects minimum value."""
        from bioetl.infrastructure.adapters.http.health_monitor import (
            HealthAdjustedConfig,
        )

        config = HealthAdjustedConfig(
            timeout_multiplier=4.0,
            batch_size_divisor=4,
            status=HealthStatus.UNHEALTHY,
        )

        # 50 / 4 = 12, but minimum is 100
        assert config.apply_batch_size(50, minimum=100) == 100


class TestProviderHealthTracker:
    """Tests for ProviderHealthTracker wrapper class."""

    @pytest.fixture
    def mock_logger(self) -> MagicMock:
        """Create mock logger."""
        return MagicMock()

    @pytest.fixture
    def tracker(
        self, monitor: ProviderHealthMonitor, mock_logger: MagicMock
    ) -> ProviderHealthTracker:
        """Create ProviderHealthTracker."""
        from bioetl.infrastructure.adapters.http.health_monitor import (
            ProviderHealthTracker,
        )

        return ProviderHealthTracker(
            provider="chembl",
            monitor=monitor,
            logger=mock_logger,
        )

    def test_status_property(
        self, tracker: ProviderHealthTracker, monitor: ProviderHealthMonitor
    ) -> None:
        """Test status property returns current health status."""
        assert tracker.status == HealthStatus.HEALTHY

        monitor.record_error("chembl")
        assert tracker.status == HealthStatus.DEGRADED

    def test_consecutive_failures_property(
        self, tracker: ProviderHealthTracker, monitor: ProviderHealthMonitor
    ) -> None:
        """Test consecutive_failures property returns error count."""
        assert tracker.consecutive_failures == 0

        monitor.record_error("chembl")
        assert tracker.consecutive_failures == 1

        monitor.record_error("chembl")
        assert tracker.consecutive_failures == 2

    def test_is_healthy_method(self, tracker: ProviderHealthTracker) -> None:
        """Test is_healthy returns True when HEALTHY."""
        assert tracker.is_healthy() is True

    def test_is_unhealthy_method(
        self, tracker: ProviderHealthTracker, monitor: ProviderHealthMonitor
    ) -> None:
        """Test is_unhealthy returns True when UNHEALTHY."""
        assert tracker.is_unhealthy() is False

        # Trigger UNHEALTHY
        monitor.record_error("chembl")
        monitor.record_error("chembl")
        monitor.record_error("chembl")

        assert tracker.is_unhealthy() is True

    def test_should_pause_pipeline(
        self, tracker: ProviderHealthTracker, monitor: ProviderHealthMonitor
    ) -> None:
        """Test should_pause_pipeline returns True when UNHEALTHY."""
        assert tracker.should_pause_pipeline() is False

        # Trigger UNHEALTHY
        for _ in range(3):
            monitor.record_error("chembl")

        assert tracker.should_pause_pipeline() is True

    def test_record_success_delegates(
        self, tracker: ProviderHealthTracker, monitor: ProviderHealthMonitor
    ) -> None:
        """Test record_success delegates to monitor."""
        monitor.record_error("chembl")  # DEGRADED

        status = tracker.record_success()

        # Should recover from DEGRADED if clear window passed
        assert status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)

    def test_record_error_delegates(self, tracker: ProviderHealthTracker) -> None:
        """Test record_error delegates to monitor."""
        status = tracker.record_error()

        assert status == HealthStatus.DEGRADED

    def test_get_adjusted_config(
        self, tracker: ProviderHealthTracker, monitor: ProviderHealthMonitor
    ) -> None:
        """Test get_adjusted_config returns proper config."""
        from bioetl.infrastructure.adapters.http.health_monitor import (
            HealthAdjustedConfig,
        )

        config = tracker.get_adjusted_config()

        assert isinstance(config, HealthAdjustedConfig)
        assert config.timeout_multiplier == pytest.approx(1.0)
        assert config.batch_size_divisor == 1
        assert config.status == HealthStatus.HEALTHY


class TestProviderHealthMonitorUpdateFromResult:
    """Tests for update_from_health_check_result method."""

    def test_updates_state_from_result(
        self, monitor: ProviderHealthMonitor, mock_metrics: MagicMock
    ) -> None:
        """Test update_from_health_check_result updates state."""
        from bioetl.domain.ports.health_check import HealthCheckResult

        result = HealthCheckResult(
            status=HealthStatus.UNHEALTHY,
            latency_ms=100.0,
            provider="chembl",
            endpoint="/status.json",
            last_error="Connection timeout",
            consecutive_failures=3,
        )

        status = monitor.update_from_health_check_result(result)

        assert status == HealthStatus.UNHEALTHY

    def test_emits_latency_metric(
        self, monitor: ProviderHealthMonitor, mock_metrics: MagicMock
    ) -> None:
        """Test update_from_health_check_result emits latency metric."""
        from bioetl.domain.ports.health_check import HealthCheckResult

        result = HealthCheckResult(
            status=HealthStatus.HEALTHY,
            latency_ms=45.5,
            provider="chembl",
            endpoint="/status.json",
        )

        monitor.update_from_health_check_result(result)

        # Should have called observe_histogram for latency
        mock_metrics.observe_histogram.assert_called_with(
            "bioetl_health_check_latency_seconds",
            0.0455,
            labels={"provider": "chembl"},
        )

    def test_logs_p2_alert_on_unhealthy(self, monitor: ProviderHealthMonitor) -> None:
        """Test P2 alert is logged when status becomes UNHEALTHY."""
        from bioetl.domain.ports.health_check import HealthCheckResult

        mock_logger = MagicMock()
        result = HealthCheckResult(
            status=HealthStatus.UNHEALTHY,
            latency_ms=100.0,
            provider="chembl",
            endpoint="/status.json",
            last_error="API unavailable",
            consecutive_failures=5,
        )

        monitor.update_from_health_check_result(result, logger=mock_logger)

        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert call_args[0][0] == "provider_unhealthy_alert"
        assert call_args[1]["alert_priority"] == "P2"
        assert call_args[1]["provider"] == "chembl"


class TestGetAdjustedConfig:
    """Tests for get_adjusted_config method."""

    def test_healthy_config(self, monitor: ProviderHealthMonitor) -> None:
        """Test get_adjusted_config returns normal config when HEALTHY."""
        from bioetl.infrastructure.adapters.http.health_monitor import (
            HealthAdjustedConfig,
        )

        config = monitor.get_adjusted_config("chembl")

        assert isinstance(config, HealthAdjustedConfig)
        assert config.timeout_multiplier == pytest.approx(1.0)
        assert config.batch_size_divisor == 1
        assert config.status == HealthStatus.HEALTHY

    def test_degraded_config(self, monitor: ProviderHealthMonitor) -> None:
        """Test get_adjusted_config returns degraded config."""
        monitor.record_error("chembl")

        config = monitor.get_adjusted_config("chembl")

        assert config.timeout_multiplier == pytest.approx(2.0)
        assert config.batch_size_divisor == 2
        assert config.status == HealthStatus.DEGRADED

    def test_unhealthy_config(self, monitor: ProviderHealthMonitor) -> None:
        """Test get_adjusted_config returns aggressive config when UNHEALTHY."""
        for _ in range(3):
            monitor.record_error("chembl")

        config = monitor.get_adjusted_config("chembl")

        assert config.timeout_multiplier == pytest.approx(4.0)
        assert config.batch_size_divisor == 4
        assert config.status == HealthStatus.UNHEALTHY
