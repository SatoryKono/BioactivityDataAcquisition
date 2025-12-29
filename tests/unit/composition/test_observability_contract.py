"""Tests for Unified Observability Contract.

Verifies that:
1. ObservabilityBundle enforces required components (logger, metrics)
2. bootstrap_observability() always returns valid implementations
3. NoOpMetrics is used as fallback when Prometheus disabled
4. Pipeline cannot run without valid logger
5. Health-check metrics are properly recorded
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from bioetl.composition.observability import (
    ObservabilityBundle,
    ObservabilityContractError,
)
from bioetl.infrastructure.observability.noop_metrics import NoOpMetrics


@pytest.mark.unit
class TestObservabilityBundle:
    """Tests for ObservabilityBundle contract enforcement."""

    def test_bundle_requires_logger(self) -> None:
        """Test that bundle creation fails without logger."""
        mock_metrics = MagicMock()

        with pytest.raises(ObservabilityContractError, match="Logger is required"):
            ObservabilityBundle(logger=None, metrics=mock_metrics)  # type: ignore[arg-type]

    def test_bundle_requires_metrics(self) -> None:
        """Test that bundle creation fails without metrics."""
        mock_logger = MagicMock()

        with pytest.raises(
            ObservabilityContractError, match="Metrics port is required"
        ):
            ObservabilityBundle(logger=mock_logger, metrics=None)  # type: ignore[arg-type]

    def test_bundle_allows_optional_tracer_none(self) -> None:
        """Test that tracer can be None."""
        mock_logger = MagicMock()
        mock_metrics = MagicMock()

        bundle = ObservabilityBundle(
            logger=mock_logger,
            metrics=mock_metrics,
            tracer=None,
            dq_monitor=None,
        )

        assert bundle.tracer is None
        assert bundle.dq_monitor is None

    def test_bundle_create_factory_method(self) -> None:
        """Test factory method enforces contract."""
        mock_logger = MagicMock()
        mock_metrics = MagicMock()
        mock_tracer = MagicMock()

        bundle = ObservabilityBundle.create(
            logger=mock_logger,
            metrics=mock_metrics,
            tracer=mock_tracer,
        )

        assert bundle.logger is mock_logger
        assert bundle.metrics is mock_metrics
        assert bundle.tracer is mock_tracer

    def test_bundle_bind_preserves_metrics(self) -> None:
        """Test that bind() preserves metrics reference."""
        mock_logger = MagicMock()
        mock_logger.bind.return_value = MagicMock()
        mock_metrics = MagicMock()

        bundle = ObservabilityBundle(logger=mock_logger, metrics=mock_metrics)
        new_bundle = bundle.bind(run_id="test-123")

        assert new_bundle.metrics is mock_metrics

    def test_bundle_frozen(self) -> None:
        """Test that bundle is frozen (immutable)."""
        mock_logger = MagicMock()
        mock_metrics = MagicMock()

        bundle = ObservabilityBundle(logger=mock_logger, metrics=mock_metrics)

        with pytest.raises(FrozenInstanceError):
            bundle.metrics = MagicMock()  # type: ignore[misc]


@pytest.mark.unit
class TestBootstrapObservability:
    """Tests for bootstrap_observability() function."""

    @patch("bioetl.composition._bootstrap.observability.start_metrics_server")
    @patch("bioetl.composition._bootstrap.observability.PrometheusMetrics")
    @patch("bioetl.composition._bootstrap.observability.create_infra_logger")
    def test_bootstrap_returns_valid_bundle(
        self,
        mock_create_logger: MagicMock,
        mock_prometheus: MagicMock,
        mock_start_server: MagicMock,
    ) -> None:
        """Test that bootstrap returns bundle with valid implementations."""
        from bioetl.composition._bootstrap.observability import bootstrap_observability

        # Setup mocks
        mock_logger = MagicMock()
        mock_logger.info = MagicMock()
        mock_create_logger.return_value = mock_logger
        mock_metrics = MagicMock()
        mock_prometheus.return_value = mock_metrics

        settings = MagicMock()
        settings.metrics_port = 8000
        settings.observability.metrics_enabled = True
        settings.observability.metrics_server_enabled = False
        settings.observability.tracing_enabled = False
        settings.observability.dq_monitor_enabled = False

        bundle = bootstrap_observability(
            pipeline="test_pipeline",
            run_id=uuid4(),
            settings=settings,
        )

        assert bundle.logger is mock_logger
        assert bundle.metrics is mock_metrics
        assert bundle.tracer is not None  # NoOpTracing
        assert bundle.dq_monitor is None

    @patch("bioetl.composition._bootstrap.observability.create_infra_logger")
    def test_bootstrap_uses_noop_metrics_when_disabled(
        self,
        mock_create_logger: MagicMock,
    ) -> None:
        """Test that NoOpMetrics is used when metrics disabled."""
        from bioetl.composition._bootstrap.observability import bootstrap_observability

        mock_logger = MagicMock()
        mock_logger.info = MagicMock()
        mock_create_logger.return_value = mock_logger

        settings = MagicMock()
        settings.observability.metrics_enabled = False
        settings.observability.tracing_enabled = False
        settings.observability.dq_monitor_enabled = False

        bundle = bootstrap_observability(
            pipeline="test_pipeline",
            run_id=uuid4(),
            settings=settings,
        )

        assert isinstance(bundle.metrics, NoOpMetrics)

    @patch("bioetl.composition._bootstrap.observability.create_infra_logger")
    def test_bootstrap_logs_initialization_status(
        self,
        mock_create_logger: MagicMock,
    ) -> None:
        """Test that bootstrap logs observability initialization."""
        from bioetl.composition._bootstrap.observability import bootstrap_observability

        mock_logger = MagicMock()
        mock_create_logger.return_value = mock_logger

        settings = MagicMock()
        settings.observability.metrics_enabled = False
        settings.observability.tracing_enabled = False
        settings.observability.dq_monitor_enabled = False

        bootstrap_observability(
            pipeline="test_pipeline",
            run_id=uuid4(),
            settings=settings,
        )

        # Verify initialization was logged
        mock_logger.info.assert_called_with(
            "observability_initialized",
            extra={
                "stage": "bootstrap",
                "metrics_type": "NoOpMetrics",
                "tracer_type": "NoOpTracing",
                "dq_monitor_enabled": False,
            },
        )


@pytest.mark.unit
class TestBootstrapMetrics:
    """Tests for bootstrap_metrics() function."""

    def test_disabled_metrics_returns_noop_metrics(self) -> None:
        """Test that disabled metrics returns NoOpMetrics, not None."""
        from bioetl.composition._bootstrap.observability import bootstrap_metrics

        settings = MagicMock()
        settings.observability.metrics_enabled = False

        result = bootstrap_metrics(settings)

        assert result is not None
        assert isinstance(result, NoOpMetrics)

    def test_noop_metrics_no_warning_when_disabled(self) -> None:
        """Test that NoOpMetrics doesn't warn when explicitly disabled."""
        from bioetl.composition._bootstrap.observability import bootstrap_metrics

        # Reset warning state
        NoOpMetrics.reset_warning()

        settings = MagicMock()
        settings.observability.metrics_enabled = False

        import warnings

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            bootstrap_metrics(settings)
            # No warning should be raised
            assert len(w) == 0

    @patch("bioetl.composition._bootstrap.observability.start_metrics_server")
    @patch("bioetl.composition._bootstrap.observability.PrometheusMetrics")
    def test_enabled_metrics_returns_prometheus_metrics(
        self,
        mock_prometheus: MagicMock,
        mock_start_server: MagicMock,
    ) -> None:
        """Test that enabled metrics returns PrometheusMetrics."""
        from bioetl.composition._bootstrap.observability import bootstrap_metrics

        mock_metrics = MagicMock()
        mock_prometheus.return_value = mock_metrics

        settings = MagicMock()
        settings.metrics_port = 8000
        settings.observability.metrics_enabled = True
        settings.observability.metrics_server_enabled = False

        result = bootstrap_metrics(settings)

        assert result is mock_metrics
        mock_prometheus.assert_called_once()


@pytest.mark.unit
class TestNoOpMetricsContract:
    """Tests for NoOpMetrics as fallback implementation."""

    def test_noop_metrics_implements_port(self) -> None:
        """Test that NoOpMetrics implements MetricsPort."""
        from bioetl.domain.ports import MetricsPort

        metrics = NoOpMetrics(warn_on_use=False)
        assert isinstance(metrics, MetricsPort)

    def test_noop_metrics_all_methods_are_noop(self) -> None:
        """Test that all NoOpMetrics methods are no-op."""
        metrics = NoOpMetrics(warn_on_use=False)

        # These should not raise
        metrics.observe_histogram("test", 1.0, {"label": "value"})
        metrics.increment_counter("test", 1, {"label": "value"})
        metrics.set_gauge("test", 1.0, {"label": "value"})
        metrics.close()

    def test_noop_metrics_close_is_idempotent(self) -> None:
        """Test that close() can be called multiple times."""
        metrics = NoOpMetrics(warn_on_use=False)

        # Multiple closes should not raise
        metrics.close()
        metrics.close()
        metrics.close()


@pytest.mark.unit
class TestObservabilityContractError:
    """Tests for ObservabilityContractError exception."""

    def test_error_is_exception(self) -> None:
        """Test that ObservabilityContractError is an Exception."""
        error = ObservabilityContractError("test message")
        assert isinstance(error, Exception)

    def test_error_has_message(self) -> None:
        """Test that error message is preserved."""
        error = ObservabilityContractError("test message")
        assert str(error) == "test message"


@pytest.mark.unit
class TestHealthCheckMetrics:
    """Tests for health check metrics definitions."""

    def test_health_check_metrics_exist(self) -> None:
        """Test that health check metrics are defined."""
        from bioetl.infrastructure.observability.metrics import (
            HEALTH_CHECK_DURATION_SECONDS,
            INFRASTRUCTURE_VALIDATED,
            PIPELINE_HEALTH_CHECK_PASSED,
        )

        assert PIPELINE_HEALTH_CHECK_PASSED is not None
        assert INFRASTRUCTURE_VALIDATED is not None
        assert HEALTH_CHECK_DURATION_SECONDS is not None

    def test_health_check_metrics_have_correct_labels(self) -> None:
        """Test that health check metrics have correct labels."""
        from bioetl.infrastructure.observability.metrics import (
            INFRASTRUCTURE_VALIDATED,
            PIPELINE_HEALTH_CHECK_PASSED,
        )

        # Verify label names from metric description
        assert "pipeline" in PIPELINE_HEALTH_CHECK_PASSED._labelnames
        assert "component" in PIPELINE_HEALTH_CHECK_PASSED._labelnames
        assert "pipeline" in INFRASTRUCTURE_VALIDATED._labelnames
        assert "run_id" in INFRASTRUCTURE_VALIDATED._labelnames


@pytest.mark.unit
class TestObservabilityPreflightValidation:
    """Tests for observability preflight validation.

    Verifies that NoOp implementations in production trigger warnings
    to prevent silent data loss.
    """

    def test_observability_production_warning_noop_tracing(self) -> None:
        """Test that NoOpTracing in production logs warning."""
        from bioetl.composition._bootstrap.observability import (
            validate_observability_preflight,
        )
        from bioetl.infrastructure.observability.noop_tracing import NoOpTracing

        mock_logger = MagicMock()
        mock_metrics = MagicMock()
        noop_tracer = NoOpTracing()

        validate_observability_preflight(
            tracer=noop_tracer,
            metrics=mock_metrics,
            environment="prod",
            logger=mock_logger,
        )

        # Verify warning was logged for NoOpTracing
        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args
        assert call_args[0][0] == "noop_tracing_in_production"
        assert "traces will be lost" in call_args[1]["message"]

    def test_observability_production_warning_noop_metrics(self) -> None:
        """Test that NoOpMetrics in production logs warning."""
        from bioetl.composition._bootstrap.observability import (
            validate_observability_preflight,
        )
        from bioetl.infrastructure.observability.noop_tracing import NoOpTracing

        mock_logger = MagicMock()
        noop_metrics = NoOpMetrics(warn_on_use=False)
        noop_tracer = NoOpTracing()  # Both NoOp to verify both warnings

        validate_observability_preflight(
            tracer=noop_tracer,
            metrics=noop_metrics,
            environment="prod",
            logger=mock_logger,
        )

        # Verify both warnings were logged
        assert mock_logger.warning.call_count == 2
        calls = mock_logger.warning.call_args_list
        event_names = [call[0][0] for call in calls]
        assert "noop_tracing_in_production" in event_names
        assert "noop_metrics_in_production" in event_names

    def test_observability_no_warning_in_dev_environment(self) -> None:
        """Test that NoOp implementations in dev don't log warnings."""
        from bioetl.composition._bootstrap.observability import (
            validate_observability_preflight,
        )
        from bioetl.infrastructure.observability.noop_tracing import NoOpTracing

        mock_logger = MagicMock()
        noop_tracer = NoOpTracing()
        noop_metrics = NoOpMetrics(warn_on_use=False)

        validate_observability_preflight(
            tracer=noop_tracer,
            metrics=noop_metrics,
            environment="dev",
            logger=mock_logger,
        )

        # No warnings should be logged in dev
        mock_logger.warning.assert_not_called()

    def test_observability_no_warning_in_staging_environment(self) -> None:
        """Test that NoOp implementations in staging don't log warnings."""
        from bioetl.composition._bootstrap.observability import (
            validate_observability_preflight,
        )
        from bioetl.infrastructure.observability.noop_tracing import NoOpTracing

        mock_logger = MagicMock()
        noop_tracer = NoOpTracing()
        noop_metrics = NoOpMetrics(warn_on_use=False)

        validate_observability_preflight(
            tracer=noop_tracer,
            metrics=noop_metrics,
            environment="staging",
            logger=mock_logger,
        )

        # No warnings should be logged in staging
        mock_logger.warning.assert_not_called()

    def test_observability_no_warning_with_real_implementations(self) -> None:
        """Test that real implementations don't log warnings in production."""
        from bioetl.composition._bootstrap.observability import (
            validate_observability_preflight,
        )

        mock_logger = MagicMock()
        mock_tracer = MagicMock()  # Not NoOpTracing
        mock_metrics = MagicMock()  # Not NoOpMetrics

        validate_observability_preflight(
            tracer=mock_tracer,
            metrics=mock_metrics,
            environment="prod",
            logger=mock_logger,
        )

        # No warnings for real implementations
        mock_logger.warning.assert_not_called()

    @patch("bioetl.composition._bootstrap.observability.start_metrics_server")
    @patch("bioetl.composition._bootstrap.observability.create_infra_logger")
    def test_bootstrap_observability_calls_preflight_validation(
        self,
        mock_create_logger: MagicMock,
        mock_start_server: MagicMock,
    ) -> None:
        """Test that bootstrap_observability calls preflight validation."""
        from bioetl.composition._bootstrap.observability import bootstrap_observability

        mock_logger = MagicMock()
        mock_create_logger.return_value = mock_logger

        settings = MagicMock()
        settings.env = "prod"
        settings.observability.metrics_enabled = False
        settings.observability.tracing_enabled = False
        settings.observability.dq_monitor_enabled = False

        bootstrap_observability(
            pipeline="test_pipeline",
            run_id=uuid4(),
            settings=settings,
        )

        # Verify preflight validation logged warnings for NoOp implementations
        warning_calls = list(mock_logger.warning.call_args_list)
        event_names = [call[0][0] for call in warning_calls]
        assert "noop_tracing_in_production" in event_names
        assert "noop_metrics_in_production" in event_names
