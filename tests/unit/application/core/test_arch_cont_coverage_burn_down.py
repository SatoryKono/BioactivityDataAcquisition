"""ARCH-CONT-02/03: close residual miss=1 branches in application_core helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.core._runner_dependency_support import (
    PipelineRunnerDependencies,
    load_runner_checkpoint,
)
from bioetl.application.core.lifecycle.shutdown import ShutdownSignal
from bioetl.application.core.runner_flow_metrics import record_output_ready
from bioetl.domain.types import RunType

pytestmark = pytest.mark.unit


def test_pipeline_runner_dependencies_lock_manager_alias() -> None:
    lock = object()
    deps = PipelineRunnerDependencies(
        executor=object(),  # type: ignore[arg-type]
        checkpoint_manager=object(),  # type: ignore[arg-type]
        lock_runtime_service=lock,  # type: ignore[arg-type]
        preflight=object(),  # type: ignore[arg-type]
        postrun=object(),  # type: ignore[arg-type]
        lifecycle_service=object(),  # type: ignore[arg-type]
        observer=object(),  # type: ignore[arg-type]
        shutdown_signal=ShutdownSignal(),
    )
    assert deps.lock_manager is lock


@pytest.mark.asyncio
async def test_load_runner_checkpoint_forwards_current_metadata() -> None:
    checkpoint_manager = SimpleNamespace(
        current_metadata={"k": "v"},
        load_checkpoint=AsyncMock(return_value={"loaded": True}),
    )
    result = await load_runner_checkpoint(checkpoint_manager)  # type: ignore[arg-type]
    assert result == {"loaded": True}
    checkpoint_manager.load_checkpoint.assert_awaited_once_with(
        current_metadata={"k": "v"}
    )


def test_record_output_ready_skips_when_all_counts_zero() -> None:
    host = SimpleNamespace(
        execution_metrics={
            "records_gold": 0,
            "records_silver": 0,
            "records_bronze": 0,
        },
        _services=SimpleNamespace(metrics=MagicMock()),
        _config=SimpleNamespace(pipeline_name="chembl_activity"),
        _runtime=SimpleNamespace(run_type=RunType.INCREMENTAL),
    )
    record_output_ready(host)  # type: ignore[arg-type]
    host._services.metrics.increment_counter.assert_not_called()


def test_shutdown_signal_request_is_idempotent() -> None:
    signal = ShutdownSignal()
    assert signal.is_requested is False
    signal.request()
    signal.request()
    assert signal.is_requested is True
    assert signal.is_shutting_down() is True
