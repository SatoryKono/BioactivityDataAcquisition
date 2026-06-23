"""Focused tests for composite runner lifecycle helpers."""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING, cast
from unittest.mock import AsyncMock, MagicMock
from tests.helpers.deterministic_ids import deterministic_uuid_from_callsite

import pytest

from tests.helpers.clock import fixed_test_clock

if TYPE_CHECKING:
    from bioetl.application.composite.runner_pkg.runner_runtime_helpers import (
        _CheckpointManagerProtocol,
        _FSMRuntimeHelperProtocol,
    )

from bioetl.application.composite.lifecycle_observer_service import (
    CompositeLifecycleObserverService,
)
from bioetl.application.composite.runner_pkg.runner_runtime_helpers import (
    bind_runner_dependencies,
    prepare_run_state,
    resolve_original_run_id,
    run_with_managed_lock,
    validate_runner_can_start,
)
from bioetl.application.composite.runtime_models import (
    CompositeRunnerDependencies,
    CompositeRuntimeConfig,
)
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.exceptions import LockAcquisitionError, RunnerAlreadyExecutedError


def _make_runtime(**overrides: object) -> CompositeRuntimeConfig:
    defaults = {"resume": False}
    defaults.update(overrides)
    return cast(CompositeRuntimeConfig, SimpleNamespace(**defaults))


def _make_checkpoint_state(**overrides: object) -> object:
    defaults = {
        "is_resumable": True,
        "run_id": "original-run",
        "state": CompositePipelineState.FAILED,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


@pytest.mark.unit
def test_bind_runner_dependencies_builds_metrics_aware_observer_fallback() -> None:
    host = SimpleNamespace()
    logger = MagicMock()
    metrics = MagicMock()
    tracer = MagicMock()
    deps = cast(
        CompositeRunnerDependencies,
        SimpleNamespace(
            seed_runner_factory=MagicMock(),
            enricher_runner_factory=MagicMock(),
            dependencies_runner_factory=MagicMock(),
            key_extractor=MagicMock(),
            dependency_coordinator=MagicMock(),
            coordinator=MagicMock(),
            merger=MagicMock(),
            checkpoint_manager=MagicMock(),
            logger=logger,
            lock=MagicMock(),
            dq_report_service=MagicMock(),
            preflight_validator=MagicMock(),
            quarantine_port=MagicMock(),
            metrics=metrics,
            tracer=tracer,
            observer=None,
            fsm_state_helper=MagicMock(),
            manifest_id="manifest-123",
            run_ledger_service=MagicMock(),
            clock=fixed_test_clock(),
        ),
    )

    bind_runner_dependencies(host, deps)

    assert isinstance(host._observer, CompositeLifecycleObserverService)
    assert host._observer.logger is logger
    assert host._observer.metrics is metrics
    assert host._observer.tracer is tracer


@pytest.mark.unit
def test_validate_runner_can_start_raises_for_finished_runner() -> None:
    with pytest.raises(RunnerAlreadyExecutedError, match="CompositePipelineRunner"):
        validate_runner_can_start(
            finished=True,
            run_id="run-123",
            final_state=CompositePipelineState.FAILED,
        )


@pytest.mark.unit
def test_resolve_original_run_id_for_resume_returns_checkpoint_run_id() -> None:
    runtime = _make_runtime(resume=True)
    state = _make_checkpoint_state(is_resumable=True, run_id="original-run")

    result = resolve_original_run_id(
        runtime=runtime,
        state=state,
        current_run_id="new-run",
    )

    assert result == "original-run"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_with_managed_lock_starts_and_stops_heartbeat() -> None:
    lock_port = AsyncMock()
    lock_port.acquire.return_value = True
    lock_port.release = AsyncMock()
    heartbeat = SimpleNamespace(start=AsyncMock(), stop=AsyncMock())
    owner_id = deterministic_uuid_from_callsite("test_runner_runtime_helpers")
    run_while_locked = AsyncMock(return_value="ok")

    result = await run_with_managed_lock(
        lock_port=lock_port,
        lock_key="lock:composite",
        owner_id=owner_id,
        lock_ttl_seconds=300,
        heartbeat_interval_seconds=30,
        logger=SimpleNamespace(),
        run_while_locked=run_while_locked,
        lock_context_factory=lambda **_: SimpleNamespace(heartbeat=heartbeat),
    )

    assert result == "ok"
    heartbeat.start.assert_awaited_once()
    run_while_locked.assert_awaited_once()
    heartbeat.stop.assert_awaited_once()
    lock_port.release.assert_awaited_once_with(
        key="lock:composite",
        owner_id=owner_id,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_with_managed_lock_raises_when_lock_not_acquired() -> None:
    lock_port = AsyncMock()
    lock_port.acquire.return_value = False
    owner_id = deterministic_uuid_from_callsite("test_runner_runtime_helpers")

    with pytest.raises(LockAcquisitionError, match="lock:composite"):
        await run_with_managed_lock(
            lock_port=lock_port,
            lock_key="lock:composite",
            owner_id=owner_id,
            lock_ttl_seconds=300,
            heartbeat_interval_seconds=30,
            logger=SimpleNamespace(),
            run_while_locked=AsyncMock(),
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_prepare_run_state_normalizes_failed_resume_before_logging() -> None:
    failed_state = _make_checkpoint_state(
        state=CompositePipelineState.FAILED,
        is_resumable=True,
    )
    resumed_state = _make_checkpoint_state(
        state=CompositePipelineState.ENRICHMENT_COMPLETED,
        is_resumable=True,
    )
    checkpoint_manager = SimpleNamespace(load=AsyncMock(return_value=failed_state))
    fsm = SimpleNamespace(
        handle_resume_from_failed=MagicMock(return_value=resumed_state),
        log_resume_context=MagicMock(),
    )

    result = await prepare_run_state(
        checkpoint_manager=cast("_CheckpointManagerProtocol", checkpoint_manager),
        runtime=_make_runtime(resume=True),
        fsm=cast("_FSMRuntimeHelperProtocol", fsm),
    )

    assert result is resumed_state
    fsm.handle_resume_from_failed.assert_called_once_with(failed_state)
    fsm.log_resume_context.assert_called_once_with(resumed_state)
