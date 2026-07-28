"""ARCH-CR-06: PipelineObserver identity bag + from_parts compatibility."""

from __future__ import annotations

from types import SimpleNamespace

from bioetl.application.observability.observer import (
    PipelineObserver,
    PipelineObserverIdentity,
)
from bioetl.domain.types import RunID, RunType


def _ports() -> tuple[SimpleNamespace, SimpleNamespace, SimpleNamespace]:
    metrics = SimpleNamespace()
    logger = SimpleNamespace()
    clock = SimpleNamespace()
    return metrics, logger, clock


def test_pipeline_observer_from_identity_bag() -> None:
    metrics, logger, clock = _ports()
    identity = PipelineObserverIdentity(
        pipeline_name="chembl_activity",
        run_id=RunID("run-1"),
        run_type=RunType.INCREMENTAL,
        manifest_id="m-1",
        entity="activity",
    )
    observer = PipelineObserver(
        identity=identity,
        metrics=metrics,  # type: ignore[arg-type]
        logger=logger,  # type: ignore[arg-type]
        clock=clock,  # type: ignore[arg-type]
    )
    assert observer.pipeline_name == "chembl_activity"
    assert observer.run_id == "run-1"
    assert observer.entity == "activity"
    assert observer.manifest_id == "m-1"


def test_pipeline_observer_from_parts_compat_factory() -> None:
    metrics, logger, clock = _ports()
    observer = PipelineObserver.from_parts(
        pipeline_name="chembl_target",
        run_id=RunID("run-2"),
        run_type=RunType.REBUILD,
        metrics=metrics,  # type: ignore[arg-type]
        logger=logger,  # type: ignore[arg-type]
        clock=clock,  # type: ignore[arg-type]
        entity="target",
    )
    assert observer.pipeline_name == "chembl_target"
    assert observer.run_id == "run-2"
    assert observer.run_type == RunType.REBUILD.value
    assert observer.entity == "target"
