# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for tracing bootstrap helpers.

Tests bootstrap_tracer and its deprecated alias bootstrap_tracer,
verifying feature-flag gating and DI factory wiring.
"""

from __future__ import annotations

import importlib
import sys
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

    def test_module_import_does_not_load_opentelemetry_adapter(self) -> None:
        """Disabled/default import path must not touch the heavy OTel adapter."""
        module_name = "bioetl.composition.bootstrap.runtime.tracing_bootstrap"
        adapter_name = "bioetl.infrastructure.observability.tracing"
        previous_module = sys.modules.pop(module_name, None)
        previous_adapter = sys.modules.pop(adapter_name, None)

        try:
            importlib.import_module(module_name)

            assert adapter_name not in sys.modules
        finally:
            sys.modules.pop(module_name, None)
            if previous_module is not None:
                sys.modules[module_name] = previous_module
            if previous_adapter is not None:
                sys.modules[adapter_name] = previous_adapter

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
