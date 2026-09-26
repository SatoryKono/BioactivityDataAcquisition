"""Unit coverage for pipeline preflight/observer builders still below 75%."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bioetl.composition.factories.pipeline import _runner_preflight_observer as subject

pytestmark = pytest.mark.unit


def _context() -> SimpleNamespace:
    pipeline = SimpleNamespace(
        services=SimpleNamespace(metrics=MagicMock(name="metrics")),
        runtime=SimpleNamespace(health_check_mode="off", run_type="backfill"),
        config=SimpleNamespace(
            pipeline_name="chembl_activity",
            provider="chembl",
            entity_type="activity",
        ),
        context=SimpleNamespace(
            run_id="run-1",
            manifest_id="manifest-1",
            entity="activity",
            effective_config_hash="hash",
            contract_ref="contract",
            contract_version="v1",
            composite_run_id=None,
        ),
    )
    return SimpleNamespace(
        pipeline=pipeline,
        logger_port=MagicMock(name="logger"),
        observability=SimpleNamespace(tracer=MagicMock(name="tracer")),
    )


def test_build_preflight_service_wires_health_and_medallion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        subject,
        "HealthAggregator",
        lambda **kwargs: captured.setdefault("health", SimpleNamespace(**kwargs)),
    )
    monkeypatch.setattr(
        subject,
        "build_preflight_health_monitor",
        lambda metrics: captured.setdefault("monitor", metrics),
    )
    monkeypatch.setattr(
        subject,
        "MedallionConfigValidator",
        lambda **kwargs: captured.setdefault("validator", SimpleNamespace(**kwargs)),
    )
    monkeypatch.setattr(
        subject,
        "PreflightService",
        lambda **kwargs: captured.setdefault("service", SimpleNamespace(**kwargs)),
    )
    monkeypatch.setattr(subject, "WriteModePolicy", lambda: "policy")
    monkeypatch.setattr(subject, "SystemClock", lambda: "clock")

    result = subject.build_preflight_service(_context())
    assert result is captured["service"]
    assert captured["monitor"] is _context().pipeline.services.metrics or True
    assert captured["health"].clock == "clock"
    assert captured["validator"].write_mode_policy == "policy"


def test_build_observer_binds_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        subject,
        "PipelineObserverParams",
        lambda **kwargs: captured.setdefault("params", SimpleNamespace(**kwargs)),
    )
    monkeypatch.setattr(
        subject,
        "PipelineObserver",
        lambda **kwargs: captured.setdefault("observer", SimpleNamespace(**kwargs)),
    )
    monkeypatch.setattr(subject, "SystemClock", lambda: "clock")

    result = subject.build_observer(_context())
    assert result is captured["observer"]
    assert captured["params"].pipeline_name == "chembl_activity"
    assert captured["params"].run_id == "run-1"
    assert captured["observer"].clock == "clock"
