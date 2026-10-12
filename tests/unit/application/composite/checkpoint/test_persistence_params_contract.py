"""Contract tests for composite checkpoint persistence parameters."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import FrozenInstanceError
from typing import cast
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

from bioetl.application.composite.checkpoint.persistence_service import (
    CompositeCheckpointPersistenceParams,
    CompositeCheckpointPersistenceService,
)
from bioetl.application.composite.checkpoint.service import (
    CompositeCheckpointService,
    CompositeCheckpointServiceContext,
)


def _params(**overrides: object) -> CompositeCheckpointPersistenceParams:
    values: dict[str, object] = {
        "composite_name": "activity",
        "checkpoint_filename": "cp.json",
        "glob_pattern": "*.json",
        "storage": MagicMock(),
        "logger": MagicMock(),
    }
    values.update(overrides)
    return CompositeCheckpointPersistenceParams(**values)  # type: ignore[arg-type]


def test_persistence_params_are_frozen_slotted_and_metrics_default_to_none() -> None:
    params = _params()

    assert params.metrics is None
    assert not hasattr(params, "__dict__")
    with pytest.raises(FrozenInstanceError):
        params.metrics = MagicMock()  # pyright: ignore[reportAttributeAccessIssue]


def test_persistence_service_rejects_legacy_keyword_signature() -> None:
    legacy = {
        "composite_name": "activity",
        "checkpoint_filename": "cp.json",
        "glob_pattern": "*.json",
        "storage": MagicMock(),
        "logger": MagicMock(),
    }

    with pytest.raises(TypeError):
        CompositeCheckpointPersistenceService(**legacy)  # type: ignore[arg-type]


def test_custom_factory_receives_persistence_params() -> None:
    captured: list[CompositeCheckpointPersistenceParams] = []

    def factory(
        params: CompositeCheckpointPersistenceParams,
    ) -> CompositeCheckpointPersistenceService:
        captured.append(params)
        return CompositeCheckpointPersistenceService(params)

    metrics = MagicMock()
    CompositeCheckpointService(
        CompositeCheckpointServiceContext(
            composite_name="activity",
            run_id="run-1",
            storage=MagicMock(),
            logger=MagicMock(),
            metrics=metrics,
            persistence_service_factory=factory,
        )
    )

    assert len(captured) == 1
    params = captured[0]
    assert params.composite_name == "activity"
    assert params.checkpoint_filename == "composite_activity_run-1.json"
    assert params.glob_pattern == "composite_activity_*.json"
    assert params.metrics is metrics
    assert params.storage is not None
    assert params.logger is not None


def test_legacy_keyword_factory_is_not_adapted() -> None:
    def legacy_factory(
        *,
        composite_name: str,
        checkpoint_filename: str,
        glob_pattern: str,
        storage: object,
        logger: object,
        metrics: object | None = None,
    ) -> CompositeCheckpointPersistenceService:
        del (
            composite_name,
            checkpoint_filename,
            glob_pattern,
            storage,
            logger,
            metrics,
        )
        raise AssertionError("legacy keyword factory must not be adapted")

    factory = cast(
        Callable[
            [CompositeCheckpointPersistenceParams],
            CompositeCheckpointPersistenceService,
        ],
        legacy_factory,
    )

    with pytest.raises(TypeError):
        CompositeCheckpointService(
            CompositeCheckpointServiceContext(
                composite_name="activity",
                run_id="run-1",
                storage=MagicMock(),
                logger=MagicMock(),
                persistence_service_factory=factory,
            )
        )
