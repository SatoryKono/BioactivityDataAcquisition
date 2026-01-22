"""Composite pipeline finite state machine.

Defines states and transition rules for composite pipeline execution lifecycle.
The FSM ensures predictable execution flow and prevents invalid operations.
See ADR-026 for architectural decisions.

Transition flow: NOT_STARTED -> SEED_RUNNING -> SEED_COMPLETED -> ENRICHING
-> ENRICHMENT_COMPLETED -> MERGING -> COMPLETED. Any active state can -> FAILED.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import Enum


class CompositePipelineState(str, Enum):
    """State of composite pipeline execution.

    States: NOT_STARTED, SEED_RUNNING, SEED_COMPLETED, ENRICHING,
    ENRICHMENT_COMPLETED, MERGING, COMPLETED, FAILED.

    Terminal states: COMPLETED, FAILED (no transitions allowed).
    Active states: SEED_RUNNING, ENRICHING, MERGING (work in progress).
    """

    NOT_STARTED = "not_started"
    SEED_RUNNING = "seed_running"
    SEED_COMPLETED = "seed_completed"
    ENRICHING = "enriching"
    ENRICHMENT_COMPLETED = "enrichment_completed"
    MERGING = "merging"
    COMPLETED = "completed"
    FAILED = "failed"

    @property
    def is_terminal(self) -> bool:
        """Check if this is a terminal state (COMPLETED or FAILED)."""
        return self in {CompositePipelineState.COMPLETED, CompositePipelineState.FAILED}

    @property
    def is_active(self) -> bool:
        """Check if this is an active state (SEED_RUNNING, ENRICHING, MERGING)."""
        return self in {
            CompositePipelineState.SEED_RUNNING,
            CompositePipelineState.ENRICHING,
            CompositePipelineState.MERGING,
        }

    @property
    def is_success(self) -> bool:
        """Check if this state represents successful completion (COMPLETED only)."""
        return self == CompositePipelineState.COMPLETED

    @property
    def allowed_transitions(self) -> frozenset[CompositePipelineState]:
        """Get the set of states that can be transitioned to from this state."""
        allowed_values = _STATE_TRANSITIONS.get(self.value, frozenset())
        return frozenset(CompositePipelineState(v) for v in allowed_values)

    def can_transition_to(self, target: CompositePipelineState) -> bool:
        """Check if transition to target state is valid."""
        return target in self.allowed_transitions

    def validate_transition(self, target: CompositePipelineState) -> None:
        """Validate transition to target state, raising InvalidStateError if invalid."""
        if not self.can_transition_to(target):
            from bioetl.domain.exceptions import InvalidStateError

            raise InvalidStateError(
                f"Invalid state transition: {self.value} -> {target.value}",
                current_state=self.value,
                attempted_operation=f"transition_to_{target.value}",
            )

    @classmethod
    def from_string(cls, value: str) -> CompositePipelineState:
        """Create CompositePipelineState from string value (case-insensitive)."""
        try:
            return cls(value.lower())
        except ValueError:
            valid = ", ".join(s.value for s in cls)
            raise ValueError(
                f"Invalid composite pipeline state: {value}. Valid: {valid}"
            ) from None

    def to_metric_value(self) -> int:
        """Convert state to numeric value (0-7) for Prometheus metrics."""
        return _STATE_METRIC_VALUES[self]


# Valid transitions for each state
# Maps current state value -> set of allowed next state values
_STATE_TRANSITIONS: Mapping[str, frozenset[str]] = {
    "not_started": frozenset({"seed_running"}),
    "seed_running": frozenset({"seed_completed", "failed"}),
    "seed_completed": frozenset({"enriching"}),
    "enriching": frozenset({"enrichment_completed", "failed"}),
    "enrichment_completed": frozenset({"merging"}),
    "merging": frozenset({"completed", "failed"}),
    "completed": frozenset(),  # Terminal state
    "failed": frozenset(),  # Terminal state
}

# Metric values for each state (for Prometheus gauge)
_STATE_METRIC_VALUES: Mapping[CompositePipelineState, int] = {
    CompositePipelineState.NOT_STARTED: 0,
    CompositePipelineState.SEED_RUNNING: 1,
    CompositePipelineState.SEED_COMPLETED: 2,
    CompositePipelineState.ENRICHING: 3,
    CompositePipelineState.ENRICHMENT_COMPLETED: 4,
    CompositePipelineState.MERGING: 5,
    CompositePipelineState.COMPLETED: 6,
    CompositePipelineState.FAILED: 7,
}


def can_transition(
    current: CompositePipelineState,
    target: CompositePipelineState,
) -> bool:
    """Check if a state transition is valid (module-level function)."""
    return current.can_transition_to(target)


def validate_transition(
    current: CompositePipelineState,
    target: CompositePipelineState,
) -> None:
    """Validate a state transition, raising InvalidStateError if invalid."""
    current.validate_transition(target)


# Type alias for state transition rules
TransitionRules = Mapping[CompositePipelineState, frozenset[CompositePipelineState]]


def get_transition_rules() -> TransitionRules:
    """Get the complete state transition rules as a mapping."""
    return {state: state.allowed_transitions for state in CompositePipelineState}
