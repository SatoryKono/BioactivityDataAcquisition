"""Lifecycle helpers for composite runner entrypoint orchestration."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, TypeVar, cast
from uuid import UUID, uuid4

from bioetl.application.composite.lifecycle_observer_service import (
    CompositeLifecycleObserverService,
)
from bioetl.application.core.lifecycle.heartbeat import HeartbeatTask
from bioetl.application.core.lifecycle.shutdown import ShutdownSignal
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.exceptions import LockAcquisitionError, RunnerAlreadyExecutedError
from bioetl.domain.types import RunID

if TYPE_CHECKING:
    from bioetl.application.composite.checkpoint import CompositeCheckpointState
    from bioetl.application.composite.runtime_models import (
        CompositeRunnerDependencies,
        CompositeRuntimeConfig,
    )
    from bioetl.domain.ports import ClockPort, LockPort, LoggerPort

__all__ = [
    "ManagedCompositeLockContext",
    "bind_runner_dependencies",
    "create_managed_lock_resources",
    "initialize_runner_runtime_state",
    "prepare_run_state",
    "resolve_original_run_id",
    "run_with_managed_lock",
    "validate_runner_can_start",
]

TRunResult = TypeVar("TRunResult")


class _CheckpointManagerProtocol(Protocol):
    async def load(self) -> CompositeCheckpointState: ...


class _FSMRuntimeHelperProtocol(Protocol):
    def handle_resume_from_failed(
        self,
        state: CompositeCheckpointState,
        *,
        clock: ClockPort | None = None,
    ) -> CompositeCheckpointState: ...

    def log_resume_context(self, state: CompositeCheckpointState) -> None: ...


@dataclass(frozen=True, slots=True)
class ManagedCompositeLockContext:
    """Lock lifecycle resources that wrap one composite run."""

    shutdown_signal: ShutdownSignal
    heartbeat: HeartbeatTask


class _CompositeRunnerHostProtocol(Protocol):
    _seed_runner_factory: object
    _enricher_runner_factory: object
    _dependencies_runner_factory: object
    _key_extractor: object
    _dependency_coordinator: object
    _coordinator: object
    _merger: object
    _checkpoint_manager: object
    _logger: object
    _lock: object
    _dq_report_service: object
    _preflight_validator: object
    _quarantine_port: object
    _metrics: object
    _tracing: object
    _observer: object
    _fsm: object
    _manifest_id: str | None
    _run_ledger_service: object
    _clock: object
    _run_id_str: str
    _run_id: RunID
    _start_time: float | None
    _started_at: object
    _original_run_id: object
    _finished: bool
    _final_state: object


def validate_runner_can_start(
    *,
    finished: bool,
    run_id: str,
    final_state: CompositePipelineState | None,
) -> None:
    """Guard against composite runner re-entry after a terminal run."""
    if not finished:
        return
    raise RunnerAlreadyExecutedError(
        runner_type="CompositePipelineRunner",
        run_id=run_id,
        final_state=final_state.value if final_state else None,
    )


def bind_runner_dependencies(host: object, deps: CompositeRunnerDependencies) -> None:
    """Project grouped runner dependencies onto the runner host."""
    runner_host = cast(_CompositeRunnerHostProtocol, host)
    runner_host._seed_runner_factory = deps.seed_runner_factory
    runner_host._enricher_runner_factory = deps.enricher_runner_factory
    runner_host._dependencies_runner_factory = deps.dependencies_runner_factory
    runner_host._key_extractor = deps.key_extractor
    runner_host._dependency_coordinator = deps.dependency_coordinator
    runner_host._coordinator = deps.coordinator
    runner_host._merger = deps.merger
    runner_host._checkpoint_manager = deps.checkpoint_manager
    runner_host._logger = deps.logger
    runner_host._lock = deps.lock
    runner_host._dq_report_service = deps.dq_report_service
    runner_host._preflight_validator = deps.preflight_validator
    runner_host._quarantine_port = deps.quarantine_port
    runner_host._metrics = deps.metrics
    runner_host._tracing = deps.tracer
    runner_host._observer = deps.observer or CompositeLifecycleObserverService(
        logger=deps.logger,
        metrics=deps.metrics,
        tracer=deps.tracer,
    )
    runner_host._fsm = deps.fsm_state_helper
    runner_host._manifest_id = deps.manifest_id
    runner_host._run_ledger_service = deps.run_ledger_service
    runner_host._clock = getattr(deps, "clock", None)


def initialize_runner_runtime_state(host: object, run_id: str | None) -> None:
    """Initialize mutable run lifecycle state on the runner host."""
    runner_host = cast(_CompositeRunnerHostProtocol, host)
    run_id_str = run_id or str(uuid4())
    runner_host._run_id_str = run_id_str
    runner_host._run_id = cast(RunID, UUID(run_id_str))
    runner_host._start_time = None
    runner_host._started_at = None
    runner_host._original_run_id = None
    runner_host._finished = False
    runner_host._final_state = None


def resolve_original_run_id(
    *,
    runtime: CompositeRuntimeConfig,
    state: CompositeCheckpointState,
    current_run_id: str,
) -> str | None:
    """Resolve the original run ID retained for resumed composite diagnostics."""
    if runtime.resume and state.is_resumable and state.run_id != current_run_id:
        return state.run_id
    return None


def create_managed_lock_resources(
    *,
    lock_port: LockPort,
    lock_key: str,
    owner_id: RunID,
    heartbeat_interval_seconds: int,
    logger: LoggerPort,
) -> ManagedCompositeLockContext:
    """Create heartbeat resources for the duration of a held lock."""
    shutdown_signal = ShutdownSignal()
    heartbeat = HeartbeatTask(
        lock_port=lock_port,
        lock_key=lock_key,
        owner_id=owner_id,
        exclusive=False,
        interval=heartbeat_interval_seconds,
        shutdown_signal=shutdown_signal,
        logger=logger,
    )
    return ManagedCompositeLockContext(
        shutdown_signal=shutdown_signal,
        heartbeat=heartbeat,
    )


async def run_with_managed_lock(
    *,
    lock_port: LockPort,
    lock_key: str,
    owner_id: RunID,
    lock_ttl_seconds: int,
    heartbeat_interval_seconds: int,
    logger: LoggerPort,
    run_while_locked: Callable[[], Awaitable[TRunResult]],
    lock_context_factory: Callable[..., ManagedCompositeLockContext] = (
        create_managed_lock_resources
    ),
) -> TRunResult:
    """Acquire a managed lock, run the callback, and always release cleanly."""
    acquired = await lock_port.acquire(
        key=lock_key,
        owner_id=owner_id,
        ttl=lock_ttl_seconds,
    )
    if not acquired:
        raise LockAcquisitionError(key=lock_key)

    lock_context = lock_context_factory(
        lock_port=lock_port,
        lock_key=lock_key,
        owner_id=owner_id,
        heartbeat_interval_seconds=heartbeat_interval_seconds,
        logger=logger,
    )
    try:
        await lock_context.heartbeat.start()
        return await run_while_locked()
    finally:
        await lock_context.heartbeat.stop()
        await lock_port.release(key=lock_key, owner_id=owner_id)


async def prepare_run_state(
    *,
    checkpoint_manager: _CheckpointManagerProtocol,
    runtime: CompositeRuntimeConfig,
    fsm: _FSMRuntimeHelperProtocol,
    clock: ClockPort | None = None,
) -> CompositeCheckpointState:
    """Load checkpoint state and apply resume normalization semantics."""
    state = await checkpoint_manager.load()

    if runtime.resume and state.state == CompositePipelineState.FAILED:
        if clock is None:
            state = fsm.handle_resume_from_failed(state)
        else:
            state = fsm.handle_resume_from_failed(state, clock=clock)
    if runtime.resume and state.is_resumable:
        fsm.log_resume_context(state)

    return state
