"""Application-owned transition seam for composite checkpoint FSM state."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.domain.composite.state import CompositePipelineState, validate_transition

if TYPE_CHECKING:
    from bioetl.application.composite.checkpoint.state import CompositeCheckpointState
    from bioetl.domain.ports import ClockPort

__all__ = [
    "apply_recovery_checkpoint_transition",
    "apply_validated_checkpoint_transition",
]


def _replace_checkpoint_state(
    checkpoint_state: CompositeCheckpointState,
    new_state: CompositePipelineState,
    *,
    clock: ClockPort | None = None,
) -> CompositeCheckpointState:
    """Delegate raw immutable state replacement while preserving clock semantics."""
    if clock is None:
        return checkpoint_state.with_state(new_state)
    return checkpoint_state.with_state(new_state, clock=clock)


def apply_validated_checkpoint_transition(
    checkpoint_state: CompositeCheckpointState,
    new_state: CompositePipelineState,
    *,
    clock: ClockPort | None = None,
) -> CompositeCheckpointState:
    """Apply a normal execution transition guarded by the domain FSM."""
    validate_transition(checkpoint_state.state, new_state)
    return _replace_checkpoint_state(checkpoint_state, new_state, clock=clock)


def apply_recovery_checkpoint_transition(
    checkpoint_state: CompositeCheckpointState,
    new_state: CompositePipelineState,
    *,
    reason: str,
    clock: ClockPort | None = None,
) -> CompositeCheckpointState:
    """Apply an explicit recovery-only transition that bypasses domain FSM rules."""
    if not reason.strip():
        raise ValueError("Recovery checkpoint transitions require a non-empty reason")
    return _replace_checkpoint_state(checkpoint_state, new_state, clock=clock)
