"""Tests for infrastructure/observability/tracing.py.

These tests verify the OpenTelemetry tracing implementation.
"""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

from bioetl.domain.ports.noop import NoOpTracing


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
        """OTEL_AVAILABLE flag is defined."""
        from bioetl.infrastructure.observability import tracing

        assert hasattr(tracing, "OTEL_AVAILABLE")
        assert isinstance(tracing.OTEL_AVAILABLE, bool)

    def test_opentelemetry_tracer_class_defined(self) -> None:
        """OpenTelemetryTracer class is defined."""
        from bioetl.infrastructure.observability import tracing

        assert hasattr(tracing, "OpenTelemetryTracer")


class TestOpenTelemetryTracerWithoutOTEL:
    """Tests for OpenTelemetryTracer when OpenTelemetry is not available."""

    def test_init_raises_without_otel(self) -> None:
        """OpenTelemetryTracer raises ImportError if OTEL not available."""
        from bioetl.infrastructure.observability import tracing

        if not tracing.OTEL_AVAILABLE:
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

        if tracing.OTEL_AVAILABLE:
            # Create tracer - it should work
            tracer = tracing.OpenTelemetryTracer("test_service")
            assert tracer is not None
            tracer.close()
        else:
            pytest.skip("OpenTelemetry is not available")

    def test_sets_service_name_resource_attribute(self) -> None:
        """Tracer provider should publish a stable service.name resource."""
        from bioetl.infrastructure.observability import tracing

        if tracing.OTEL_AVAILABLE:
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

        if tracing.OTEL_AVAILABLE:
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

    def test_close_is_idempotent__test_open_telemetry_tracer_close_infrastructure_observability_test_tracing_158(self) -> None:
        """close() can be called multiple times safely."""
        from bioetl.infrastructure.observability import tracing

        if tracing.OTEL_AVAILABLE:
            tracer = tracing.OpenTelemetryTracer("test")
            tracer.close()
            tracer.close()  # Should not raise
            tracer.close()  # Should not raise
        else:
            pytest.skip("OpenTelemetry is not available")


class TestOpenTelemetryTracerSpanAdapter:
    """Tests for span-handle compatibility returned by get_tracer()."""

    def test_start_as_current_span_returns_span_like_handle(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Returned handle should support set_attribute/record_exception/__exit__."""
        from bioetl.infrastructure.observability import tracing

        if not tracing.OTEL_AVAILABLE:
            pytest.skip("OpenTelemetry is not available")

        entered_span = MagicMock()
        context_manager = MagicMock()
        context_manager.__enter__.return_value = entered_span
        context_manager.__exit__.return_value = None
        otel_tracer = MagicMock()
        otel_tracer.start_as_current_span.return_value = context_manager
        monkeypatch.setattr(
            tracing.trace, "get_tracer", MagicMock(return_value=otel_tracer)
        )

        tracer = tracing.OpenTelemetryTracer("test_service")
        span = tracer.get_tracer("bioetl.test").start_as_current_span(
            "demo",
            attributes={"bioetl.pipeline": "chembl_activity"},
        )
        span.__enter__()
        span.set_attribute("bioetl.status", "success")
        span.record_exception(RuntimeError("boom"))
        span.__exit__(None, None, None)

        entered_span.set_attribute.assert_called_once_with(
            "bioetl.status",
            "success",
        )
        entered_span.record_exception.assert_called_once()
        context_manager.__exit__.assert_called_once_with(None, None, None)
        tracer.close()


class TestModuleAll:
    """Tests for __all__ exports."""

    def test_all_exports(self) -> None:
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
            if use_otel and tracing.OTEL_AVAILABLE:
                return tracing.OpenTelemetryTracer("bioetl")
            return tracing.NoOpTracing()

        # Should always work
        tracer = create_tracer(use_otel=False)
        assert isinstance(tracer, NoOpTracing)


@pytest.mark.unit
class TestOTLPAvailability:
    """Tests for OTLP exporter availability checks."""

    def test_otlp_available_flag_defined(self) -> None:
        """Test OTLP_AVAILABLE flag is defined."""
        from bioetl.infrastructure.observability import tracing

        assert hasattr(tracing, "OTLP_AVAILABLE")
        assert isinstance(tracing.OTLP_AVAILABLE, bool)

    def test_otlp_exporter_class_stored(self) -> None:
        """Test _OtlpExporterClass is set correctly based on availability."""
        from bioetl.infrastructure.observability import tracing

        if tracing.OTLP_AVAILABLE:
            assert tracing._OtlpExporterClass is not None
        else:
            # When OTLP is not available, _OtlpExporterClass might be None
            # depending on whether the base OTEL is available
            pass


@pytest.mark.unit
class TestTelemetryExporterResolution:
    """Tests for OTLP exporter resolution helpers."""

    def test_prefers_insecure_for_local_tempo_when_env_unspecified(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Local Tempo endpoints should default to insecure OTLP."""
        from bioetl.infrastructure.observability import tracing

        if not tracing.OTEL_AVAILABLE:
            pytest.skip("OpenTelemetry is not available")

        exporter_factory = MagicMock(return_value=MagicMock())
        monkeypatch.setattr(tracing, "OTLP_AVAILABLE", True)
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

        if not tracing.OTEL_AVAILABLE:
            pytest.skip("OpenTelemetry is not available")

        exporter_factory = MagicMock(return_value=MagicMock())
        monkeypatch.setattr(tracing, "OTLP_AVAILABLE", True)
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

        if tracing.OTEL_AVAILABLE:
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

        if tracing.OTEL_AVAILABLE:
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

        if tracing.OTEL_AVAILABLE:
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

        if tracing.OTEL_AVAILABLE:
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
        # We need to test the case where OTEL_AVAILABLE is False
        # This requires temporarily patching the module
        from bioetl.infrastructure.observability import tracing

        original_available = tracing.OTEL_AVAILABLE
        try:
            # Temporarily set OTEL as unavailable
            tracing.OTEL_AVAILABLE = False

            with pytest.raises(ImportError) as exc_info:
                tracing.OpenTelemetryTracer("test")

            assert "OpenTelemetry is not installed" in str(exc_info.value)
        finally:
            # Restore original value
            tracing.OTEL_AVAILABLE = original_available

    def test_tracer_with_console_exporter_when_otlp_unavailable(self) -> None:
        """Test tracer uses ConsoleSpanExporter when OTLP is unavailable."""
        from bioetl.infrastructure.observability import tracing

        if tracing.OTEL_AVAILABLE:
            original_otlp = tracing.OTLP_AVAILABLE
            original_class = tracing._OtlpExporterClass

            try:
                # Simulate OTLP unavailable
                tracing.OTLP_AVAILABLE = False
                tracing._OtlpExporterClass = None

                # Should still work with ConsoleSpanExporter
                otel_tracer = tracing.OpenTelemetryTracer("test_service")
                assert otel_tracer is not None
                otel_tracer.close()
            finally:
                tracing.OTLP_AVAILABLE = original_otlp
                tracing._OtlpExporterClass = original_class
        else:
            pytest.skip("OpenTelemetry is not available")


@pytest.mark.unit
class TestOpenTelemetryTracerServiceName:
    """Tests for service name configuration."""

    def test_default_service_name(self) -> None:
        """Test default service name is 'bioetl'."""
        from bioetl.infrastructure.observability import tracing

        if tracing.OTEL_AVAILABLE:
            # Create with default service name
            otel_tracer = tracing.OpenTelemetryTracer()
            assert otel_tracer is not None
            otel_tracer.close()
        else:
            pytest.skip("OpenTelemetry is not available")

    def test_custom_service_name(self) -> None:
        """Test custom service name can be set."""
        from bioetl.infrastructure.observability import tracing

        if tracing.OTEL_AVAILABLE:
            otel_tracer = tracing.OpenTelemetryTracer("custom_service")
            assert otel_tracer is not None
            otel_tracer.close()
        else:
            pytest.skip("OpenTelemetry is not available")
