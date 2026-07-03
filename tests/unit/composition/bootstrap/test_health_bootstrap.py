"""Unit tests for bootstrap health functions.

Tests bootstrap functions for HealthService and health server dependencies.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest

from bioetl.application.services.health_service import HealthService
from bioetl.composition.bootstrap.cli.health import (
    HealthServerDependencies,
    bootstrap_health_server_dependencies,
    bootstrap_health_server_quarantine_service,
    bootstrap_health_service,
)
from bioetl.domain.ports import (
    CheckpointPort,
    HealthMonitorPort,
    MetricsPort,
    RunLedgerPort,
    RunManifestPort,
)
from bioetl.domain.ports.health_check import HealthCheckResult, HealthStatePort
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.observability.prometheus_metrics import PrometheusMetrics
from bioetl.infrastructure.time import SystemClock
from tests.helpers.control_plane import InMemoryRunLedgerStore, InMemoryRunManifestStore


@dataclass(frozen=True, slots=True)
class _FakeHealthMonitor:
    metrics: MetricsPort

    def update_from_health_check_result(
        self,
        result: HealthCheckResult,
        logger: object | None = None,
    ) -> HealthStatus:
        return result.status

    def record_success(self, provider: str) -> HealthStatus:
        return HealthStatus.HEALTHY

    def record_error(self, provider: str) -> HealthStatus:
        return HealthStatus.DEGRADED

    def get_all_states(self) -> Mapping[str, HealthStatePort]:
        return {}


@pytest.mark.unit
class TestHealthServerDependencies:
    """Tests for HealthServerDependencies dataclass."""

    def test_health_server_dependencies_is_frozen(self):
        """Test that HealthServerDependencies is immutable."""
        metrics = PrometheusMetrics()
        monitor = _FakeHealthMonitor(metrics=metrics)
        checkpoint_port = MagicMock()
        manifest_store = InMemoryRunManifestStore()
        ledger_store = InMemoryRunLedgerStore()

        deps = HealthServerDependencies(
            health_monitor=monitor,
            metrics=metrics,
            checkpoint_port=checkpoint_port,
            run_manifest_port=manifest_store,
            run_ledger_port=ledger_store,
        )

        with pytest.raises(AttributeError):
            deps.metrics = PrometheusMetrics()  # type: ignore

    def test_health_server_dependencies_has_slots(self):
        """Test that HealthServerDependencies uses slots for efficiency."""
        assert hasattr(HealthServerDependencies, "__slots__")

    def test_health_server_dependencies_stores_components(self):
        """Test that HealthServerDependencies stores components correctly."""
        metrics = PrometheusMetrics()
        monitor = _FakeHealthMonitor(metrics=metrics)
        checkpoint_port = MagicMock()
        manifest_store = InMemoryRunManifestStore()
        ledger_store = InMemoryRunLedgerStore()

        deps = HealthServerDependencies(
            health_monitor=monitor,
            metrics=metrics,
            checkpoint_port=checkpoint_port,
            run_manifest_port=manifest_store,
            run_ledger_port=ledger_store,
        )

        assert deps.health_monitor is monitor
        assert deps.metrics is metrics
        assert deps.checkpoint_port is checkpoint_port
        assert deps.run_manifest_port is manifest_store
        assert deps.run_ledger_port is ledger_store


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

    def test_bootstrap_health_service_delegates_to_canonical_assembly(self):
        """CLI health bootstrap should delegate service construction to assembly."""
        expected_service = MagicMock(spec=HealthService)

        with patch(
            "bioetl.composition.bootstrap.cli.health.create_health_service",
            return_value=expected_service,
        ) as mock_create:
            result = bootstrap_health_service()

        assert result is expected_service
        mock_create.assert_called_once()


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
        """Test that bootstrap_health_server_dependencies creates a health monitor."""
        result = bootstrap_health_server_dependencies()

        assert isinstance(result.health_monitor, HealthMonitorPort)

    def test_bootstrap_wires_run_manifest_port(self):
        """Test that bootstrap_health_server_dependencies exposes a manifest catalog."""
        result = bootstrap_health_server_dependencies()

        assert isinstance(result.run_manifest_port, RunManifestPort)

    def test_bootstrap_wires_checkpoint_port(self):
        """Test that bootstrap_health_server_dependencies exposes checkpoint reads."""
        result = bootstrap_health_server_dependencies()

        assert isinstance(result.checkpoint_port, CheckpointPort)

    def test_bootstrap_wires_run_ledger_port(self):
        """Test that bootstrap_health_server_dependencies exposes a run ledger."""
        result = bootstrap_health_server_dependencies()

        assert isinstance(result.run_ledger_port, RunLedgerPort)

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
        assert result1.checkpoint_port is not result2.checkpoint_port
        assert result1.run_manifest_port is not result2.run_manifest_port
        assert result1.run_ledger_port is not result2.run_ledger_port

    def test_bootstrap_dependencies_delegate_to_canonical_assembly(self):
        """Health listener dependency wiring should delegate to assembly."""
        expected_dependencies = MagicMock(spec=HealthServerDependencies)

        with patch(
            "bioetl.composition.bootstrap.cli.health.create_health_server_dependencies",
            return_value=expected_dependencies,
        ) as mock_create:
            result = bootstrap_health_server_dependencies()

        assert result is expected_dependencies
        mock_create.assert_called_once()

    def test_quarantine_service_delegates_to_cli_service_builder(self):
        """Health-server quarantine wiring should reuse canonical CLI assembly."""
        expected_service = MagicMock()

        with patch(
            "bioetl.composition.bootstrap.cli.health.build_cli_quarantine_service",
            return_value=expected_service,
        ) as mock_build:
            result = bootstrap_health_server_quarantine_service()

        assert result is expected_service
        mock_build.assert_called_once()
        kwargs = mock_build.call_args.kwargs
        assert kwargs["run_manifest_service_factory"] is None
        assert kwargs["clock_factory"] is SystemClock
