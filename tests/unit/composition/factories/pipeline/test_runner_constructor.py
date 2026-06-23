"""Unit tests for the final PipelineRunner constructor payload."""

from __future__ import annotations

import pytest

from types import SimpleNamespace
from unittest.mock import MagicMock

from bioetl.application.core.wiring.factory import PipelineRunnerDependencies
from bioetl.composition.factories.pipeline import runner_constructor


pytestmark = pytest.mark.unit


def test_create_pipeline_runner_uses_grouped_dependency_bundle(monkeypatch) -> None:
    """Composition must call PipelineRunner with typed grouped dependencies."""
    captured: dict[str, object] = {}
    tracer = MagicMock(name="tracer")

    def _fake_pipeline_runner(**kwargs: object) -> object:
        captured.update(kwargs)
        return SimpleNamespace(name="runner")

    monkeypatch.setattr(runner_constructor, "resolve_tracer", lambda value: value)
    monkeypatch.setattr(
        runner_constructor,
        "PipelineRunner",
        _fake_pipeline_runner,
    )

    pipeline = SimpleNamespace(
        config=MagicMock(name="config"),
        runtime=MagicMock(name="runtime"),
        services=MagicMock(name="services"),
        context=MagicMock(name="context"),
        shutdown_signal=MagicMock(name="shutdown_signal"),
    )
    observability = SimpleNamespace(tracer=tracer)
    executor = MagicMock(name="executor")
    checkpoint_manager = MagicMock(name="checkpoint_manager")
    lock_runtime_service = MagicMock(name="lock_runtime_service")
    preflight_service = MagicMock(name="preflight_service")
    postrun_service = MagicMock(name="postrun_service")
    lifecycle_service = MagicMock(name="lifecycle_service")
    observer = MagicMock(name="observer")

    result = runner_constructor.create_pipeline_runner(
        pipeline=pipeline,
        observability=observability,
        executor=executor,
        checkpoint_manager=checkpoint_manager,
        lock_runtime_service=lock_runtime_service,
        preflight_service=preflight_service,
        postrun_service=postrun_service,
        lifecycle_service=lifecycle_service,
        observer=observer,
    )

    assert result == SimpleNamespace(name="runner")
    dependencies = captured["dependencies"]
    assert isinstance(dependencies, PipelineRunnerDependencies)
    assert dependencies.executor is executor
    assert dependencies.checkpoint_manager is checkpoint_manager
    assert dependencies.lock_runtime_service is lock_runtime_service
    assert dependencies.preflight is preflight_service
    assert dependencies.postrun is postrun_service
    assert dependencies.lifecycle_service is lifecycle_service
    assert dependencies.observer is observer
    assert dependencies.shutdown_signal is pipeline.shutdown_signal
    assert captured["tracer"] is tracer
    assert "executor" not in captured
    assert "checkpoint_manager" not in captured
    assert "lock_manager" not in captured
    assert "preflight" not in captured
    assert "postrun" not in captured
    assert "lifecycle_service" not in captured
    assert "observer" not in captured
