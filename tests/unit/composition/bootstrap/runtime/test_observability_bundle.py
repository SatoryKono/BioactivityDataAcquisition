"""Unit tests for observability_bundle bootstrap helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from bioetl.composition.observability import (
    ObservabilityBundle,
    ObservabilityContractError,
)
from bioetl.domain.ports.noop import (
    NoOpAudit,
    NoOpMetrics,
    NoOpTracing,
)
from bioetl.infrastructure.observability.noop_logger import NoOpLogger

_FIXED_UUID = UUID("abcdef01-2345-6789-abcd-ef0123456789")


def _settings(env: str = "dev", *, allow_noop: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        env=env,
        observability=SimpleNamespace(
            allow_noop_observability_in_prod=allow_noop,
        ),
        pipeline=SimpleNamespace(
            control_plane=SimpleNamespace(
                required_persistence_profile="degraded_observable",
                run_manifest_enabled=True,
                run_ledger_enabled=True,
            )
        ),
    )


@pytest.mark.unit
class TestValidateObservabilityPreflightImpl:
    """Tests for validate_observability_preflight_impl."""

    def test_noop_tracing_warns_and_fails_closed_in_prod(self) -> None:
        from bioetl.composition.bootstrap.runtime.observability_bundle import (
            validate_observability_preflight_impl,
        )

        logger = MagicMock()
        with pytest.raises(ObservabilityContractError, match="NoOpTracing"):
            validate_observability_preflight_impl(
                tracer=NoOpTracing(),
                metrics=MagicMock(spec=["increment"]),
                environment="prod",
                logger=logger,
            )

        logger.warning.assert_called_once()
        assert logger.warning.call_args[0][0] == "noop_tracing_in_production"

    def test_noop_metrics_warns_and_fails_closed_in_prod(self) -> None:
        from bioetl.composition.bootstrap.runtime.observability_bundle import (
            validate_observability_preflight_impl,
        )

        logger = MagicMock()
        with pytest.raises(ObservabilityContractError, match="NoOpMetrics"):
            validate_observability_preflight_impl(
                tracer=MagicMock(),
                metrics=NoOpMetrics(),
                environment="prod",
                logger=logger,
            )

        logger.warning.assert_called_once()
        assert logger.warning.call_args[0][0] == "noop_metrics_in_production"

    def test_noop_implementations_only_warn_when_override_enabled(self) -> None:
        from bioetl.composition.bootstrap.runtime.observability_bundle import (
            validate_observability_preflight_impl,
        )

        logger = MagicMock()
        validate_observability_preflight_impl(
            tracer=NoOpTracing(),
            metrics=NoOpMetrics(),
            environment="prod",
            logger=logger,
            allow_noop_in_prod=True,
        )

        event_names = [call[0][0] for call in logger.warning.call_args_list]
        assert "noop_tracing_in_production" in event_names
        assert "noop_metrics_in_production" in event_names

    def test_noop_audit_warns_and_fails_closed_in_prod(self) -> None:
        from bioetl.composition.bootstrap.runtime.observability_bundle import (
            validate_observability_preflight_impl,
        )

        logger = MagicMock()
        with pytest.raises(ObservabilityContractError, match="NoOpAudit"):
            validate_observability_preflight_impl(
                tracer=MagicMock(),
                metrics=MagicMock(),
                environment="prod",
                logger=logger,
                audit=NoOpAudit(),
                audit_required=True,
            )

        assert logger.warning.call_args[0][0] == "noop_audit_in_production"

    def test_noop_logger_fails_closed_in_prod(self) -> None:
        from bioetl.composition.bootstrap.runtime.observability_bundle import (
            validate_observability_preflight_impl,
        )

        with pytest.raises(ObservabilityContractError, match="NoOpLogger"):
            validate_observability_preflight_impl(
                tracer=MagicMock(),
                metrics=MagicMock(),
                environment="prod",
                logger=NoOpLogger(),
            )

    def test_control_plane_failure_reuses_runner_builder_invariants(self) -> None:
        from bioetl.composition.bootstrap.runtime.observability_bundle import (
            validate_observability_preflight_impl,
        )

        logger = MagicMock()
        with pytest.raises(
            ObservabilityContractError,
            match="metadata sidecars / lineage persistence for active layers",
        ):
            validate_observability_preflight_impl(
                tracer=MagicMock(),
                metrics=MagicMock(),
                environment="prod",
                logger=logger,
                audit=MagicMock(),
                control_plane=SimpleNamespace(
                    required_persistence_profile="forensic_grade",
                    run_manifest_enabled=True,
                    run_ledger_enabled=True,
                ),
                yaml_config=SimpleNamespace(
                    sink={
                        "bronze": SimpleNamespace(enabled=True, save_metadata=False),
                        "silver": SimpleNamespace(enabled=True, save_metadata=True),
                        "gold": SimpleNamespace(enabled=True, save_metadata=False),
                    }
                ),
            )

        assert (
            logger.warning.call_args[0][0] == "control_plane_readiness_preflight_failed"
        )

    def test_forensic_grade_run_fails_closed_without_observability_evidence(
        self,
    ) -> None:
        from bioetl.composition.bootstrap.runtime.observability_bundle import (
            validate_observability_preflight_impl,
        )

        logger = MagicMock()
        with pytest.raises(
            ObservabilityContractError,
            match="forensic_grade runs require non-noop observability evidence",
        ):
            validate_observability_preflight_impl(
                tracer=NoOpTracing(),
                metrics=NoOpMetrics(),
                environment="staging",
                logger=logger,
                audit=NoOpAudit(),
                control_plane=SimpleNamespace(
                    required_persistence_profile="forensic_grade",
                    run_manifest_enabled=True,
                    run_ledger_enabled=True,
                ),
                yaml_config=SimpleNamespace(
                    sink={
                        "bronze": SimpleNamespace(enabled=True, save_metadata=True),
                        "silver": SimpleNamespace(enabled=True, save_metadata=True),
                        "gold": SimpleNamespace(enabled=True, save_metadata=True),
                    }
                ),
            )

        assert (
            logger.warning.call_args[0][0]
            == "forensic_grade_observability_evidence_unavailable"
        )
        assert logger.warning.call_args.kwargs["missing_observability_evidence"] == [
            "tracing",
            "metrics",
            "audit",
        ]

    def test_forensic_grade_run_requires_audit_even_outside_prod(self) -> None:
        from bioetl.composition.bootstrap.runtime.observability_bundle import (
            validate_observability_preflight_impl,
        )

        logger = MagicMock()
        with pytest.raises(ObservabilityContractError, match="missing: audit"):
            validate_observability_preflight_impl(
                tracer=MagicMock(),
                metrics=MagicMock(),
                environment="dev",
                logger=logger,
                audit=None,
                control_plane=SimpleNamespace(
                    required_persistence_profile="forensic_grade",
                    run_manifest_enabled=True,
                    run_ledger_enabled=True,
                ),
                yaml_config=SimpleNamespace(
                    sink={
                        "bronze": SimpleNamespace(enabled=True, save_metadata=True),
                        "silver": SimpleNamespace(enabled=True, save_metadata=True),
                        "gold": SimpleNamespace(enabled=True, save_metadata=True),
                    }
                ),
            )

    def test_forensic_grade_run_ignores_allow_noop_override_and_still_fails_closed(
        self,
    ) -> None:
        from bioetl.composition.bootstrap.runtime.observability_bundle import (
            validate_observability_preflight_impl,
        )

        logger = MagicMock()
        with pytest.raises(
            ObservabilityContractError,
            match="forensic_grade runs require non-noop observability evidence",
        ):
            validate_observability_preflight_impl(
                tracer=NoOpTracing(),
                metrics=NoOpMetrics(),
                environment="prod",
                logger=logger,
                allow_noop_in_prod=True,
                audit=NoOpAudit(),
                control_plane=SimpleNamespace(
                    required_persistence_profile="forensic_grade",
                    run_manifest_enabled=True,
                    run_ledger_enabled=True,
                ),
                yaml_config=SimpleNamespace(
                    sink={
                        "bronze": SimpleNamespace(enabled=True, save_metadata=True),
                        "silver": SimpleNamespace(enabled=True, save_metadata=True),
                        "gold": SimpleNamespace(enabled=True, save_metadata=True),
                    }
                ),
            )

        warning_events = [call.args[0] for call in logger.warning.call_args_list]
        assert "forensic_grade_observability_evidence_unavailable" in warning_events

    def test_forensic_grade_run_passes_with_evidence_and_lineage_sidecars(
        self,
    ) -> None:
        from bioetl.composition.bootstrap.runtime.observability_bundle import (
            validate_observability_preflight_impl,
        )

        logger = MagicMock()
        validate_observability_preflight_impl(
            tracer=MagicMock(),
            metrics=MagicMock(),
            environment="staging",
            logger=logger,
            audit=MagicMock(),
            control_plane=SimpleNamespace(
                required_persistence_profile="forensic_grade",
                run_manifest_enabled=True,
                run_ledger_enabled=True,
            ),
            yaml_config=SimpleNamespace(
                sink={
                    "bronze": SimpleNamespace(enabled=True, save_metadata=True),
                    "silver": SimpleNamespace(enabled=True, save_metadata=True),
                    "gold": SimpleNamespace(enabled=True, save_metadata=True),
                }
            ),
        )

        logger.warning.assert_not_called()

    def test_non_prod_environment_silent(self) -> None:
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
        from bioetl.composition.bootstrap.runtime.observability_bundle import (
            bootstrap_observability_bundle_impl,
        )

        logger = MagicMock()
        tracer = MagicMock()
        metrics = MagicMock()
        audit = MagicMock()
        dq_monitor = MagicMock()

        bundle = bootstrap_observability_bundle_impl(
            pipeline="test_pipe",
            run_id=_FIXED_UUID,
            settings=_settings(),
            log_level="INFO",
            logger_bootstrapper=lambda _p, _r, _l: logger,
            tracer_bootstrapper=lambda _s: tracer,
            metrics_bootstrapper=lambda _s: metrics,
            audit_bootstrapper=lambda _s, _l, _m, _t: audit,
            dq_monitor_bootstrapper=lambda _s, _lg: dq_monitor,
            preflight_validator=MagicMock(),
        )

        assert isinstance(bundle, ObservabilityBundle)
        assert bundle.logger is logger
        assert bundle.tracer is tracer
        assert bundle.metrics is metrics
        assert bundle.dq_monitor is dq_monitor

    def test_calls_preflight_validator_with_allow_flag(self) -> None:
        from bioetl.composition.bootstrap.runtime.observability_bundle import (
            bootstrap_observability_bundle_impl,
        )

        tracer = MagicMock()
        metrics = MagicMock()
        logger = MagicMock()
        audit = MagicMock()
        preflight = MagicMock()
        settings = _settings(env="prod", allow_noop=True)

        bootstrap_observability_bundle_impl(
            pipeline="p",
            run_id=_FIXED_UUID,
            settings=settings,
            log_level="DEBUG",
            logger_bootstrapper=lambda _p, _r, _l: logger,
            tracer_bootstrapper=lambda _s: tracer,
            metrics_bootstrapper=lambda _s: metrics,
            audit_bootstrapper=lambda _s, _l, _m, _t: audit,
            dq_monitor_bootstrapper=lambda _s, _lg: None,
            preflight_validator=preflight,
        )

        assert preflight.call_count == 1
        kwargs = preflight.call_args.kwargs
        assert kwargs["tracer"] is tracer
        assert kwargs["metrics"] is metrics
        assert kwargs["environment"] == "prod"
        assert kwargs["logger"] is logger
        assert kwargs["allow_noop_in_prod"] is True
        assert kwargs["audit"] is audit
        assert kwargs["audit_required"] is False

    def test_logs_observability_initialized_with_flat_context(self) -> None:
        from bioetl.composition.bootstrap.runtime.observability_bundle import (
            bootstrap_observability_bundle_impl,
        )

        logger = MagicMock()
        audit = NoOpAudit()

        bootstrap_observability_bundle_impl(
            pipeline="p",
            run_id=_FIXED_UUID,
            settings=_settings(),
            log_level="INFO",
            logger_bootstrapper=lambda _p, _r, _l: logger,
            tracer_bootstrapper=lambda _s: MagicMock(),
            metrics_bootstrapper=lambda _s: MagicMock(),
            audit_bootstrapper=lambda _s, _l, _m, _t: audit,
            dq_monitor_bootstrapper=lambda _s, _lg: None,
            preflight_validator=MagicMock(),
        )

        logger.info.assert_called_once_with(
            "observability_initialized",
            stage="bootstrap",
            logger_type="MagicMock",
            metrics_type="MagicMock",
            tracer_type="MagicMock",
            audit_type="NoOpAudit",
            audit_enabled=False,
            dq_monitor_enabled=False,
            required_persistence_profile="degraded_observable",
            run_manifest_enabled=True,
            run_ledger_enabled=True,
            preflight_status="passed",
        )

    def test_emits_runtime_status_gauges_for_all_observability_components(self) -> None:
        from bioetl.composition.bootstrap.runtime.observability_bundle import (
            bootstrap_observability_bundle_impl,
        )

        logger = MagicMock()
        metrics = MagicMock()

        bootstrap_observability_bundle_impl(
            pipeline="p",
            run_id=_FIXED_UUID,
            settings=_settings(),
            log_level="INFO",
            logger_bootstrapper=lambda _p, _r, _l: logger,
            tracer_bootstrapper=lambda _s: NoOpTracing(),
            metrics_bootstrapper=lambda _s: metrics,
            audit_bootstrapper=lambda _s, _l, _m, _t: NoOpAudit(),
            dq_monitor_bootstrapper=lambda _s, _lg: None,
            preflight_validator=MagicMock(),
        )

        metrics.set_gauge.assert_any_call(
            "bioetl_observability_runtime_status",
            1.0,
            {"pipeline": "unknown", "component": "logger", "mode": "active"},
        )
        metrics.set_gauge.assert_any_call(
            "bioetl_observability_runtime_status",
            1.0,
            {"pipeline": "unknown", "component": "metrics", "mode": "active"},
        )
        metrics.set_gauge.assert_any_call(
            "bioetl_observability_runtime_status",
            1.0,
            {"pipeline": "unknown", "component": "tracing", "mode": "noop"},
        )
        metrics.set_gauge.assert_any_call(
            "bioetl_observability_runtime_status",
            1.0,
            {"pipeline": "unknown", "component": "audit", "mode": "noop"},
        )
        metrics.set_gauge.assert_any_call(
            "bioetl_observability_runtime_status",
            1.0,
            {"pipeline": "unknown", "component": "dq_monitor", "mode": "disabled"},
        )

    def test_emits_noop_logger_runtime_status_gauge(self) -> None:
        from bioetl.composition.bootstrap.runtime.observability_bundle import (
            _log_observability_initialized,
        )

        metrics = MagicMock()

        _log_observability_initialized(
            logger=NoOpLogger(),
            metrics=metrics,
            tracer=NoOpTracing(),
            audit=NoOpAudit(),
            dq_monitor=None,
            control_plane=None,
        )

        metrics.set_gauge.assert_any_call(
            "bioetl_observability_runtime_status",
            1.0,
            {"pipeline": "unknown", "component": "logger", "mode": "noop"},
        )
