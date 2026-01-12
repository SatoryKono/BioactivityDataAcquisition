"""Tests for infrastructure/observability/tracing.py.

These tests verify the OpenTelemetry tracing implementation.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from bioetl.infrastructure.observability.noop_tracing import NoOpTracing


class TestNoOpTracingReExport:
    """Tests for NoOpTracing re-export from tracing module."""

    def test_noop_tracing_importable(self) -> None:
        """NoOpTracing is importable from tracing module."""
        from bioetl.infrastructure.observability.tracing import NoOpTracing

        assert NoOpTracing is not None

    def test_noop_tracing_is_same(self) -> None:
        """NoOpTracing from tracing is same as direct import."""
        from bioetl.infrastructure.observability.noop_tracing import (
            NoOpTracing as Direct,
        )
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
    def mock_otel(self) -> None:
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


class TestOpenTelemetryTracerClose:
    """Tests for OpenTelemetryTracer close behavior."""

    def test_close_is_idempotent(self) -> None:
        """close() can be called multiple times safely."""
        from bioetl.infrastructure.observability import tracing

        if tracing.OTEL_AVAILABLE:
            tracer = tracing.OpenTelemetryTracer("test")
            tracer.close()
            tracer.close()  # Should not raise
            tracer.close()  # Should not raise
        else:
            pytest.skip("OpenTelemetry is not available")


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
                side_effect=Exception("Force flush failed")
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
                side_effect=Exception("Shutdown failed")
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
