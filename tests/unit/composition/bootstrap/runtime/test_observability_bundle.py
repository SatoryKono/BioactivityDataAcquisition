"""Unit tests for observability_bundle bootstrap helpers."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, call
from uuid import UUID

import pytest

from bioetl.composition.observability import ObservabilityBundle
from bioetl.domain.ports import NoOpMetrics, NoOpTracing


_FIXED_UUID = UUID("abcdef01-2345-6789-abcd-ef0123456789")


@pytest.mark.unit
class TestValidateObservabilityPreflightImpl:
    """Tests for validate_observability_preflight_impl."""

    def test_noop_tracing_warns_in_prod(self) -> None:
        """NoOpTracing in production environment triggers a warning log."""
        from bioetl.composition.bootstrap.runtime.observability_bundle import (
            validate_observability_preflight_impl,
        )

        logger = MagicMock()
        validate_observability_preflight_impl(
            tracer=NoOpTracing(),
            metrics=MagicMock(spec=["increment"]),
            environment="prod",
            logger=logger,
        )

        logger.warning.assert_any_call(
            "noop_tracing_in_production",
            message="NoOpTracing in production - traces will be lost",
            recommendation=(
                "Set BIOETL_OBSERVABILITY__TRACING_ENABLED=true "
                "and configure OpenTelemetry endpoint"
            ),
        )

    def test_noop_metrics_warns_in_prod(self) -> None:
        """NoOpMetrics in production environment triggers a warning log."""
        from bioetl.composition.bootstrap.runtime.observability_bundle import (
            validate_observability_preflight_impl,
        )

        logger = MagicMock()
        validate_observability_preflight_impl(
            tracer=MagicMock(),
            metrics=NoOpMetrics(),
            environment="prod",
            logger=logger,
        )

        logger.warning.assert_any_call(
            "noop_metrics_in_production",
            message="NoOpMetrics in production - metrics will be lost",
            recommendation=(
                "Set BIOETL_OBSERVABILITY__METRICS_ENABLED=true "
                "to enable Prometheus metrics collection"
            ),
        )

    def test_non_prod_environment_silent(self) -> None:
        """Non-production environments do not emit warnings even with NoOps."""
        from bioetl.composition.bootstrap.runtime.observability_bundle import (
            validate_observability_preflight_impl,
        )

        logger = MagicMock()
        validate_observability_preflight_impl(
            tracer=NoOpTracing(),
            metrics=NoOpMetrics(),
            environment="staging",
            logger=logger,
        )

        logger.warning.assert_not_called()

    def test_real_implementations_no_warn_in_prod(self) -> None:
        """Real tracer and metrics in prod do not trigger warnings."""
        from bioetl.composition.bootstrap.runtime.observability_bundle import (
            validate_observability_preflight_impl,
        )

        logger = MagicMock()
        validate_observability_preflight_impl(
            tracer=MagicMock(),
            metrics=MagicMock(),
            environment="prod",
            logger=logger,
        )

        logger.warning.assert_not_called()


@pytest.mark.unit
class TestBootstrapObservabilityBundleImpl:
    """Tests for bootstrap_observability_bundle_impl."""

    def test_returns_observability_bundle(self) -> None:
        """Function returns an ObservabilityBundle with all components."""
        from bioetl.composition.bootstrap.runtime.observability_bundle import (
            bootstrap_observability_bundle_impl,
        )

        logger = MagicMock()
        tracer = MagicMock()
        metrics = MagicMock()
        dq_monitor = MagicMock()
        settings = SimpleNamespace(env="dev")

        bundle = bootstrap_observability_bundle_impl(
            pipeline="test_pipe",
            run_id=_FIXED_UUID,
            settings=settings,
            log_level="INFO",
            logger_bootstrapper=lambda _p, _r, _l: logger,
            tracer_bootstrapper=lambda _s: tracer,
            metrics_bootstrapper=lambda _s: metrics,
            dq_monitor_bootstrapper=lambda _s, _lg: dq_monitor,
            preflight_validator=MagicMock(),
        )

        assert isinstance(bundle, ObservabilityBundle)
        assert bundle.logger is logger
        assert bundle.tracer is tracer
        assert bundle.metrics is metrics
        assert bundle.dq_monitor is dq_monitor

    def test_calls_preflight_validator(self) -> None:
        """preflight_validator is called with assembled components."""
        from bioetl.composition.bootstrap.runtime.observability_bundle import (
            bootstrap_observability_bundle_impl,
        )

        tracer = MagicMock()
        metrics = MagicMock()
        logger = MagicMock()
        settings = SimpleNamespace(env="prod")
        preflight = MagicMock()

        bootstrap_observability_bundle_impl(
            pipeline="p",
            run_id=_FIXED_UUID,
            settings=settings,
            log_level="DEBUG",
            logger_bootstrapper=lambda _p, _r, _l: logger,
            tracer_bootstrapper=lambda _s: tracer,
            metrics_bootstrapper=lambda _s: metrics,
            dq_monitor_bootstrapper=lambda _s, _lg: None,
            preflight_validator=preflight,
        )

        preflight.assert_called_once_with(tracer, metrics, "prod", logger)

    def test_logs_observability_initialized(self) -> None:
        """Emits observability_initialized info log after assembly."""
        from bioetl.composition.bootstrap.runtime.observability_bundle import (
            bootstrap_observability_bundle_impl,
        )

        logger = MagicMock()
        settings = SimpleNamespace(env="dev")

        bootstrap_observability_bundle_impl(
            pipeline="p",
            run_id=_FIXED_UUID,
            settings=settings,
            log_level="INFO",
            logger_bootstrapper=lambda _p, _r, _l: logger,
            tracer_bootstrapper=lambda _s: MagicMock(),
            metrics_bootstrapper=lambda _s: MagicMock(),
            dq_monitor_bootstrapper=lambda _s, _lg: None,
            preflight_validator=MagicMock(),
        )

        logger.info.assert_called_once()
        assert logger.info.call_args[0][0] == "observability_initialized"
