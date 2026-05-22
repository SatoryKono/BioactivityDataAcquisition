"""Unit tests for canonical observability bundle construction."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from bioetl.composition.runtime_builders import observability_builder


@pytest.mark.unit
def test_canonical_observability_builder_uses_noop_when_disabled() -> None:
    logger, tracer, metrics = MagicMock(), MagicMock(), MagicMock()
    logger_factory = MagicMock(return_value=logger)
    noop_tracing_factory = MagicMock(return_value=tracer)
    noop_metrics_factory = MagicMock(return_value=metrics)

    obs = SimpleNamespace(
        tracing_enabled=False,
        metrics_enabled=False,
        dq_monitor_enabled=False,
        allow_noop_observability_in_prod=False,
        audit_enabled=False,
    )
    result = observability_builder.build_observability_bundle(
        pipeline="chembl_activity",
        run_id=uuid4(),
        settings=SimpleNamespace(env="dev", observability=obs),
        logger_factory=logger_factory,
        noop_tracing_factory=noop_tracing_factory,
        noop_metrics_factory=noop_metrics_factory,
    )

    assert result.logger is logger
    assert result.tracer is tracer
    assert result.metrics is metrics
    assert result.dq_monitor is None
    noop_metrics_factory.assert_called_once_with(warn_on_use=False)


@pytest.mark.unit
def test_canonical_observability_builder_configures_dq_monitor_thresholds() -> None:
    logger, tracer, metrics, dq_monitor = (
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
    )
    logger_factory = MagicMock(return_value=logger)
    tracer_factory = MagicMock(return_value=tracer)
    metrics_factory = MagicMock(return_value=metrics)
    dq_monitor_factory = MagicMock(return_value=dq_monitor)

    obs_settings = SimpleNamespace(
        tracing_enabled=True,
        metrics_enabled=True,
        dq_monitor_enabled=True,
        dq_baseline_window=20,
        dq_z_score_threshold=2.5,
        dq_min_baseline_samples=12,
        dq_error_rate_max=0.3,
        dq_quality_score_min=0.7,
        allow_noop_observability_in_prod=False,
        audit_enabled=False,
    )
    settings = SimpleNamespace(env="dev", observability=obs_settings)

    result = observability_builder.build_observability_bundle(
        pipeline="chembl_activity",
        run_id=uuid4(),
        settings=settings,
        logger_factory=logger_factory,
        tracer_factory=tracer_factory,
        metrics_factory=metrics_factory,
        dq_monitor_factory=dq_monitor_factory,
    )

    assert result.logger is logger
    assert result.tracer is tracer
    assert result.metrics is metrics
    assert result.dq_monitor is dq_monitor
    assert dq_monitor.detector.min_baseline_samples == 12
    assert dq_monitor.detector.set_threshold.call_count == 2
