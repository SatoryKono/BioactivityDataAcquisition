"""Pure finite-state transition table for batch execution lifecycle."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

__all__ = [
    "BatchExecutionCommand",
    "BatchExecutionCommandTask",
    "BatchExecutionCoordinator",
    "BatchExecutionEvent",
    "BatchExecutionEventSignal",
    "BatchExecutionFSM",
    "BatchExecutionState",
    "BatchExecutionTransitionResult",
    "IllegalStateTransitionError",
    "TransitionResult",
]


class IllegalStateTransitionError(RuntimeError):
    """Raised when an invalid FSM transition is attempted."""
    pass


class BatchExecutionState(Enum):
    """Valid states during a batch execution run."""
    IDLE = auto()
    STREAMING = auto()
    PROCESSING = auto()
    STATE_COMMIT = auto()
    CHECKPOINT_EVALUATION = auto()
    SHUTTING_DOWN = auto()
    DONE = auto()
    FAILED = auto()


class BatchExecutionEventSignal(Enum):
    """Events that trigger state transitions."""
    RUN_STARTED = auto()
    BATCH_ASSEMBLED = auto()
    STREAM_EXHAUSTED_EMPTY = auto()
    STREAM_EXHAUSTED_WITH_BATCH = auto()
    PROCESS_SUCCEEDED = auto()
    PROCESS_FAILED = auto()
    STATE_COMMITTED = auto()
    STATE_COMMIT_FAILED = auto()
    CHECKPOINT_REQUIRED = auto()
    CHECKPOINT_NOT_REQUIRED = auto()
    CHECKPOINT_SAVED = auto()
    CHECKPOINT_FAILED = auto()
    SHUTDOWN_REQUESTED = auto()


class BatchExecutionCommandTask(Enum):
    """Commands to be executed by the orchestration layer."""
    PROCESS_BATCH = auto()
    COMMIT_STATE = auto()
    SAVE_CHECKPOINT = auto()
    STOP_LOOP = auto()
    PROPAGATE_ERROR = auto()
    NOOP = auto()


@dataclass(frozen=True, slots=True)
class BatchExecutionTransitionResult:
    """Result of a transition with the next state and orchestration commands."""
    new_state: BatchExecutionState
    commands: tuple[BatchExecutionCommandTask, ...]


def _transition(
    new_state: BatchExecutionState,
    *commands: BatchExecutionCommandTask,
) -> BatchExecutionTransitionResult:
    """Create one immutable transition entry."""
    return BatchExecutionTransitionResult(new_state=new_state, commands=commands)


_TRANSITIONS: dict[
    tuple[BatchExecutionState, BatchExecutionEventSignal],
    BatchExecutionTransitionResult,
] = {
    (BatchExecutionState.IDLE, BatchExecutionEventSignal.RUN_STARTED): _transition(
        BatchExecutionState.STREAMING,
        BatchExecutionCommandTask.NOOP,
    ),
    (
        BatchExecutionState.STREAMING,
        BatchExecutionEventSignal.BATCH_ASSEMBLED,
    ): _transition(
        BatchExecutionState.PROCESSING,
        BatchExecutionCommandTask.PROCESS_BATCH,
    ),
    (
        BatchExecutionState.PROCESSING,
        BatchExecutionEventSignal.PROCESS_SUCCEEDED,
    ): _transition(
        BatchExecutionState.STATE_COMMIT,
        BatchExecutionCommandTask.COMMIT_STATE,
    ),
    (
        BatchExecutionState.STATE_COMMIT,
        BatchExecutionEventSignal.STATE_COMMITTED,
    ): _transition(
        BatchExecutionState.CHECKPOINT_EVALUATION,
        BatchExecutionCommandTask.NOOP,
    ),
    (
        BatchExecutionState.CHECKPOINT_EVALUATION,
        BatchExecutionEventSignal.CHECKPOINT_REQUIRED,
    ): _transition(
        BatchExecutionState.CHECKPOINT_EVALUATION,
        BatchExecutionCommandTask.SAVE_CHECKPOINT,
    ),
    (
        BatchExecutionState.CHECKPOINT_EVALUATION,
        BatchExecutionEventSignal.CHECKPOINT_SAVED,
    ): _transition(
        BatchExecutionState.STREAMING,
        BatchExecutionCommandTask.NOOP,
    ),
    (
        BatchExecutionState.CHECKPOINT_EVALUATION,
        BatchExecutionEventSignal.CHECKPOINT_NOT_REQUIRED,
    ): _transition(
        BatchExecutionState.STREAMING,
        BatchExecutionCommandTask.NOOP,
    ),
    (
        BatchExecutionState.STREAMING,
        BatchExecutionEventSignal.STREAM_EXHAUSTED_EMPTY,
    ): _transition(
        BatchExecutionState.DONE,
        BatchExecutionCommandTask.NOOP,
    ),
    (
        BatchExecutionState.STREAMING,
        BatchExecutionEventSignal.STREAM_EXHAUSTED_WITH_BATCH,
    ): _transition(
        BatchExecutionState.PROCESSING,
        BatchExecutionCommandTask.PROCESS_BATCH,
    ),
    (
        BatchExecutionState.STREAMING,
        BatchExecutionEventSignal.SHUTDOWN_REQUESTED,
    ): _transition(
        BatchExecutionState.SHUTTING_DOWN,
        BatchExecutionCommandTask.SAVE_CHECKPOINT,
        BatchExecutionCommandTask.STOP_LOOP,
    ),
    (
        BatchExecutionState.SHUTTING_DOWN,
        BatchExecutionEventSignal.CHECKPOINT_SAVED,
    ): _transition(
        BatchExecutionState.DONE,
        BatchExecutionCommandTask.NOOP,
    ),
    (
        BatchExecutionState.PROCESSING,
        BatchExecutionEventSignal.PROCESS_FAILED,
    ): _transition(
        BatchExecutionState.FAILED,
        BatchExecutionCommandTask.PROPAGATE_ERROR,
    ),
    (
        BatchExecutionState.STATE_COMMIT,
        BatchExecutionEventSignal.STATE_COMMIT_FAILED,
    ): _transition(
        BatchExecutionState.FAILED,
        BatchExecutionCommandTask.PROPAGATE_ERROR,
    ),
    (
        BatchExecutionState.CHECKPOINT_EVALUATION,
        BatchExecutionEventSignal.CHECKPOINT_FAILED,
    ): _transition(
        BatchExecutionState.FAILED,
        BatchExecutionCommandTask.PROPAGATE_ERROR,
    ),
}


class BatchExecutionCoordinator:
    """Pure coordinator that validates batch lifecycle transitions."""
    def advance(
        self,
        current_state: BatchExecutionState,
        event: BatchExecutionEventSignal,
    ) -> BatchExecutionTransitionResult:
        """Advance to the next state for the given event."""
        transition = _TRANSITIONS.get((current_state, event))
        if transition is None:
            raise IllegalStateTransitionError(
                f"Invalid transition: {current_state.name} + {event.name}"
            )
        return transition


# Backward-compatible aliases preserved for existing imports/tests.
BatchExecutionEvent = BatchExecutionEventSignal
BatchExecutionCommand = BatchExecutionCommandTask
TransitionResult = BatchExecutionTransitionResult
BatchExecutionFSM = BatchExecutionCoordinator
