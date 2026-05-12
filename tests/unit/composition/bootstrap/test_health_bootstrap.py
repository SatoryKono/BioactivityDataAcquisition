"""Unit tests for bootstrap health functions.

Tests bootstrap functions for HealthService and health server dependencies.
"""

from __future__ import annotations

import pytest

from bioetl.application.services.health_service import HealthService
from bioetl.composition.bootstrap.cli.health import (
    HealthServerDependencies,
    bootstrap_health_server_dependencies,
    bootstrap_health_service,
)
from bioetl.domain.ports import MetricsPort
from bioetl.infrastructure.adapters.http.health_monitor import ProviderHealthMonitor
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.observability.prometheus_metrics import PrometheusMetrics
from bioetl.infrastructure.time import SystemClock


@pytest.mark.unit
class TestHealthServerDependencies:
    """Tests for HealthServerDependencies dataclass."""

    def test_health_server_dependencies_is_frozen(self):
        """Test that HealthServerDependencies is immutable."""
        metrics = PrometheusMetrics()
        monitor = ProviderHealthMonitor(metrics=metrics)

        deps = HealthServerDependencies(
            health_monitor=monitor,
            metrics=metrics,
        )

        with pytest.raises(AttributeError):
            deps.metrics = PrometheusMetrics()  # type: ignore

    def test_health_server_dependencies_has_slots(self):
        """Test that HealthServerDependencies uses slots for efficiency."""
        assert hasattr(HealthServerDependencies, "__slots__")

    def test_health_server_dependencies_stores_components(self):
        """Test that HealthServerDependencies stores components correctly."""
        metrics = PrometheusMetrics()
        monitor = ProviderHealthMonitor(metrics=metrics)

        deps = HealthServerDependencies(
            health_monitor=monitor,
            metrics=metrics,
        )

        assert deps.health_monitor is monitor
        assert deps.metrics is metrics


@pytest.mark.unit
class TestBootstrapHealthService:
    """Tests for bootstrap_health_service function."""

    def test_bootstrap_health_service_returns_health_service(self):
        """Test that bootstrap_health_service returns HealthService."""
        result = bootstrap_health_service()

        assert isinstance(result, HealthService)

    def test_bootstrap_health_service_wires_noop_logger(self):
        """Test that bootstrap_health_service wires NoOpLogger."""
        result = bootstrap_health_service()

        # HealthService uses logger attribute (dataclass)
        assert isinstance(result.logger, NoOpLogger)

    def test_bootstrap_health_service_wires_composition_aware_factory(self):
        """Test that bootstrap_health_service wires provider-aware factory wrapper."""
        result = bootstrap_health_service()

        factory = result._factory
        assert hasattr(factory, "create")
        assert hasattr(factory, "list_providers")
        assert callable(factory.create)
        assert callable(factory.list_providers)

    def test_bootstrap_health_service_wires_system_clock(self):
        """Test that bootstrap_health_service wires SystemClock."""
        result = bootstrap_health_service()

        assert isinstance(result.clock, SystemClock)


@pytest.mark.unit
class TestBootstrapHealthServerDependencies:
    """Tests for bootstrap_health_server_dependencies function."""

    def test_bootstrap_returns_health_server_dependencies(self):
        """Test that bootstrap_health_server_dependencies returns HealthServerDependencies."""
        result = bootstrap_health_server_dependencies()

        assert isinstance(result, HealthServerDependencies)

    def test_bootstrap_creates_prometheus_metrics(self):
        """Test that bootstrap_health_server_dependencies creates PrometheusMetrics."""
        result = bootstrap_health_server_dependencies()

        assert isinstance(result.metrics, MetricsPort)
        assert isinstance(result.metrics, PrometheusMetrics)

    def test_bootstrap_creates_provider_health_monitor(self):
        """Test that bootstrap_health_server_dependencies creates ProviderHealthMonitor."""
        result = bootstrap_health_server_dependencies()

        assert isinstance(result.health_monitor, ProviderHealthMonitor)

    def test_bootstrap_wires_metrics_to_health_monitor(self):
        """Test that the metrics are wired to the health monitor."""
        result = bootstrap_health_server_dependencies()

        # ProviderHealthMonitor uses metrics attribute (dataclass)
        assert result.health_monitor.metrics is result.metrics

    def test_bootstrap_creates_new_instances_each_call(self):
        """Test that each call creates new instances."""
        result1 = bootstrap_health_server_dependencies()
        result2 = bootstrap_health_server_dependencies()

        assert result1 is not result2
        assert result1.metrics is not result2.metrics
        assert result1.health_monitor is not result2.health_monitor
