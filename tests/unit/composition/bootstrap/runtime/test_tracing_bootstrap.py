"""Unit tests for tracing bootstrap helpers.

Tests bootstrap_tracer and its deprecated alias bootstrap_tracer,
verifying feature-flag gating and DI factory wiring.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bioetl.composition.bootstrap.runtime.tracing_bootstrap import (
    bootstrap_tracer,
)
from bioetl.domain.ports import TracingPort
from bioetl.domain.ports.noop import NoOpTracing


def _make_settings(*, tracing_enabled: bool = False) -> SimpleNamespace:
    """Create minimal Settings-like object for tracing bootstrap tests."""
    return SimpleNamespace(
        observability=SimpleNamespace(tracing_enabled=tracing_enabled)
    )


@pytest.mark.unit
class TestBootstrapTracerPort:
    """Tests for bootstrap_tracer."""

    def test_returns_noop_when_tracing_disabled(self) -> None:
        """Should return NoOpTracing when tracing_enabled is False."""
        settings = _make_settings(tracing_enabled=False)

        result = bootstrap_tracer(settings=settings)

        assert isinstance(result, NoOpTracing)

    def test_returns_tracer_from_factory_when_enabled(self) -> None:
        """Should use the factory to build a tracer when tracing_enabled is True."""
        mock_tracer = MagicMock(spec=TracingPort)
        factory = MagicMock(return_value=mock_tracer)
        settings = _make_settings(tracing_enabled=True)

        result = bootstrap_tracer(
            settings=settings,
            tracer_factory=factory,
        )

        assert result is mock_tracer
        factory.assert_called_once_with("bioetl")

    def test_passes_service_name_to_factory(self) -> None:
        """Factory should receive the service_name argument."""
        mock_tracer = MagicMock(spec=TracingPort)
        factory = MagicMock(return_value=mock_tracer)
        settings = _make_settings(tracing_enabled=True)

        bootstrap_tracer(
            settings=settings,
            service_name="my_service",
            tracer_factory=factory,
        )

        factory.assert_called_once_with("my_service")

    def test_default_service_name_is_bioetl(self) -> None:
        """Default service_name should be 'bioetl'."""
        captured_names: list[str] = []

        def capture_factory(name: str) -> TracingPort:
            captured_names.append(name)
            return MagicMock(spec=TracingPort)

        settings = _make_settings(tracing_enabled=True)

        bootstrap_tracer(settings=settings, tracer_factory=capture_factory)

        assert captured_names[0] == "bioetl"

    def test_noop_returned_when_disabled_regardless_of_factory(self) -> None:
        """Factory should not be called when tracing is disabled."""
        factory = MagicMock()
        settings = _make_settings(tracing_enabled=False)

        result = bootstrap_tracer(settings=settings, tracer_factory=factory)

        assert isinstance(result, NoOpTracing)
        factory.assert_not_called()

    def test_returns_tracing_port_interface(self) -> None:
        """Result should always implement TracingPort regardless of mode."""
        # Disabled mode
        settings_off = _make_settings(tracing_enabled=False)
        result_off = bootstrap_tracer(settings=settings_off)
        assert isinstance(result_off, TracingPort)

        # Enabled mode with fake factory
        mock_tracer = MagicMock(spec=TracingPort)
        factory = MagicMock(return_value=mock_tracer)
        settings_on = _make_settings(tracing_enabled=True)
        result_on = bootstrap_tracer(settings=settings_on, tracer_factory=factory)
        assert result_on is mock_tracer
