"""Owner tests for CompositeInfrastructureContext thin package module."""

from __future__ import annotations

import pytest

from types import SimpleNamespace
from unittest.mock import MagicMock

from bioetl.composition.bootstrap.composite_infrastructure_context import (
    CompositeInfrastructureContext,
)


pytestmark = pytest.mark.unit

def test_composite_infrastructure_context_exposes_bootstrap_primitives() -> None:
    settings = SimpleNamespace(data_dir="data")
    logger = MagicMock()
    metrics = MagicMock()
    tracer = MagicMock()
    storage = MagicMock()
    lock = MagicMock()

    context = CompositeInfrastructureContext(
        run_id="run-123",
        settings=settings,
        logger=logger,
        metrics=metrics,
        tracer=tracer,
        storage=storage,
        lock=lock,
    )

    assert context.run_id == "run-123"
    assert context.settings is settings
    assert context.logger is logger
    assert context.metrics is metrics
    assert context.tracer is tracer
    assert context.storage is storage
    assert context.lock is lock
