"""Unit tests for metrics bootstrap helpers.

Tests bootstrap_metrics_port, maybe_start_metrics_server,
and their deprecated aliases.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bioetl.composition.bootstrap.runtime.metrics_bootstrap import (
    bootstrap_metrics_port,
    maybe_start_metrics_server,
)
from bioetl.domain.ports import MetricsPort, NoOpMetrics


def _make_settings(
    *,
    metrics_enabled: bool = True,
    metrics_server_enabled: bool = True,
    metrics_fail_fast: bool = False,
    metrics_retry_count: int = 3,
    metrics_retry_delay: float = 1.0,
    metrics_port: int = 8000,
    metrics_addr: str = "0.0.0.0",
) -> SimpleNamespace:
    """Create a minimal Settings-like object for metrics bootstrap tests."""
    return SimpleNamespace(
        metrics_port=metrics_port,
        metrics_addr=metrics_addr,
        observability=SimpleNamespace(
            metrics_enabled=metrics_enabled,
            metrics_server_enabled=metrics_server_enabled,
            metrics_fail_fast=metrics_fail_fast,
            metrics_retry_count=metrics_retry_count,
            metrics_retry_delay=metrics_retry_delay,
        ),
    )


@pytest.mark.unit
class TestBootstrapMetricsPort:
    """Tests for bootstrap_metrics_port."""

    def test_returns_noop_when_disabled(self) -> None:
        """Should return NoOpMetrics when metrics_enabled is False."""
        settings = _make_settings(metrics_enabled=False)

        result = bootstrap_metrics_port(settings=settings)

        assert isinstance(result, NoOpMetrics)

    def test_returns_metrics_port_when_enabled(self) -> None:
        """Should return MetricsPort from factory when metrics_enabled is True."""
        mock_metrics = MagicMock(spec=MetricsPort)
        factory = MagicMock(return_value=mock_metrics)
        settings = _make_settings(metrics_enabled=True)

        result = bootstrap_metrics_port(settings=settings, metrics_factory=factory)

        assert result is mock_metrics
        factory.assert_called_once()

    def test_uses_default_factory_when_none(self) -> None:
        """Should use PrometheusMetrics as default when metrics_factory is None."""
        settings = _make_settings(metrics_enabled=True)

        # Should not raise and return a MetricsPort
        result = bootstrap_metrics_port(settings=settings, metrics_factory=None)

        assert isinstance(result, MetricsPort)

    def test_noop_metrics_is_correct_type(self) -> None:
        """Disabled-metrics result should be a NoOpMetrics instance."""
        settings = _make_settings(metrics_enabled=False)

        result = bootstrap_metrics_port(settings=settings)

        assert isinstance(result, NoOpMetrics)

    def test_di_factory_called_with_no_args(self) -> None:
        """Factory should be called with no arguments."""
        mock_metrics = MagicMock(spec=MetricsPort)
        factory = MagicMock(return_value=mock_metrics)
        settings = _make_settings(metrics_enabled=True)

        bootstrap_metrics_port(settings=settings, metrics_factory=factory)

        factory.assert_called_once_with()


@pytest.mark.unit
class TestMaybeStartMetricsServer:
    """Tests for maybe_start_metrics_server."""

    def test_returns_false_when_metrics_disabled(self) -> None:
        """Should return False immediately when metrics_enabled is False."""
        settings = _make_settings(metrics_enabled=False)
        mock_starter = MagicMock()

        result = maybe_start_metrics_server(
            settings=settings, start_server=mock_starter
        )

        assert result is False
        mock_starter.assert_not_called()

    def test_returns_false_when_server_disabled(self) -> None:
        """Should return False when metrics_enabled but metrics_server_enabled is False."""
        settings = _make_settings(metrics_enabled=True, metrics_server_enabled=False)
        mock_starter = MagicMock()

        result = maybe_start_metrics_server(
            settings=settings, start_server=mock_starter
        )

        assert result is False
        mock_starter.assert_not_called()

    def test_returns_true_when_server_started(self) -> None:
        """Should return True when server starts successfully."""
        settings = _make_settings(metrics_enabled=True, metrics_server_enabled=True)
        mock_starter = MagicMock(return_value=True)

        result = maybe_start_metrics_server(
            settings=settings, start_server=mock_starter
        )

        assert result is True

    def test_passes_correct_args_to_starter(self) -> None:
        """Should pass port, addr, and observability flags to start_server."""
        settings = _make_settings(
            metrics_enabled=True,
            metrics_server_enabled=True,
            metrics_fail_fast=True,
            metrics_retry_count=5,
            metrics_retry_delay=2.5,
            metrics_port=9090,
            metrics_addr="127.0.0.1",
        )
        mock_starter = MagicMock(return_value=True)

        maybe_start_metrics_server(settings=settings, start_server=mock_starter)

        mock_starter.assert_called_once_with(
            port=9090,
            addr="127.0.0.1",
            fail_fast=True,
            retry_count=5,
            retry_delay=2.5,
        )

    def test_propagates_starter_exception(self) -> None:
        """Should propagate exceptions from start_server to caller."""
        settings = _make_settings(metrics_enabled=True, metrics_server_enabled=True)
        mock_starter = MagicMock(side_effect=RuntimeError("bind failed"))

        with pytest.raises(RuntimeError, match="bind failed"):
            maybe_start_metrics_server(settings=settings, start_server=mock_starter)


