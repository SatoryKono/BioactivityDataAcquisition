"""Composite pipeline finite state machine.

Defines states and transition rules for composite pipeline execution lifecycle.
The FSM ensures predictable execution flow and prevents invalid operations.
See ADR-026 for architectural decisions.

Transition flow: NOT_STARTED -> SEED_RUNNING -> SEED_COMPLETED ->
DEPENDENCIES_RUNNING -> DEPENDENCIES_COMPLETED -> ENRICHING ->
ENRICHMENT_COMPLETED -> MERGING -> CROSS_VALIDATION_RUNNING ->
CROSS_VALIDATION_COMPLETED -> COMPLETED. Any active state can -> FAILED.

Note: Dependencies are optional. If no dependencies, SEED_COMPLETED transitions
directly to ENRICHING (or DEPENDENCIES_RUNNING which immediately transitions to
DEPENDENCIES_COMPLETED).

Note: Cross-validation is optional. If no cross-validation configured, MERGING
transitions directly to COMPLETED (or CROSS_VALIDATION_RUNNING which immediately
transitions to CROSS_VALIDATION_COMPLETED).

Note: Dry-run composite execution skips MERGING entirely, but that shortcut is
owned by the application layer rather than the domain FSM.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum

__all__ = [
    "CompositePipelineState",
    "TransitionRules",
    "can_transition",
    "get_transition_rules",
    "validate_transition",
]


class CompositePipelineState(StrEnum):
    """State of composite pipeline execution.

    States: NOT_STARTED, SEED_RUNNING, SEED_COMPLETED, DEPENDENCIES_RUNNING,
    DEPENDENCIES_COMPLETED, ENRICHING, ENRICHMENT_COMPLETED, MERGING,
    CROSS_VALIDATION_RUNNING, CROSS_VALIDATION_COMPLETED, COMPLETED, FAILED.

    Terminal states: COMPLETED, FAILED (no transitions allowed).
    Active states: SEED_RUNNING, DEPENDENCIES_RUNNING, ENRICHING, MERGING,
        CROSS_VALIDATION_RUNNING (work in progress).
    """

    NOT_STARTED = "not_started"
    SEED_RUNNING = "seed_running"
    SEED_COMPLETED = "seed_completed"
    DEPENDENCIES_RUNNING = "dependencies_running"
    DEPENDENCIES_COMPLETED = "dependencies_completed"
    ENRICHING = "enriching"
    ENRICHMENT_COMPLETED = "enrichment_completed"
    MERGING = "merging"
    CROSS_VALIDATION_RUNNING = "cross_validation_running"
    CROSS_VALIDATION_COMPLETED = "cross_validation_completed"
    COMPLETED = "completed"
    FAILED = "failed"

    @property
    def is_terminal(self) -> bool:
        """Check if this is a terminal state (COMPLETED or FAILED)."""
        return self in {CompositePipelineState.COMPLETED, CompositePipelineState.FAILED}

    @property
    def is_active(self) -> bool:
        """Check if this is an active state (work in progress).

        Active states: SEED_RUNNING, DEPENDENCIES_RUNNING, ENRICHING, MERGING,
            CROSS_VALIDATION_RUNNING.
        """
        return self in {
            CompositePipelineState.SEED_RUNNING,
            CompositePipelineState.DEPENDENCIES_RUNNING,
            CompositePipelineState.ENRICHING,
            CompositePipelineState.MERGING,
            CompositePipelineState.CROSS_VALIDATION_RUNNING,
        }

    @property
    def is_success(self) -> bool:
        """Check if this state represents successful completion (COMPLETED only)."""
        return self == CompositePipelineState.COMPLETED

    @property
    def is_resumable(self) -> bool:
        """Check if execution can be resumed from this state.

        Resumable states have completed work that can be skipped on resume:
        SEED_COMPLETED, DEPENDENCIES_RUNNING, DEPENDENCIES_COMPLETED, ENRICHING,
        ENRICHMENT_COMPLETED, CROSS_VALIDATION_RUNNING, CROSS_VALIDATION_COMPLETED, FAILED.

        FAILED is resumable to allow retry after merge failure - the seed,
        dependency, and enrichment results are preserved in the checkpoint.

        Returns:
            True if this state allows resume with partial progress preserved.

        Example:
            >>> CompositePipelineState.SEED_COMPLETED.is_resumable
            True
            >>> CompositePipelineState.NOT_STARTED.is_resumable
            False
            >>> CompositePipelineState.FAILED.is_resumable
            True
        """
        return self in {
            CompositePipelineState.SEED_COMPLETED,
            CompositePipelineState.DEPENDENCIES_RUNNING,
            CompositePipelineState.DEPENDENCIES_COMPLETED,
            CompositePipelineState.ENRICHING,
            CompositePipelineState.ENRICHMENT_COMPLETED,
            CompositePipelineState.CROSS_VALIDATION_RUNNING,
            CompositePipelineState.CROSS_VALIDATION_COMPLETED,
            CompositePipelineState.FAILED,
        }

    @property
    def allowed_transitions(self) -> frozenset[CompositePipelineState]:
        """Get the set of states that can be transitioned to from this state."""
        allowed_values = _STATE_TRANSITIONS.get(self.value, frozenset())
        return frozenset(CompositePipelineState(v) for v in allowed_values)

    def can_transition_to(self, target: CompositePipelineState) -> bool:
        """Check if transition to target state is valid.

        Args:
            target: Target destination.

        Returns:
            True if this state allows transitioning to target, False otherwise.
        """
        return target in self.allowed_transitions

    def validate_transition(self, target: CompositePipelineState) -> None:
        """Validate transition to target state, raising InvalidStateError if invalid.

        Args:
            target: Target destination.
        """
        if not self.can_transition_to(target):
            from bioetl.domain.exceptions import InvalidStateError

            raise InvalidStateError(
                f"Invalid state transition: {self.value} -> {target.value}",
                current_state=self.value,
                attempted_operation=f"transition_to_{target.value}",
            )

    @classmethod
    def from_string(cls, value: str) -> CompositePipelineState:
        """Create CompositePipelineState from string value (case-insensitive).

        Args:
            value: Input value.

        Returns:
            Matching CompositePipelineState enum member.
        """
        try:
            return cls(value.lower())
        except ValueError:
            valid = ", ".join(s.value for s in cls)
            raise ValueError(
                f"Invalid composite pipeline state: {value}. Valid: {valid}"
            ) from None

    def to_metric_value(self) -> int:
        """Convert state to numeric value (0-9) for Prometheus metrics.

        Returns:
            Integer in range 0-9 representing the current pipeline state.
        """
        return _STATE_METRIC_VALUES[self]


# Valid transitions for each state
# Maps current state value -> set of allowed next state values
# Note: seed_completed can go to dependencies_running OR enriching (if no dependencies)
# Note: dry-run completion shortcut is guarded in the application layer
# Note: merging can go to cross_validation_running OR completed (if no cross-validation)
# Note: any active state can transition to FAILED, including MERGING
_STATE_TRANSITIONS: Mapping[str, frozenset[str]] = {
    "not_started": frozenset({"seed_running"}),
    "seed_running": frozenset({"seed_completed", "failed"}),
    "seed_completed": frozenset({"dependencies_running", "enriching"}),
    "dependencies_running": frozenset({"dependencies_completed", "failed"}),
    "dependencies_completed": frozenset({"enriching"}),
    "enriching": frozenset({"enrichment_completed", "failed"}),
    "enrichment_completed": frozenset({"merging"}),
    "merging": frozenset({"cross_validation_running", "completed", "failed"}),
    "cross_validation_running": frozenset({"cross_validation_completed", "failed"}),
    "cross_validation_completed": frozenset({"completed"}),
    "completed": frozenset(),  # Terminal state
    "failed": frozenset(),  # Terminal state
}

# Metric values for each state (for Prometheus gauge)
_STATE_METRIC_VALUES: Mapping[CompositePipelineState, int] = {
    CompositePipelineState.NOT_STARTED: 0,
    CompositePipelineState.SEED_RUNNING: 1,
    CompositePipelineState.SEED_COMPLETED: 2,
    CompositePipelineState.DEPENDENCIES_RUNNING: 3,
    CompositePipelineState.DEPENDENCIES_COMPLETED: 4,
    CompositePipelineState.ENRICHING: 5,
    CompositePipelineState.ENRICHMENT_COMPLETED: 6,
    CompositePipelineState.MERGING: 7,
    CompositePipelineState.CROSS_VALIDATION_RUNNING: 8,
    CompositePipelineState.CROSS_VALIDATION_COMPLETED: 9,
    CompositePipelineState.COMPLETED: 10,
    CompositePipelineState.FAILED: 11,
}


def can_transition(
    current: CompositePipelineState,
    target: CompositePipelineState,
) -> bool:
    """Check if a state transition is valid (module-level function).

    Args:
        current: Current.
        target: Target destination.

    Returns:
        True if current state allows transitioning to target, False otherwise.
    """
    return current.can_transition_to(target)


def validate_transition(
    current: CompositePipelineState,
    target: CompositePipelineState,
) -> None:
    """Validate a state transition, raising InvalidStateError if invalid.

    Args:
        current: Current.
        target: Target destination.
    """
    current.validate_transition(target)


# Type alias for state transition rules
TransitionRules = Mapping[CompositePipelineState, frozenset[CompositePipelineState]]


def get_transition_rules() -> TransitionRules:
    """Get the complete state transition rules as a mapping.

    Returns a dictionary mapping each state to its allowed target states.
    Useful for visualization or external validation.

    Returns:
        Mapping of state -> allowed target states.

    Example:
        >>> rules = get_transition_rules()
        >>> CompositePipelineState.MERGING in rules[CompositePipelineState.ENRICHMENT_COMPLETED]
        True
    """
    return {state: state.allowed_transitions for state in CompositePipelineState}
