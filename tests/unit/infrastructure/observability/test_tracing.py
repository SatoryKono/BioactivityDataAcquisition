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
            pytest.skip("OpenTelemetry is available")


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
