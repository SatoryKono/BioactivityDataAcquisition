from __future__ import annotations

from unittest import mock

from bioetl.composition.observability_resolution import (
    resolve_metrics_port,
    resolve_tracing_port,
)
from bioetl.domain.ports.noop import NoOpMetrics, NoOpTracing


def test_resolve_metrics_port_uses_injected_port() -> None:
    expected = mock.Mock()
    result = resolve_metrics_port(metrics=expected)
    assert result is expected


def test_resolve_metrics_port_bootstraps_from_settings() -> None:
    settings = mock.Mock()
    expected = mock.Mock()

    with mock.patch(
        "bioetl.composition.bootstrap.runtime.metrics_bootstrap.bootstrap_metrics",
        return_value=expected,
    ) as mock_bootstrap:
        result = resolve_metrics_port(metrics=None, settings=settings)

    assert result is expected
    mock_bootstrap.assert_called_once_with(settings)


def test_resolve_metrics_port_falls_back_to_noop() -> None:
    result = resolve_metrics_port(metrics=None, settings=None)
    assert isinstance(result, NoOpMetrics)


def test_resolve_tracing_port_uses_injected_port() -> None:
    expected = mock.Mock()
    result = resolve_tracing_port(tracer=expected)
    assert result is expected


def test_resolve_tracing_port_bootstraps_from_settings() -> None:
    settings = mock.Mock()
    expected = mock.Mock()
    service_name = "test-service"

    with mock.patch(
        "bioetl.composition.bootstrap.runtime.observability.bootstrap_tracer",
        return_value=expected,
    ) as mock_bootstrap:
        result = resolve_tracing_port(
            tracer=None,
            settings=settings,
            service_name=service_name,
        )

    assert result is expected
    mock_bootstrap.assert_called_once_with(settings, service_name=service_name)


def test_resolve_tracing_port_falls_back_to_noop() -> None:
    result = resolve_tracing_port(tracer=None, settings=None)
    assert isinstance(result, NoOpTracing)
