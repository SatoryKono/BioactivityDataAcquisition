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
"""Tests for infrastructure/observability/tracing.py.

These tests verify the OpenTelemetry tracing implementation.
"""

from __future__ import annotations

import builtins
import importlib.metadata
import importlib.util
import logging
from collections.abc import Generator
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

from bioetl.domain.ports.noop import NoOpTracing


pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _use_console_exporter_for_unit_tests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep unit tests independent of the optional native gRPC extension."""
    from bioetl.infrastructure.observability import tracing

    monkeypatch.setattr(tracing, "otlp_available", False)
    monkeypatch.setattr(tracing, "_OtlpExporterClass", None)


class TestNoOpTracingReExport:
    """Tests for NoOpTracing re-export from tracing module."""

    def test_noop_tracing_importable(self) -> None:
        """NoOpTracing is importable from tracing module."""
        from bioetl.infrastructure.observability.tracing import NoOpTracing

        assert NoOpTracing is not None

    def test_noop_tracing_is_same(self) -> None:
        """NoOpTracing from tracing is same as direct import."""
        from bioetl.domain.ports.noop import NoOpTracing as Direct
        from bioetl.infrastructure.observability.tracing import (
            NoOpTracing as ReExported,
        )

        assert Direct is ReExported


class TestModuleImports:
    """Tests for module-level imports."""

    def test_otel_available_defined(self) -> None:
        """otel_available flag is defined."""
        from bioetl.infrastructure.observability import tracing

        assert hasattr(tracing, "otel_available")
        assert isinstance(tracing.otel_available, bool)

    def test_opentelemetry_tracer_class_defined(self) -> None:
        """OpenTelemetryTracer class is defined."""
        from bioetl.infrastructure.observability import tracing

        assert hasattr(tracing, "OpenTelemetryTracer")


class TestOpenTelemetryTracerWithoutOTEL:
    """Tests for OpenTelemetryTracer when OpenTelemetry is not available."""

    def test_init_raises_without_otel(self) -> None:
        """OpenTelemetryTracer raises ImportError if OTEL not available."""
        from bioetl.infrastructure.observability import tracing

        if not tracing.otel_available:
            with pytest.raises(ImportError) as exc_info:
                tracing.OpenTelemetryTracer()
            assert "OpenTelemetry is not installed" in str(exc_info.value)
        else:
            # This test is only relevant when OTEL is NOT available.
            # If it IS available, we can't test the ImportError without complex mocking
            # that might interfere with other tests.
            pass


class TestOpenTelemetryTracerWithOTEL:
    """Tests for OpenTelemetryTracer when OpenTelemetry is available."""

    @pytest.fixture
    def mock_otel(self) -> Generator[dict[str, MagicMock], None, None]:
        """Mock OpenTelemetry modules."""
        mock_trace = MagicMock()
        mock_provider = MagicMock()
        mock_processor = MagicMock()
        mock_exporter = MagicMock()
        mock_tracer = MagicMock()

        mock_trace.get_tracer.return_value = mock_tracer
        mock_provider_class = MagicMock(return_value=mock_provider)
        mock_processor_class = MagicMock(return_value=mock_processor)

        with patch.dict(
            "sys.modules",
            {
                "opentelemetry": MagicMock(),
                "opentelemetry.trace": mock_trace,
                "opentelemetry.sdk": MagicMock(),
                "opentelemetry.sdk.trace": MagicMock(
                    TracerProvider=mock_provider_class
                ),
                "opentelemetry.sdk.trace.export": MagicMock(
                    BatchSpanProcessor=mock_processor_class,
                    ConsoleSpanExporter=mock_exporter,
                ),
            },
        ):
            yield {
                "trace": mock_trace,
                "provider": mock_provider,
                "tracer": mock_tracer,
            }

    def test_tracer_available(self) -> None:
        """Test when OTEL is available."""
        from bioetl.infrastructure.observability import tracing

        if tracing.otel_available:
            # Create tracer - it should work
            tracer = tracing.OpenTelemetryTracer("test_service")
            assert tracer is not None
            tracer.close()
        else:
            pytest.skip("OpenTelemetry is not available")

    def test_sets_service_name_resource_attribute(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Tracer provider should publish a stable service.name resource."""
        from bioetl.infrastructure.observability import tracing

        if tracing.otel_available:
            monkeypatch.delenv("OTEL_SERVICE_NAME", raising=False)
            tracer = tracing.OpenTelemetryTracer("bioetl")
            try:
                assert (
                    tracer._provider.resource.attributes.get("service.name") == "bioetl"
                )
            finally:
                tracer.close()
        else:
            pytest.skip("OpenTelemetry is not available")

    def test_prefers_otel_service_name_env(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Explicit OTEL_SERVICE_NAME should override the constructor default."""
        from bioetl.infrastructure.observability import tracing

        if tracing.otel_available:
            monkeypatch.setenv("OTEL_SERVICE_NAME", "bioetl-local")
            tracer = tracing.OpenTelemetryTracer("bioetl")
            try:
                assert (
                    tracer._provider.resource.attributes.get("service.name")
                    == "bioetl-local"
                )
            finally:
                tracer.close()
        else:
            pytest.skip("OpenTelemetry is not available")


class TestOpenTelemetryTracerClose:
    """Tests for OpenTelemetryTracer close behavior."""

    def test_close_is_idempotent__test_open_telemetry_tracer_close_infrastructure_observability_test_tracing_158(
        self,
    ) -> None:
        """close() can be called multiple times safely."""
        from bioetl.infrastructure.observability import tracing

        if tracing.otel_available:
            tracer = tracing.OpenTelemetryTracer("test")
            tracer.close()
            tracer.close()  # Should not raise
            tracer.close()  # Should not raise
        else:
            pytest.skip("OpenTelemetry is not available")


class TestTelemetryExporterSelection:
    """Tests for telemetry exporter configuration safety."""

    def test_extract_endpoint_host_handles_urls_ipv6_and_host_port(self) -> None:
        """Endpoint host extraction should normalize common OTLP endpoint forms."""
        from bioetl.infrastructure.observability import tracing

        assert tracing._extract_endpoint_host("http://localhost:4317") == "localhost"
        assert tracing._extract_endpoint_host("[::1]:4317") == "::1"
        assert tracing._extract_endpoint_host("tempo:4317") == "tempo"
        assert tracing._extract_endpoint_host("collector") == "collector"

    def test_otlp_endpoint_prefers_trace_specific_env(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Trace-specific OTLP endpoint must take precedence over generic endpoint."""
        from bioetl.infrastructure.observability import tracing

        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://generic:4317")
        monkeypatch.setenv(
            "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
            "http://traces:4317",
        )

        assert tracing._get_otlp_endpoint() == "http://traces:4317"

    def test_otlp_insecure_prefers_trace_specific_env(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Trace-specific insecure override must take precedence."""
        from bioetl.infrastructure.observability import tracing

        monkeypatch.setenv("OTEL_EXPORTER_OTLP_INSECURE", "false")
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_TRACES_INSECURE", "true")

        assert tracing._get_otlp_insecure_setting() == "true"

    def test_build_exporter_falls_back_to_console_when_otlp_unavailable(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Console exporter is used when OTLP exporter support is unavailable."""
        from bioetl.infrastructure.observability import tracing

        console_exporter = object()
        monkeypatch.setattr(tracing, "otlp_available", False)
        monkeypatch.setattr(tracing, "_OtlpExporterClass", None)
        monkeypatch.setattr(
            tracing, "ConsoleSpanExporter", MagicMock(return_value=console_exporter)
        )

        assert tracing._build_telemetry_exporter() is console_exporter

    def test_build_exporter_loads_otlp_class_lazily(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The native gRPC-backed exporter is imported only when it is used."""
        from bioetl.infrastructure.observability import tracing

        exporter = object()
        exporter_factory = MagicMock(return_value=exporter)
        exporter_module = ModuleType("lazy_otlp_exporter")
        exporter_module.OTLPSpanExporter = exporter_factory
        import_module = MagicMock(return_value=exporter_module)
        monkeypatch.setattr(tracing, "otlp_available", True)
        monkeypatch.setattr(tracing, "_OtlpExporterClass", None)
        monkeypatch.setattr(tracing, "import_module", import_module)
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", raising=False)
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_TRACES_INSECURE", raising=False)
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_INSECURE", raising=False)

        assert tracing._build_telemetry_exporter() is exporter
        import_module.assert_called_once_with(tracing._OTLP_EXPORTER_MODULE)
        exporter_factory.assert_called_once_with()
        assert tracing._OtlpExporterClass is exporter_factory

    def test_local_otlp_endpoint_defaults_to_insecure(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Local OTLP endpoints must set insecure=True unless explicitly overridden."""
        from bioetl.infrastructure.observability import tracing

        exporter_factory = MagicMock(return_value=object())
        monkeypatch.setattr(tracing, "otlp_available", True)
        monkeypatch.setattr(tracing, "_OtlpExporterClass", exporter_factory)
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", raising=False)
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_INSECURE", raising=False)
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_TRACES_INSECURE", raising=False)

        tracing._build_telemetry_exporter()

        exporter_factory.assert_called_once_with(
            endpoint="http://localhost:4317",
            insecure=True,
        )

    def test_explicit_insecure_override_wins_for_local_endpoint(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Explicit insecure override should not be replaced by local endpoint default."""
        from bioetl.infrastructure.observability import tracing

        exporter_factory = MagicMock(return_value=object())
        monkeypatch.setattr(tracing, "otlp_available", True)
        monkeypatch.setattr(tracing, "_OtlpExporterClass", exporter_factory)
        monkeypatch.setenv(
            "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", "http://localhost:4317"
        )
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_TRACES_INSECURE", "false")
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_INSECURE", raising=False)

        tracing._build_telemetry_exporter()

        exporter_factory.assert_called_once_with(
            endpoint="http://localhost:4317",
            insecure=False,
        )

    def test_parse_bool_env_rejects_falsey_values(self) -> None:
        """Only conventional truthy values should evaluate to True."""
        from bioetl.infrastructure.observability import tracing

        assert tracing._parse_bool_env("false") is False
        assert tracing._parse_bool_env("0") is False
        assert tracing._parse_bool_env("off") is False

    def test_get_otlp_endpoint_returns_none_when_env_is_unset(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """OTLP endpoint helper should return None without configured env vars."""
        from bioetl.infrastructure.observability import tracing

        monkeypatch.delenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", raising=False)
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)

        assert tracing._get_otlp_endpoint() is None

    def test_explicit_insecure_override_without_endpoint_is_honored(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Explicit insecure mode should be forwarded even without an endpoint."""
        from bioetl.infrastructure.observability import tracing

        exporter_factory = MagicMock(return_value=object())
        monkeypatch.setattr(tracing, "otlp_available", True)
        monkeypatch.setattr(tracing, "_OtlpExporterClass", exporter_factory)
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", raising=False)
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_TRACES_INSECURE", "true")

        tracing._build_telemetry_exporter()

        exporter_factory.assert_called_once_with(insecure=True)

    def test_remote_otlp_endpoint_does_not_default_to_insecure(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Remote OTLP endpoints should not receive the local insecure default."""
        from bioetl.infrastructure.observability import tracing

        exporter_factory = MagicMock(return_value=object())
        monkeypatch.setattr(tracing, "otlp_available", True)
        monkeypatch.setattr(tracing, "_OtlpExporterClass", exporter_factory)
        monkeypatch.setenv(
            "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
            "https://collector.example:4317",
        )
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_INSECURE", raising=False)
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_TRACES_INSECURE", raising=False)

        tracing._build_telemetry_exporter()

        exporter_factory.assert_called_once_with(
            endpoint="https://collector.example:4317",
        )


class TestOpenTelemetryTracerErrorPaths:
    """Tests for best-effort tracing cleanup/error swallowing paths."""

    def test_flush_swallows_provider_errors(self) -> None:
        """flush() must not raise when provider force-flush fails."""
        from bioetl.infrastructure.observability import tracing

        tracer = object.__new__(tracing.OpenTelemetryTracer)
        tracer._closed = False
        tracer._provider = MagicMock()
        tracer._provider.force_flush.side_effect = RuntimeError("boom")

        tracer.flush()

    def test_close_marks_tracer_closed_when_shutdown_fails(self) -> None:
        """close() should remain idempotent even if provider shutdown fails."""
        from bioetl.infrastructure.observability import tracing

        tracer = object.__new__(tracing.OpenTelemetryTracer)
        tracer._closed = False
        tracer._provider = MagicMock()
        tracer.flush = MagicMock()
        tracer._provider.shutdown.side_effect = OSError("boom")

        tracer.close()

        assert tracer._closed is True
        tracer.flush.assert_called_once_with()

    def test_insecure_override_without_endpoint_is_forwarded(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """An insecure override without endpoint is still passed to the OTLP exporter."""
        from bioetl.infrastructure.observability import tracing

        exporter_factory = MagicMock(return_value=object())
        monkeypatch.setattr(tracing, "otlp_available", True)
        monkeypatch.setattr(tracing, "_OtlpExporterClass", exporter_factory)
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", raising=False)
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_INSECURE", "yes")
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_TRACES_INSECURE", raising=False)

        tracing._build_telemetry_exporter()

        exporter_factory.assert_called_once_with(insecure=True)

    def test_flush_returns_without_provider_call_after_close(self) -> None:
        """flush() should be a no-op after the tracer has been closed."""
        from bioetl.infrastructure.observability import tracing

        tracer = object.__new__(tracing.OpenTelemetryTracer)
        tracer._closed = True
        tracer._provider = MagicMock()

        tracer.flush()

        tracer._provider.force_flush.assert_not_called()


class TestTracingProtocolAndSpanBranchPaths:
    """Focused branch tests for protocol and span-handle compatibility helpers."""

    def test_span_handle_methods_are_noops_before_enter(self) -> None:
        """Span helper methods should be safe before context entry."""
        from bioetl.infrastructure.observability import tracing

        context_manager = MagicMock()
        handle = tracing._SpanHandle(context_manager)

        handle.set_attribute("bioetl.status", "pending")
        handle.add_event(
            "bioetl.memory.decision",
            attributes={"bioetl.memory.decision_index": 1},
        )
        handle.record_exception(RuntimeError("not-entered"))

        context_manager.__enter__.assert_not_called()

    def test_tracer_adapter_defaults_attributes_to_empty_dict(self) -> None:
        """Adapter should pass an empty attributes mapping when none is supplied."""
        from bioetl.infrastructure.observability import tracing

        otel_tracer = MagicMock()

        tracing._TracerAdapter(otel_tracer).start_as_current_span("demo")

        otel_tracer.start_as_current_span.assert_called_once_with(
            "demo",
            attributes={},
        )

    def test_protocol_method_bodies_are_runtime_safe(self) -> None:
        """Protocol ellipsis bodies remain harmless when introspection calls them."""
        from bioetl.infrastructure.observability import tracing

        assert tracing._SpanProtocol.set_attribute(object(), "k", "v") is None
        assert (
            tracing._SpanProtocol.add_event(
                object(),
                "bioetl.memory.decision",
                {"bioetl.memory.decision_index": 1},
            )
            is None
        )
        assert (
            tracing._SpanProtocol.record_exception(
                object(),
                RuntimeError("boom"),
            )
            is None
        )
        assert tracing._SpanContextManagerProtocol.__enter__(object()) is None
        assert (
            tracing._SpanContextManagerProtocol.__exit__(
                object(),
                None,
                None,
                None,
            )
            is None
        )
        assert tracing._TracerProtocol.start_as_current_span(object(), "demo") is None


class TestTracingImportFallbackBranches:
    """Import the tracing module under mocked OTel availability states."""

    def _load_tracing_copy(
        self,
        monkeypatch: pytest.MonkeyPatch,
        *,
        blocked_prefixes: tuple[str, ...],
        otlp_distribution_available: bool | None = None,
    ) -> ModuleType:
        from bioetl.infrastructure.observability import tracing

        module_path = Path(tracing.__file__)
        module_suffix = "_".join(
            prefix.replace(".", "_") for prefix in blocked_prefixes
        )
        spec = importlib.util.spec_from_file_location(
            f"_bioetl_tracing_fallback_{module_suffix or 'available'}",
            module_path,
        )
        assert spec is not None
        assert spec.loader is not None

        real_import = builtins.__import__

        def guarded_import(
            name: str,
            globals_: dict[str, object] | None = None,
            locals_: dict[str, object] | None = None,
            fromlist: tuple[str, ...] = (),
            level: int = 0,
        ) -> object:
            if any(
                name == prefix or name.startswith(f"{prefix}.")
                for prefix in blocked_prefixes
            ):
                raise ImportError(name)
            return real_import(name, globals_, locals_, fromlist, level)

        monkeypatch.setattr(builtins, "__import__", guarded_import)
        if otlp_distribution_available is True:
            monkeypatch.setattr(
                importlib.metadata,
                "version",
                lambda distribution_name: "test",
            )
        elif otlp_distribution_available is False:

            def _missing_version(distribution_name: str) -> str:
                raise importlib.metadata.PackageNotFoundError(distribution_name)

            monkeypatch.setattr(importlib.metadata, "version", _missing_version)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_module_marks_otlp_unavailable_when_exporter_import_fails(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """OTEL stays enabled; first OTLP load failure disables the exporter."""
        module = self._load_tracing_copy(
            monkeypatch,
            blocked_prefixes=("opentelemetry.exporter.otlp",),
            otlp_distribution_available=True,
        )

        assert module.otel_available is True
        assert module.otlp_available is True
        assert module._load_otlp_exporter_class() is None
        assert module.otlp_available is False

    def test_module_does_not_import_otlp_grpc_eagerly(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Importing tracing must not load the native gRPC extension."""
        module = self._load_tracing_copy(
            monkeypatch,
            blocked_prefixes=("opentelemetry.exporter.otlp",),
            otlp_distribution_available=True,
        )

        assert module.otel_available is True
        assert module.otlp_available is True
        assert module._OtlpExporterClass is None

    def test_module_marks_otel_unavailable_when_base_import_fails(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Base OpenTelemetry import failure should disable both OTel and OTLP."""
        module = self._load_tracing_copy(
            monkeypatch,
            blocked_prefixes=("opentelemetry",),
        )

        assert module.otel_available is False
        assert module.otlp_available is False

    def test_module_marks_otlp_unavailable_when_distribution_missing(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Missing OTLP distribution metadata keeps OTEL and disables OTLP."""
        module = self._load_tracing_copy(
            monkeypatch,
            blocked_prefixes=(),
            otlp_distribution_available=False,
        )

        assert module.otel_available is True
        assert module.otlp_available is False


class TestOpenTelemetryTracerSpanAdapter:
    """Tests for span-handle compatibility returned by get_tracer()."""

    def test_start_as_current_span_returns_span_like_handle(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Returned handle supports attributes, events, exceptions, and exit."""
        from bioetl.infrastructure.observability import tracing

        if not tracing.otel_available:
            pytest.skip("OpenTelemetry is not available")

        entered_span = MagicMock()
        context_manager = MagicMock()
        context_manager.__enter__.return_value = entered_span
        context_manager.__exit__.return_value = None
        from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
            InMemorySpanExporter,
        )

        otel_tracer = MagicMock()
        otel_tracer.start_as_current_span.return_value = context_manager
        monkeypatch.setattr(
            tracing,
            "_build_telemetry_exporter",
            InMemorySpanExporter,
        )

        tracer = tracing.OpenTelemetryTracer("test_service")
        monkeypatch.setattr(
            tracer._provider,
            "get_tracer",
            MagicMock(return_value=otel_tracer),
        )
        span = tracer.get_tracer("bioetl.test").start_as_current_span(
            "demo",
            attributes={"bioetl.pipeline": "chembl_activity"},
        )
        span.__enter__()
        span.set_attribute("bioetl.status", "success")
        span.add_event(
            "bioetl.memory.decision",
            attributes={"bioetl.memory.decision_index": 1},
        )
        span.record_exception(RuntimeError("boom"))
        span.__exit__(None, None, None)

        entered_span.set_attribute.assert_called_once_with(
            "bioetl.status",
            "success",
        )
        entered_span.add_event.assert_called_once_with(
            "bioetl.memory.decision",
            attributes={"bioetl.memory.decision_index": 1},
        )
        entered_span.record_exception.assert_called_once()
        context_manager.__exit__.assert_called_once_with(None, None, None)
        tracer.close()

    def test_repeated_initialization_keeps_provider_and_context_ownership_local(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Nested adapters must not override global providers or leak contexts."""
        from bioetl.infrastructure.observability import tracing

        if not tracing.otel_available:
            pytest.skip("OpenTelemetry is not available")

        from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
            InMemorySpanExporter,
        )

        monkeypatch.setattr(
            tracing,
            "_build_telemetry_exporter",
            InMemorySpanExporter,
        )
        caplog.set_level(logging.WARNING)
        first = tracing.OpenTelemetryTracer("bioetl-first")
        second = tracing.OpenTelemetryTracer("bioetl-second")
        try:
            with first.get_tracer("bioetl.outer").start_as_current_span(
                "outer"
            ) as outer_span:
                outer_span.add_event("outer-ready", attributes={"index": 1})
                with second.get_tracer("bioetl.inner").start_as_current_span(
                    "inner"
                ) as inner_span:
                    inner_span.add_event("inner-ready", attributes={"index": 2})
        finally:
            second.close()
            first.close()

        messages = [record.getMessage() for record in caplog.records]
        assert not any(
            "Overriding of current TracerProvider" in message for message in messages
        )
        assert not any("Failed to detach context" in message for message in messages)


class TestModuleAll:
    """Tests for __all__ exports."""

    def test_tracing_module_all__all_exports__de104c4e(self) -> None:
        """All expected items are in __all__."""
        from bioetl.infrastructure.observability import tracing

        expected = ["NoOpTracing", "OpenTelemetryTracer"]
        for name in expected:
            assert name in tracing.__all__


class TestTracingIntegration:
    """Integration tests for tracing module."""

    def test_noop_tracing_usable_as_fallback(self) -> None:
        """NoOpTracing can be used when OTEL is not available."""
        from bioetl.infrastructure.observability import tracing

        # Create NoOpTracing as fallback
        noop = tracing.NoOpTracing()
        tracer = noop.get_tracer("test")

        # Verify it works
        assert tracer is not None

    def test_factory_pattern(self) -> None:
        """Demonstrate factory pattern for choosing tracer."""
        from bioetl.infrastructure.observability import tracing

        def create_tracer(use_otel: bool = False) -> NoOpTracing:
            if use_otel and tracing.otel_available:
                return tracing.OpenTelemetryTracer("bioetl")
            return tracing.NoOpTracing()

        # Should always work
        tracer = create_tracer(use_otel=False)
        assert isinstance(tracer, NoOpTracing)


@pytest.mark.unit
class TestOTLPAvailability:
    """Tests for OTLP exporter availability checks."""

    def test_otlp_available_flag_defined(self) -> None:
        """Test otlp_available flag is defined."""
        from bioetl.infrastructure.observability import tracing

        assert hasattr(tracing, "otlp_available")
        assert isinstance(tracing.otlp_available, bool)

    def test_otlp_exporter_class_cache_populated_after_load(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Lazy cache is empty before load, populated after, and reused on second call."""
        from bioetl.infrastructure.observability import tracing

        monkeypatch.setattr(tracing, "otlp_available", True)
        monkeypatch.setattr(tracing, "_OtlpExporterClass", None)
        exporter_factory = object()
        import_calls: list[str] = []

        def _fake_import(name: str) -> ModuleType:
            import_calls.append(name)
            return type("M", (), {"OTLPSpanExporter": exporter_factory})()

        monkeypatch.setattr(tracing, "import_module", _fake_import)

        assert tracing._OtlpExporterClass is None
        assert tracing._load_otlp_exporter_class() is exporter_factory
        assert tracing._OtlpExporterClass is exporter_factory
        assert len(import_calls) == 1

        # Second call must reuse the cache without another import_module.
        assert tracing._load_otlp_exporter_class() is exporter_factory
        assert len(import_calls) == 1


@pytest.mark.unit
class TestTelemetryExporterResolution:
    """Tests for OTLP exporter resolution helpers."""

    def test_prefers_insecure_for_local_tempo_when_env_unspecified(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Local Tempo endpoints should default to insecure OTLP."""
        from bioetl.infrastructure.observability import tracing

        if not tracing.otel_available:
            pytest.skip("OpenTelemetry is not available")

        exporter_factory = MagicMock(return_value=MagicMock())
        monkeypatch.setattr(tracing, "otlp_available", True)
        monkeypatch.setattr(tracing, "_OtlpExporterClass", exporter_factory)
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "localhost:4317")
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_INSECURE", raising=False)
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_TRACES_INSECURE", raising=False)

        tracing._build_telemetry_exporter()

        exporter_factory.assert_called_once_with(
            endpoint="localhost:4317",
            insecure=True,
        )

    def test_respects_explicit_insecure_override(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Explicit insecure env values should win over local defaults."""
        from bioetl.infrastructure.observability import tracing

        if not tracing.otel_available:
            pytest.skip("OpenTelemetry is not available")

        exporter_factory = MagicMock(return_value=MagicMock())
        monkeypatch.setattr(tracing, "otlp_available", True)
        monkeypatch.setattr(tracing, "_OtlpExporterClass", exporter_factory)
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "localhost:4317")
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_INSECURE", "false")
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_TRACES_INSECURE", raising=False)

        tracing._build_telemetry_exporter()

        exporter_factory.assert_called_once_with(
            endpoint="localhost:4317",
            insecure=False,
        )


@pytest.mark.unit
class TestOpenTelemetryTracerGetTracer:
    """Tests for get_tracer method."""

    def test_get_tracer_returns_tracer(self) -> None:
        """Test get_tracer returns an OpenTelemetry tracer."""
        from bioetl.infrastructure.observability import tracing

        if tracing.otel_available:
            otel_tracer = tracing.OpenTelemetryTracer("test_service")
            try:
                tracer = otel_tracer.get_tracer("component")
                assert tracer is not None
            finally:
                otel_tracer.close()
        else:
            pytest.skip("OpenTelemetry is not available")

    def test_get_tracer_with_different_names(self) -> None:
        """Test get_tracer can be called with different names."""
        from bioetl.infrastructure.observability import tracing

        if tracing.otel_available:
            otel_tracer = tracing.OpenTelemetryTracer("test_service")
            try:
                tracer1 = otel_tracer.get_tracer("component1")
                tracer2 = otel_tracer.get_tracer("component2")
                assert tracer1 is not None
                assert tracer2 is not None
            finally:
                otel_tracer.close()
        else:
            pytest.skip("OpenTelemetry is not available")


@pytest.mark.unit
class TestOpenTelemetryTracerCloseExceptionHandling:
    """Tests for close() exception handling."""

    def test_close_handles_force_flush_exception(self) -> None:
        """Test close() handles exceptions from force_flush gracefully."""
        from bioetl.infrastructure.observability import tracing

        if tracing.otel_available:
            otel_tracer = tracing.OpenTelemetryTracer("test_service")

            # Mock the provider to raise an exception during force_flush
            otel_tracer._provider.force_flush = MagicMock(
                side_effect=RuntimeError("Force flush failed")
            )

            # close() should not raise
            otel_tracer.close()

            # Should be marked as closed
            assert otel_tracer._closed is True
        else:
            pytest.skip("OpenTelemetry is not available")

    def test_close_handles_shutdown_exception(self) -> None:
        """Test close() handles exceptions from shutdown gracefully."""
        from bioetl.infrastructure.observability import tracing

        if tracing.otel_available:
            otel_tracer = tracing.OpenTelemetryTracer("test_service")

            # Mock the provider to raise an exception during shutdown
            otel_tracer._provider.force_flush = MagicMock()
            otel_tracer._provider.shutdown = MagicMock(
                side_effect=RuntimeError("Shutdown failed")
            )

            # close() should not raise
            otel_tracer.close()

            # Should be marked as closed
            assert otel_tracer._closed is True
        else:
            pytest.skip("OpenTelemetry is not available")


@pytest.mark.unit
class TestOpenTelemetryTracerWithMockedOTEL:
    """Tests with fully mocked OpenTelemetry to test edge cases."""

    def test_init_raises_importerror_when_otel_not_available(self) -> None:
        """Test ImportError is raised when OTEL is not available."""
        # We need to test the case where otel_available is False
        # This requires temporarily patching the module
        from bioetl.infrastructure.observability import tracing

        original_available = tracing.otel_available
        try:
            # Temporarily set OTEL as unavailable
            tracing.otel_available = False

            with pytest.raises(ImportError) as exc_info:
                tracing.OpenTelemetryTracer("test")

            assert "OpenTelemetry is not installed" in str(exc_info.value)
        finally:
            # Restore original value
            tracing.otel_available = original_available

    def test_tracer_with_console_exporter_when_otlp_unavailable(self) -> None:
        """Test tracer uses ConsoleSpanExporter when OTLP is unavailable."""
        from bioetl.infrastructure.observability import tracing

        if tracing.otel_available:
            original_otlp = tracing.otlp_available
            original_class = tracing._OtlpExporterClass

            try:
                # Simulate OTLP unavailable
                tracing.otlp_available = False
                tracing._OtlpExporterClass = None

                # Should still work with ConsoleSpanExporter
                otel_tracer = tracing.OpenTelemetryTracer("test_service")
                assert otel_tracer is not None
                otel_tracer.close()
            finally:
                tracing.otlp_available = original_otlp
                tracing._OtlpExporterClass = original_class
        else:
            pytest.skip("OpenTelemetry is not available")


@pytest.mark.unit
class TestOpenTelemetryTracerServiceName:
    """Tests for service name configuration."""

    def test_default_service_name(self) -> None:
        """Test default service name is 'bioetl'."""
        from bioetl.infrastructure.observability import tracing

        if tracing.otel_available:
            # Create with default service name
            otel_tracer = tracing.OpenTelemetryTracer()
            assert otel_tracer is not None
            otel_tracer.close()
        else:
            pytest.skip("OpenTelemetry is not available")

    def test_custom_service_name(self) -> None:
        """Test custom service name can be set."""
        from bioetl.infrastructure.observability import tracing

        if tracing.otel_available:
            otel_tracer = tracing.OpenTelemetryTracer("custom_service")
            assert otel_tracer is not None
            otel_tracer.close()
        else:
            pytest.skip("OpenTelemetry is not available")
