from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.composition.observability_resolution import (
    resolve_metrics_port,
    resolve_tracing_port,
)
from bioetl.domain.ports import MetricsPort, TracingPort
from bioetl.domain.ports.noop import NoOpMetrics, NoOpTracing


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    return settings


def test_resolve_metrics_port_with_explicit_injection():
    """Should return explicitly provided metrics port."""
    mock_metrics = MagicMock(spec=MetricsPort)
    result = resolve_metrics_port(
        metrics=mock_metrics,
        settings=MagicMock(),
    )
    assert result is mock_metrics


def test_resolve_metrics_port_from_settings(mock_settings):
    """Should bootstrap metrics port from settings when not explicitly provided."""
    with pytest.MonkeyPatch().context() as mp:
        mock_bootstrapped = MagicMock(spec=MetricsPort)
        # The import and call happen inside resolve_metrics_port
        mp.setattr(
            "bioetl.composition.bootstrap.runtime.metrics_bootstrap.bootstrap_metrics",
            lambda *args, **kwargs: mock_bootstrapped,
        )

        result = resolve_metrics_port(
            metrics=None,
            settings=mock_settings,
        )
        assert result is mock_bootstrapped


def test_resolve_metrics_port_fallback_to_noop():
    """Should return NoOpMetrics when neither metrics nor settings are provided."""
    result = resolve_metrics_port(
        metrics=None,
        settings=None,
    )
    assert isinstance(result, NoOpMetrics)


def test_resolve_tracing_port_with_explicit_injection():
    """Should return explicitly provided tracing port."""
    mock_tracing = MagicMock(spec=TracingPort)
    result = resolve_tracing_port(
        tracer=mock_tracing,
        settings=MagicMock(),
    )
    assert result is mock_tracing


def test_resolve_tracing_port_from_settings(mock_settings):
    """Should bootstrap tracing port from settings when not explicitly provided."""
    with pytest.MonkeyPatch().context() as mp:
        mock_bootstrapped = MagicMock(spec=TracingPort)
        # The import and call happen inside resolve_tracing_port
        mp.setattr(
            "bioetl.composition.bootstrap.runtime.observability.bootstrap_tracer",
            lambda *args, **kwargs: mock_bootstrapped,
        )

        result = resolve_tracing_port(
            tracer=None,
            settings=mock_settings,
        )
        assert result is mock_bootstrapped


def test_resolve_tracing_port_fallback_to_noop():
    """Should return NoOpTracing when neither tracer nor settings are provided."""
    result = resolve_tracing_port(
        tracer=None,
        settings=None,
    )
    assert isinstance(result, NoOpTracing)
