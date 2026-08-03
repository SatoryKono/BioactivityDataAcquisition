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
"""Unit tests for CLI NoOp factory functions.

Tests that create_noop_* functions return correct NoOp implementations
that satisfy their respective port interfaces.
"""

from __future__ import annotations

import pytest

from bioetl.composition.bootstrap.cli.noop import (
    create_noop_logger,
    create_noop_metrics,
    create_noop_observability_bundle,
    create_noop_tracing,
)
from bioetl.domain.ports import MetricsPort, TracingPort
from bioetl.infrastructure.observability.noop_logger import NoOpLogger


@pytest.mark.unit
class TestCreateNoopLogger:
    """Tests for create_noop_logger factory function."""

    def test_returns_noop_logger_instance(self) -> None:
        """create_noop_logger should return a NoOpLogger instance."""
        result = create_noop_logger()

        assert isinstance(result, NoOpLogger)

    def test_create_noop_logger__creates_new_instance__ccf6c94d(self) -> None:
        """Each call should create a distinct instance (no shared state)."""
        logger1 = create_noop_logger()
        logger2 = create_noop_logger()

        assert logger1 is not logger2

    def test_logger_is_callable_info(self) -> None:
        """Returned logger should accept info() calls without raising."""
        logger = create_noop_logger()

        # Should not raise
        logger.info("test message")

        assert isinstance(logger, NoOpLogger)

    def test_logger_accepts_log_calls(self) -> None:
        """Returned logger should accept structured log calls without raising."""
        logger = create_noop_logger()

        # All these should be silently ignored without raising
        logger.info("info msg", key="value")
        logger.warning("warning msg")
        logger.error("error msg", code=42)
        logger.debug("debug msg")

        assert isinstance(logger, NoOpLogger)


@pytest.mark.unit
class TestCreateNoopMetrics:
    """Tests for create_noop_metrics factory function."""

    def test_returns_metrics_port_instance(self) -> None:
        """create_noop_metrics should return an object implementing MetricsPort."""
        result = create_noop_metrics()

        assert isinstance(result, MetricsPort)

    def test_create_noop_metrics__creates_new_instance__28c6c219(self) -> None:
        """Each call should create a distinct instance."""
        metrics1 = create_noop_metrics()
        metrics2 = create_noop_metrics()

        assert metrics1 is not metrics2

    def test_metrics_is_noop_type(self) -> None:
        """CLI NoOp metrics should be a NoOpMetrics instance."""
        from bioetl.domain.ports.noop import NoOpMetrics

        result = create_noop_metrics()

        assert isinstance(result, NoOpMetrics)

    def test_metrics_accepts_counter_calls(self) -> None:
        """Returned metrics should accept increment_counter calls without raising."""
        metrics = create_noop_metrics()

        # Should not raise
        metrics.increment_counter("test_counter", 1, {"label": "value"})

        assert isinstance(metrics, MetricsPort)


@pytest.mark.unit
class TestCreateNoopTracing:
    """Tests for create_noop_tracing factory function."""

    def test_returns_tracing_port_instance(self) -> None:
        """create_noop_tracing should return an object implementing TracingPort."""
        result = create_noop_tracing()

        assert isinstance(result, TracingPort)

    def test_create_noop_tracing__creates_new_instance__10d74add(self) -> None:
        """Each call should create a distinct instance."""
        tracing1 = create_noop_tracing()
        tracing2 = create_noop_tracing()

        assert tracing1 is not tracing2

    def test_tracing_is_noop_type(self) -> None:
        """Returned tracing should be NoOpTracing implementation."""
        from bioetl.domain.ports.noop import NoOpTracing

        result = create_noop_tracing()

        assert isinstance(result, NoOpTracing)


@pytest.mark.unit
class TestCreateNoopObservabilityBundle:
    """Tests for create_noop_observability_bundle factory function."""

    def test_returns_three_element_tuple(self) -> None:
        """create_noop_observability_bundle should return (logger, metrics, tracing)."""
        result = create_noop_observability_bundle()

        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_bundle_contains_correct_types(self) -> None:
        """Bundle should contain NoOpLogger, MetricsPort, TracingPort."""
        logger, metrics, tracing = create_noop_observability_bundle()

        assert isinstance(logger, NoOpLogger)
        assert isinstance(metrics, MetricsPort)
        assert isinstance(tracing, TracingPort)

    def test_each_call_creates_new_instances(self) -> None:
        """Each call should create new instances — no shared state."""
        bundle1 = create_noop_observability_bundle()
        bundle2 = create_noop_observability_bundle()

        logger1, metrics1, tracing1 = bundle1
        logger2, metrics2, tracing2 = bundle2

        assert logger1 is not logger2
        assert metrics1 is not metrics2
        assert tracing1 is not tracing2

    def test_unpacking_works(self) -> None:
        """Bundle should support tuple unpacking."""
        logger, metrics, tracing = create_noop_observability_bundle()

        # Should not raise; use the objects
        logger.info("test")
        assert metrics is not None
        assert tracing is not None
