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
"""Explicit TracingPort contract suite."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.domain.ports import TracingPort
from bioetl.domain.ports.noop import NoOpTracing


@pytest.mark.unit
class TestTracingPortContract:
    """Bounded contract assertions for TracingPort implementations."""

    def test_noop_tracing_implements_tracing_port(self) -> None:
        assert isinstance(NoOpTracing(), TracingPort)

    def test_noop_tracing_span_path_is_safe(self) -> None:
        """NoOpTracing must expose an OTel-like span path without side effects."""
        tracing = NoOpTracing()
        tracer = tracing.get_tracer("bioetl.contracts")

        with tracer.start_as_current_span(
            "demo",
            attributes={"bioetl.run_id": "run-123"},
        ) as span:
            assert span is not None
            assert span.set_attribute("bioetl.status", "success") is None
            assert (
                span.add_event(
                    "bioetl.memory.decision",
                    attributes={"bioetl.memory.decision_index": 1},
                )
                is None
            )
            assert span.record_exception(RuntimeError("boom")) is None

        assert tracing.flush() is None
        assert tracing.close() is None
        assert tracing.close() is None

    def test_open_telemetry_tracer_wraps_span_context_manager(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """One canonical span path must forward into the underlying tracer."""
        from bioetl.infrastructure.observability import tracing as tracing_module

        if not tracing_module.otel_available:
            pytest.skip("OpenTelemetry is not available")

        from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
            InMemorySpanExporter,
        )

        entered_span = MagicMock()
        context_manager = MagicMock()
        context_manager.__enter__.return_value = entered_span
        context_manager.__exit__.return_value = None
        otel_tracer = MagicMock()
        otel_tracer.start_as_current_span.return_value = context_manager

        monkeypatch.setattr(
            tracing_module,
            "_build_telemetry_exporter",
            InMemorySpanExporter,
        )
        tracer_port = tracing_module.OpenTelemetryTracer("bioetl-contract-tests")
        monkeypatch.setattr(
            tracer_port._provider,
            "get_tracer",
            MagicMock(return_value=otel_tracer),
        )
        try:
            assert isinstance(tracer_port, TracingPort)

            span_handle = tracer_port.get_tracer(
                "bioetl.contracts"
            ).start_as_current_span(
                "pipeline.run",
                attributes={"bioetl.run_id": "run-123"},
            )

            with span_handle as span:
                span.set_attribute("bioetl.status", "success")
                span.add_event(
                    "bioetl.memory.decision",
                    attributes={"bioetl.memory.decision_index": 1},
                )
                span.record_exception(RuntimeError("boom"))

            otel_tracer.start_as_current_span.assert_called_once_with(
                "pipeline.run",
                attributes={"bioetl.run_id": "run-123"},
            )
            entered_span.set_attribute.assert_called_once_with(
                "bioetl.status",
                "success",
            )
            entered_span.add_event.assert_called_once_with(
                "bioetl.memory.decision",
                attributes={"bioetl.memory.decision_index": 1},
            )
            entered_span.record_exception.assert_called_once()
        finally:
            tracer_port.close()
