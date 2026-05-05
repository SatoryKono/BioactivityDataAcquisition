"""Unit tests for metrics bootstrap helpers.

Tests bootstrap_metrics, maybe_start_metrics_server,
and their deprecated aliases.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bioetl.composition.bootstrap.runtime.metrics_bootstrap import (
    bootstrap_metrics,
    maybe_start_metrics_server,
    resolve_metrics_fail_fast,
)
from bioetl.domain.ports import MetricsPort
from bioetl.domain.ports.noop import NoOpMetrics


def _make_settings(
    *,
    metrics_enabled: bool = True,
    metrics_server_enabled: bool = True,
    metrics_fail_fast: bool = False,
    metrics_retry_count: int = 3,
    metrics_retry_delay: float = 1.0,
    metrics_port: int = 8000,
    metrics_addr: str = "0.0.0.0",
    env: str = "dev",
    test_mode: bool = False,
    explicit_observability_fields: set[str] | None = None,
) -> SimpleNamespace:
    """Create a minimal Settings-like object for metrics bootstrap tests."""
    return SimpleNamespace(
        env=env,
        test_mode=test_mode,
        metrics_port=metrics_port,
        metrics_addr=metrics_addr,
        observability=SimpleNamespace(
            metrics_enabled=metrics_enabled,
            metrics_server_enabled=metrics_server_enabled,
            metrics_fail_fast=metrics_fail_fast,
            metrics_retry_count=metrics_retry_count,
            metrics_retry_delay=metrics_retry_delay,
            model_fields_set=explicit_observability_fields or set(),
        ),
    )


@pytest.mark.unit
class TestBootstrapMetricsPort:
    """Tests for bootstrap_metrics."""

    def test_returns_noop_when_disabled(self) -> None:
        """Should return NoOpMetrics when metrics_enabled is False."""
        settings = _make_settings(metrics_enabled=False)

        result = bootstrap_metrics(settings=settings)

        assert isinstance(result, NoOpMetrics)

    def test_returns_metrics_port_when_enabled(self) -> None:
        """Should return MetricsPort from factory when metrics_enabled is True."""
        mock_metrics = MagicMock(spec=MetricsPort)
        factory = MagicMock(return_value=mock_metrics)
        settings = _make_settings(metrics_enabled=True)

        result = bootstrap_metrics(settings=settings, metrics_factory=factory)

        assert result is mock_metrics
        factory.assert_called_once()

    def test_uses_default_factory_when_none(self) -> None:
        """Should use PrometheusMetrics as default when metrics_factory is None."""
        settings = _make_settings(metrics_enabled=True)

        # Should not raise and return a MetricsPort
        result = bootstrap_metrics(settings=settings, metrics_factory=None)

        assert isinstance(result, MetricsPort)

    def test_noop_metrics_is_correct_type(self) -> None:
        """Disabled-metrics result should be a NoOpMetrics instance."""
        settings = _make_settings(metrics_enabled=False)

        result = bootstrap_metrics(settings=settings)

        assert isinstance(result, NoOpMetrics)

    def test_di_factory_called_with_no_args(self) -> None:
        """Factory should be called with no arguments."""
        mock_metrics = MagicMock(spec=MetricsPort)
        factory = MagicMock(return_value=mock_metrics)
        settings = _make_settings(metrics_enabled=True)

        bootstrap_metrics(settings=settings, metrics_factory=factory)

        factory.assert_called_once_with()


@pytest.mark.unit
class TestMaybeStartMetricsServer:
    """Tests for maybe_start_metrics_server."""

    def test_returns_false_when_metrics_disabled(self) -> None:
        """Should return False immediately when metrics_enabled is False."""
        settings = _make_settings(metrics_enabled=False)
        mock_service_factory = MagicMock()

        result = maybe_start_metrics_server(
            settings=settings, metrics_service_factory=mock_service_factory
        )

        assert result is False
        mock_service_factory.assert_not_called()

    def test_returns_false_when_server_disabled(self) -> None:
        """Should return False when metrics_enabled but metrics_server_enabled is False."""
        settings = _make_settings(metrics_enabled=True, metrics_server_enabled=False)
        mock_service_factory = MagicMock()

        result = maybe_start_metrics_server(
            settings=settings, metrics_service_factory=mock_service_factory
        )

        assert result is False
        mock_service_factory.assert_not_called()

    def test_returns_true_when_server_started(self) -> None:
        """Should return True when server starts successfully."""
        settings = _make_settings(metrics_enabled=True, metrics_server_enabled=True)
        mock_service = MagicMock()
        mock_service.start.return_value = SimpleNamespace(success=True)
        mock_service_factory = MagicMock(return_value=mock_service)

        result = maybe_start_metrics_server(
            settings=settings, metrics_service_factory=mock_service_factory
        )

        assert result is True

    def test_passes_correct_args_to_metrics_service(self) -> None:
        """Should pass port, addr, and observability flags to MetricsService.start."""
        settings = _make_settings(
            metrics_enabled=True,
            metrics_server_enabled=True,
            metrics_fail_fast=True,
            metrics_retry_count=5,
            metrics_retry_delay=2.5,
            metrics_port=9090,
            metrics_addr="127.0.0.1",
        )
        mock_service = MagicMock()
        mock_service.start.return_value = SimpleNamespace(success=True)
        mock_service_factory = MagicMock(return_value=mock_service)

        maybe_start_metrics_server(
            settings=settings,
            metrics_service_factory=mock_service_factory,
        )

        mock_service.start.assert_called_once_with(
            port=9090,
            addr="127.0.0.1",
            fail_fast=True,
            retry_count=5,
            retry_delay=2.5,
        )

    def test_defaults_fail_fast_for_production_launcher(self) -> None:
        """Production launchers default to fail-fast metrics startup."""
        settings = _make_settings(
            env="prod",
            metrics_fail_fast=False,
        )
        mock_service = MagicMock()
        mock_service.start.return_value = SimpleNamespace(success=True)
        mock_service_factory = MagicMock(return_value=mock_service)

        maybe_start_metrics_server(
            settings=settings,
            metrics_service_factory=mock_service_factory,
        )

        mock_service.start.assert_called_once_with(
            port=8000,
            addr="0.0.0.0",
            fail_fast=True,
            retry_count=3,
            retry_delay=1.0,
        )

    def test_allows_explicit_production_fail_fast_override(self) -> None:
        """Explicit operator config can still opt out of fail-fast startup."""
        settings = _make_settings(
            env="prod",
            metrics_fail_fast=False,
            explicit_observability_fields={"metrics_fail_fast"},
        )

        assert resolve_metrics_fail_fast(settings) is False

    def test_does_not_default_fail_fast_in_production_test_mode(self) -> None:
        """Test-mode production fixtures keep graceful metrics degradation."""
        settings = _make_settings(
            env="prod",
            test_mode=True,
            metrics_fail_fast=False,
        )

        assert resolve_metrics_fail_fast(settings) is False

    def test_propagates_metrics_service_exception(self) -> None:
        """Should propagate exceptions from MetricsService.start to caller."""
        settings = _make_settings(metrics_enabled=True, metrics_server_enabled=True)
        mock_service = MagicMock()
        mock_service.start.side_effect = RuntimeError("bind failed")
        mock_service_factory = MagicMock(return_value=mock_service)

        with pytest.raises(RuntimeError, match="bind failed"):
            maybe_start_metrics_server(
                settings=settings,
                metrics_service_factory=mock_service_factory,
            )
