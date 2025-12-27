"""Tests for ProviderHealthMonitor (RULES.md §3.5).

Verifies health state transitions and metric emission.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.http.health_monitor import (
    ProviderHealthMonitor,
    ProviderHealthState,
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
        assert ProviderHealthState.CLEAR_WINDOW_SECONDS == 300.0


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

    def test_degraded_after_two_errors(
        self, monitor: ProviderHealthMonitor
    ) -> None:
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
        assert state.status == HealthStatus.DEGRADED  # Still degraded (window not passed)

        # Simulate 5 minutes passing by setting last_success in the past
        # This simulates that the previous success happened 5+ minutes ago
        state.last_success = time.monotonic() - 301  # 5 min + 1 sec ago

        # Next success should check the window BEFORE updating last_success
        # Since last_success is 5+ min in the past, _check_clear_window returns True
        status = monitor.record_success("chembl")

        # Now should be HEALTHY since 5 min window passed
        assert status == HealthStatus.HEALTHY

    def test_success_resets_error_count(
        self, monitor: ProviderHealthMonitor
    ) -> None:
        """Test that success resets consecutive error count."""
        monitor.record_error("chembl")
        monitor.record_error("chembl")
        assert monitor.get_state("chembl").consecutive_errors == 2

        monitor.record_success("chembl")
        assert monitor.get_state("chembl").consecutive_errors == 0

    def test_independent_provider_states(
        self, monitor: ProviderHealthMonitor
    ) -> None:
        """Test that each provider has independent state."""
        monitor.record_error("chembl")
        monitor.record_error("chembl")
        monitor.record_error("chembl")  # chembl -> UNHEALTHY

        monitor.record_error("uniprot")  # uniprot -> DEGRADED

        assert monitor.get_state("chembl").status == HealthStatus.UNHEALTHY
        assert monitor.get_state("uniprot").status == HealthStatus.DEGRADED
        assert monitor.get_state("pubchem").status == HealthStatus.HEALTHY  # Never errored


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

    def test_emits_metric_on_error(
        self, monitor: ProviderHealthMonitor, mock_metrics: MagicMock
    ) -> None:
        """Test that error emits provider_health_status metric."""
        monitor.record_error("chembl")

        mock_metrics.gauge.assert_called_with(
            "provider_health_status",
            1,  # DEGRADED = 1
            labels={"provider": "chembl"},
        )

    def test_emits_metric_on_success(
        self, monitor: ProviderHealthMonitor, mock_metrics: MagicMock
    ) -> None:
        """Test that success emits provider_health_status metric."""
        monitor.record_success("chembl")

        mock_metrics.gauge.assert_called_with(
            "provider_health_status",
            2,  # HEALTHY = 2
            labels={"provider": "chembl"},
        )

    def test_emits_metric_on_health_check(
        self, monitor: ProviderHealthMonitor, mock_metrics: MagicMock
    ) -> None:
        """Test that health check result emits metric."""
        monitor.record_health_check_result("chembl", HealthStatus.UNHEALTHY)

        mock_metrics.gauge.assert_called_with(
            "provider_health_status",
            0,  # UNHEALTHY = 0
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


class TestProviderHealthMonitorAdaptiveParams:
    """Tests for adaptive timeout/batch_size parameters."""

    def test_healthy_returns_normal_params(
        self, monitor: ProviderHealthMonitor
    ) -> None:
        """Test HEALTHY state returns normal parameters."""
        timeout_mult, batch_div = monitor.get_adaptive_params("chembl")

        assert timeout_mult == 1.0
        assert batch_div == 1

    def test_degraded_returns_doubled_timeout_halved_batch(
        self, monitor: ProviderHealthMonitor
    ) -> None:
        """Test DEGRADED state: Timeout ×2, batch_size ÷2."""
        monitor.record_error("chembl")  # -> DEGRADED

        timeout_mult, batch_div = monitor.get_adaptive_params("chembl")

        assert timeout_mult == 2.0
        assert batch_div == 2

    def test_unhealthy_returns_aggressive_throttling(
        self, monitor: ProviderHealthMonitor
    ) -> None:
        """Test UNHEALTHY state returns aggressive throttling params."""
        monitor.record_error("chembl")
        monitor.record_error("chembl")
        monitor.record_error("chembl")  # -> UNHEALTHY

        timeout_mult, batch_div = monitor.get_adaptive_params("chembl")

        assert timeout_mult == 4.0
        assert batch_div == 4


class TestProviderHealthMonitorGetAllStates:
    """Tests for get_all_states() method."""

    def test_get_all_states_empty(
        self, monitor: ProviderHealthMonitor
    ) -> None:
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
