"""Unit tests for CLI metrics bootstrap.

Tests bootstrap_metrics_service wires MetricsService with
correct infrastructure adapters.
"""

from __future__ import annotations

import pytest

from bioetl.application.services.metrics_service import MetricsService
from bioetl.composition.bootstrap.cli.metrics import bootstrap_metrics_service
from bioetl.domain.ports import TracingPort
from bioetl.infrastructure.observability.metrics_server_adapter import (
    MetricsServerAdapter,
)
from bioetl.infrastructure.observability.noop_logger import NoOpLogger


@pytest.mark.unit
class TestBootstrapMetricsService:
    """Tests for bootstrap_metrics_service function."""

    def test_returns_metrics_service(self) -> None:
        """bootstrap_metrics_service should return a MetricsService instance."""
        result = bootstrap_metrics_service()

        assert isinstance(result, MetricsService)

    def test_metrics_service__wires_noop_logger__e6658389(self) -> None:
        """bootstrap_metrics_service should wire a NoOpLogger."""
        result = bootstrap_metrics_service()

        assert isinstance(result.logger, NoOpLogger)

    def test_wires_metrics_server_adapter(self) -> None:
        """bootstrap_metrics_service should wire a MetricsServerAdapter."""
        result = bootstrap_metrics_service()

        assert isinstance(result._server, MetricsServerAdapter)

    def test_server_adapter_receives_noop_logger(self) -> None:
        """The MetricsServerAdapter should receive a NoOpLogger (stored as _logger)."""
        result = bootstrap_metrics_service()

        assert isinstance(result._server._logger, NoOpLogger)

    def test_metrics_service__creates_new_instance__c1911644(self) -> None:
        """Each call should create a distinct MetricsService instance."""
        result1 = bootstrap_metrics_service()
        result2 = bootstrap_metrics_service()

        assert result1 is not result2

    def test_server_instances_are_independent(self) -> None:
        """Each call should wire fresh adapter instances (no shared state)."""
        result1 = bootstrap_metrics_service()
        result2 = bootstrap_metrics_service()

        assert result1._server is not result2._server

    def test_metrics_service__wires_tracing_port__5a712c50(self) -> None:
        """bootstrap_metrics_service should wire an explicit tracing port."""
        result = bootstrap_metrics_service()

        assert isinstance(result.tracer, TracingPort)
