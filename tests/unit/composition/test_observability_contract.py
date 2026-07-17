"""Tests for Unified Observability Contract.

Verifies that:
1. ObservabilityBundle enforces required components (logger, metrics)
2. bootstrap_observability_bundle() always returns valid implementations
3. NoOpMetrics is used as fallback when Prometheus disabled
4. Pipeline cannot run without valid logger
5. Health-check metrics are properly recorded
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from tests.helpers.deterministic_ids import deterministic_uuid_from_callsite

import pytest

from bioetl.composition.observability import (
    ObservabilityBundle,
    ObservabilityContractError,
)
from bioetl.domain.ports.noop import NoOpAudit, NoOpMetrics, NoOpTracing
from tests.helpers.deterministic_ids import deterministic_uuid
from tests.helpers.git_index_scan import git_grep_fixed

pytestmark = pytest.mark.unit


@pytest.mark.unit
class TestObservabilityBundle:
    """Tests for ObservabilityBundle contract enforcement."""

    def test_bundle_requires_logger(self) -> None:
        """Test that bundle creation fails without logger."""
        mock_metrics = MagicMock()
        tracer = NoOpTracing()

        with pytest.raises(ObservabilityContractError, match="Logger is required"):
            ObservabilityBundle(
                logger=None,
                metrics=mock_metrics,
                tracer=tracer,
                audit=NoOpAudit(),
            )  # type: ignore[arg-type]

    def test_bundle_requires_metrics(self) -> None:
        """Test that bundle creation fails without metrics."""
        mock_logger = MagicMock()
        tracer = NoOpTracing()

        with pytest.raises(
            ObservabilityContractError, match="Metrics port is required"
        ):
            ObservabilityBundle(
                logger=mock_logger,
                metrics=None,
                tracer=tracer,
                audit=NoOpAudit(),
            )  # type: ignore[arg-type]

    def test_bundle_requires_tracer(self) -> None:
        """Test that tracer must be explicit even when tracing is disabled."""
        mock_logger = MagicMock()
        mock_metrics = MagicMock()

        with pytest.raises(ObservabilityContractError, match="Tracer is required"):
            ObservabilityBundle(
                logger=mock_logger,
                metrics=mock_metrics,
                tracer=None,  # type: ignore[arg-type]
                audit=NoOpAudit(),
                dq_monitor=None,
            )

    def test_bundle_requires_audit(self) -> None:
        """Test that audit must be explicit even when audit is disabled."""
        mock_logger = MagicMock()
        mock_metrics = MagicMock()

        with pytest.raises(ObservabilityContractError, match="Audit port is required"):
            ObservabilityBundle(
                logger=mock_logger,
                metrics=mock_metrics,
                tracer=NoOpTracing(),
                audit=None,  # type: ignore[arg-type]
            )

    def test_bundle_create_factory_method(self) -> None:
        """Test factory method enforces contract."""
        mock_logger = MagicMock()
        mock_metrics = MagicMock()
        mock_tracer = MagicMock()

        bundle = ObservabilityBundle.create(
            logger=mock_logger,
            metrics=mock_metrics,
            tracer=mock_tracer,
            audit=NoOpAudit(),
        )

        assert bundle.logger is mock_logger
        assert bundle.metrics is mock_metrics
        assert bundle.tracer is mock_tracer
        assert isinstance(bundle.audit, NoOpAudit)

    def test_bundle_bind_preserves_metrics(self) -> None:
        """Test that bind() preserves metrics reference."""
        mock_logger = MagicMock()
        mock_logger.bind.return_value = MagicMock()
        mock_metrics = MagicMock()
        tracer = NoOpTracing()

        bundle = ObservabilityBundle(
            logger=mock_logger,
            metrics=mock_metrics,
            tracer=tracer,
            audit=NoOpAudit(),
        )
        new_bundle = bundle.bind(run_id="test-123")

        assert new_bundle.metrics is mock_metrics
        assert new_bundle.tracer is tracer
        assert new_bundle.audit is bundle.audit

    def test_bundle_frozen(self) -> None:
        """Test that bundle is frozen (immutable)."""
        mock_logger = MagicMock()
        mock_metrics = MagicMock()
        tracer = NoOpTracing()

        bundle = ObservabilityBundle(
            logger=mock_logger,
            metrics=mock_metrics,
            tracer=tracer,
            audit=NoOpAudit(),
        )

        with pytest.raises(FrozenInstanceError):
            bundle.metrics = MagicMock()  # type: ignore[misc]


@pytest.mark.unit
class TestBootstrapObservability:
    """Tests for bootstrap_observability_bundle() function."""

    @patch(
        "bioetl.composition.bootstrap.runtime.metrics_bootstrap._default_metrics_factory"
    )
    @patch(
        "bioetl.composition.bootstrap.runtime.logger_bootstrap._default_logger_factory"
    )
    def test_bootstrap_returns_valid_bundle(
        self,
        mock_logger_factory: MagicMock,
        mock_metrics_factory: MagicMock,
    ) -> None:
        """Test that bootstrap returns bundle with valid implementations."""
        from bioetl.composition.bootstrap.runtime.observability import (
            bootstrap_observability_bundle,
        )

        # Setup mocks
        mock_logger = MagicMock()
        mock_logger.info = MagicMock()
        mock_logger_factory.return_value = mock_logger
        mock_metrics = MagicMock()
        mock_metrics_factory.return_value = mock_metrics

        settings = MagicMock()
        settings.metrics_port = 8000
        settings.observability.metrics_enabled = True
        settings.observability.metrics_server_enabled = False
        settings.observability.tracing_enabled = False
        settings.observability.dq_monitor_enabled = False
        settings.observability.allow_noop_observability_in_prod = False
        settings.observability.audit_enabled = False
        settings.pipeline.control_plane.required_persistence_profile = (
            "degraded_observable"
        )
        settings.pipeline.control_plane.run_manifest_enabled = True
        settings.pipeline.control_plane.run_ledger_enabled = True

        bundle = bootstrap_observability_bundle(
            pipeline="test_pipeline",
            run_id=deterministic_uuid("observability-contract:metrics-enabled"),
            settings=settings,
        )

        assert bundle.logger is mock_logger
        assert bundle.metrics is mock_metrics
        assert bundle.tracer is not None  # NoOpTracing
        assert bundle.dq_monitor is None

    @patch(
        "bioetl.composition.bootstrap.runtime.logger_bootstrap._default_logger_factory"
    )
    def test_bootstrap_uses_noop_metrics_when_disabled(
        self,
        mock_logger_factory: MagicMock,
    ) -> None:
        """Test that NoOpMetrics is used when metrics disabled."""
        from bioetl.composition.bootstrap.runtime.observability import (
            bootstrap_observability_bundle,
        )

        mock_logger = MagicMock()
        mock_logger.info = MagicMock()
        mock_logger_factory.return_value = mock_logger

        settings = MagicMock()
        settings.observability.metrics_enabled = False
        settings.observability.tracing_enabled = False
        settings.observability.dq_monitor_enabled = False
        settings.observability.allow_noop_observability_in_prod = False
        settings.observability.audit_enabled = False
        settings.pipeline.control_plane.required_persistence_profile = (
            "degraded_observable"
        )
        settings.pipeline.control_plane.run_manifest_enabled = True
        settings.pipeline.control_plane.run_ledger_enabled = True

        bundle = bootstrap_observability_bundle(
            pipeline="test_pipeline",
            run_id=deterministic_uuid_from_callsite("test_observability_contract"),
            settings=settings,
        )

        assert isinstance(bundle.metrics, NoOpMetrics)

    @patch(
        "bioetl.composition.bootstrap.runtime.logger_bootstrap._default_logger_factory"
    )
    def test_bootstrap_logs_initialization_status(
        self,
        mock_logger_factory: MagicMock,
    ) -> None:
        """Test that bootstrap logs observability initialization."""
        from bioetl.composition.bootstrap.runtime.observability import (
            bootstrap_observability_bundle,
        )

        mock_logger = MagicMock()
        mock_logger_factory.return_value = mock_logger

        settings = MagicMock()
        settings.observability.metrics_enabled = False
        settings.observability.tracing_enabled = False
        settings.observability.dq_monitor_enabled = False
        settings.observability.allow_noop_observability_in_prod = False
        settings.observability.audit_enabled = False
        settings.pipeline.control_plane.required_persistence_profile = (
            "degraded_observable"
        )
        settings.pipeline.control_plane.run_manifest_enabled = True
        settings.pipeline.control_plane.run_ledger_enabled = True

        bootstrap_observability_bundle(
            pipeline="test_pipeline",
            run_id=deterministic_uuid_from_callsite("test_observability_contract"),
            settings=settings,
        )

        # Verify initialization was logged
        mock_logger.info.assert_called_with(
            "observability_initialized",
            stage="bootstrap",
            logger_type="MagicMock",
            metrics_type="NoOpMetrics",
            tracer_type="NoOpTracing",
            audit_type="NoOpAudit",
            audit_enabled=False,
            dq_monitor_enabled=False,
            configured_required_persistence_profile="degraded_observable",
            run_manifest_enabled=True,
            run_ledger_enabled=True,
            preflight_status="passed",
        )

    def test_application_and_composition_logging_avoid_nested_extra_payloads(
        self,
    ) -> None:
        """Application and composition code should use flat LoggerPort kwargs."""
        repo_root = Path(__file__).resolve().parents[3]
        source_paths = (
            "src/bioetl/application",
            "src/bioetl/composition",
        )

        matches = git_grep_fixed(
            root=repo_root,
            patterns=("extra=",),
            paths=source_paths,
            suffixes=(".py",),
        )

        offenders = sorted({match.path for match in matches})
        # Exclude _pipeline_execution.py which uses grouping_key_extra parameter (not LoggerPort extra)
        offenders = [f for f in offenders if f != "src/bioetl/composition/_pipeline_execution.py"]
        assert offenders == [], (
            "Nested LoggerPort extra payloads are forbidden in application/"
            f"composition. Offenders: {offenders}"
        )


@pytest.mark.unit
class TestBootstrapMetrics:
    """Tests for bootstrap_metrics() function."""

    def test_disabled_metrics_returns_noop_metrics(self) -> None:
        """Test that disabled metrics returns NoOpMetrics, not None."""
        from bioetl.composition.bootstrap.runtime.observability import (
            bootstrap_metrics,
        )

        settings = MagicMock()
        settings.observability.metrics_enabled = False

        result = bootstrap_metrics(settings)

        assert result is not None
        assert isinstance(result, NoOpMetrics)

    def test_noop_metrics_no_warning_when_disabled(self) -> None:
        """Test that NoOpMetrics doesn't warn when explicitly disabled."""
        from bioetl.composition.bootstrap.runtime.observability import (
            bootstrap_metrics,
        )

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

    @patch(
        "bioetl.composition.bootstrap.runtime.metrics_bootstrap._default_metrics_factory"
    )
    def test_enabled_metrics_returns_prometheus_metrics(
        self,
        mock_metrics_factory: MagicMock,
    ) -> None:
        """Test that enabled metrics returns PrometheusMetrics."""
        from bioetl.composition.bootstrap.runtime.observability import (
            bootstrap_metrics,
        )

        mock_metrics = MagicMock()
        mock_metrics_factory.return_value = mock_metrics

        settings = MagicMock()
        settings.metrics_port = 8000
        settings.observability.metrics_enabled = True
        settings.observability.metrics_server_enabled = False

        result = bootstrap_metrics(settings)

        assert result is mock_metrics
        mock_metrics_factory.assert_called_once()


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
        assert INFRASTRUCTURE_VALIDATED._labelnames == ("pipeline",)


@pytest.mark.unit
class TestObservabilityPreflightValidation:
    """Tests for observability preflight validation.

    Verifies that NoOp implementations in production trigger warnings
    to prevent silent data loss.
    """

    def test_observability_production_warning_noop_tracing(self) -> None:
        """Test that NoOpTracing in production logs warning and fails closed."""
        from bioetl.composition.bootstrap.runtime.observability import (
            validate_observability_preflight,
        )
        from bioetl.composition.observability import ObservabilityContractError
        from bioetl.domain.ports.noop import NoOpTracing

        mock_logger = MagicMock()
        mock_metrics = MagicMock()
        noop_tracer = NoOpTracing()

        with pytest.raises(ObservabilityContractError, match="NoOpTracing"):
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
        """Test that NoOp implementations only warn when explicit override is enabled."""
        from bioetl.composition.bootstrap.runtime.observability import (
            validate_observability_preflight,
        )
        from bioetl.domain.ports.noop import NoOpTracing

        mock_logger = MagicMock()
        noop_metrics = NoOpMetrics(warn_on_use=False)
        noop_tracer = NoOpTracing()  # Both NoOp to verify both warnings

        validate_observability_preflight(
            tracer=noop_tracer,
            metrics=noop_metrics,
            environment="prod",
            logger=mock_logger,
            allow_noop_in_prod=True,
            control_plane=SimpleNamespace(
                required_persistence_profile="degraded_observable",
                run_manifest_enabled=True,
                run_ledger_enabled=True,
            ),
        )

        # Verify both warnings were logged
        assert mock_logger.warning.call_count == 2
        calls = mock_logger.warning.call_args_list
        event_names = [call[0][0] for call in calls]
        assert "noop_tracing_in_production" in event_names
        assert "noop_metrics_in_production" in event_names

    def test_observability_no_warning_in_dev_environment(self) -> None:
        """Test that NoOp implementations in dev don't log warnings."""
        from bioetl.composition.bootstrap.runtime.observability import (
            validate_observability_preflight,
        )
        from bioetl.domain.ports.noop import NoOpTracing

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
        from bioetl.composition.bootstrap.runtime.observability import (
            validate_observability_preflight,
        )
        from bioetl.domain.ports.noop import NoOpTracing

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
        from bioetl.composition.bootstrap.runtime.observability import (
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
            control_plane=SimpleNamespace(
                required_persistence_profile="degraded_observable",
                run_manifest_enabled=True,
                run_ledger_enabled=True,
            ),
        )

        # No warnings for real implementations
        mock_logger.warning.assert_not_called()

    @patch(
        "bioetl.composition.bootstrap.runtime.logger_bootstrap._default_logger_factory"
    )
    def test_bootstrap_observability_bundle_calls_preflight_validation(
        self,
        mock_logger_factory: MagicMock,
    ) -> None:
        """Test that bootstrap_observability_bundle calls preflight validation."""
        from bioetl.composition.bootstrap.runtime.observability import (
            bootstrap_observability_bundle,
        )

        mock_logger = MagicMock()
        mock_logger_factory.return_value = mock_logger

        settings = MagicMock()
        settings.env = "prod"
        settings.observability.metrics_enabled = False
        settings.observability.tracing_enabled = False
        settings.observability.dq_monitor_enabled = False
        settings.observability.allow_noop_observability_in_prod = True
        settings.observability.audit_enabled = False
        settings.pipeline.control_plane.required_persistence_profile = (
            "degraded_observable"
        )
        settings.pipeline.control_plane.run_manifest_enabled = True
        settings.pipeline.control_plane.run_ledger_enabled = True

        bootstrap_observability_bundle(
            pipeline="test_pipeline",
            run_id=deterministic_uuid_from_callsite("test_observability_contract"),
            settings=settings,
        )

        # Verify preflight validation logged warnings for NoOp implementations
        warning_calls = list(mock_logger.warning.call_args_list)
        event_names = [call[0][0] for call in warning_calls]
        assert "noop_tracing_in_production" in event_names
        assert "noop_metrics_in_production" in event_names
