"""Composite pipeline finite state machine.

Defines states and transition rules for composite pipeline execution lifecycle.

The FSM ensures predictable execution flow and prevents invalid operations.
For example, merging cannot start before all enrichments complete.

See ADR-026 for architectural decisions.

State Transition Diagram::

    NOT_STARTED ─────► SEED_RUNNING
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
         SEED_COMPLETED                 FAILED
              │
              ▼
          ENRICHING
              │
    ┌─────────┴─────────┐
    ▼                   ▼
 ENRICHMENT_COMPLETED FAILED
    │
    ▼
  MERGING
    │
    ┌───────┴───────┐
    ▼               ▼
 COMPLETED        FAILED
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import Enum


class CompositePipelineState(str, Enum):
    """State of composite pipeline execution.

    Represents the current stage in the composite pipeline lifecycle.
    Each state has specific semantics and allowed transitions.

    States:
        NOT_STARTED: Initial state before any execution. The pipeline has been
            configured but not yet started.

        SEED_RUNNING: The seed pipeline is currently executing. This is the
            first active state where data extraction begins.

        SEED_COMPLETED: The seed pipeline finished successfully. Ready to
            proceed with enrichment stage.

        ENRICHING: One or more enrichment pipelines are executing in parallel.
            This stage may run multiple enrichers concurrently.

        ENRICHMENT_COMPLETED: All enrichment pipelines have finished. This
            includes successful, failed (optional), and skipped enrichers.
            Ready for merge stage.

        MERGING: The merge operation is in progress, combining seed and
            enriched data into the final output.

        COMPLETED: The composite pipeline finished successfully. Gold table
            has been created with merged data.

        FAILED: The composite pipeline terminated due to a critical error.
            This is a terminal state. Errors include: seed failure,
            required enricher failure, or merge failure.

    Example:
        >>> state = CompositePipelineState.NOT_STARTED
        >>> state.is_terminal
        False
        >>> CompositePipelineState.FAILED.is_terminal
        True
        >>> state.can_transition_to(CompositePipelineState.SEED_RUNNING)
        True
        >>> state.can_transition_to(CompositePipelineState.MERGING)
        False
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
        """Check if this is a terminal (final) state.

        Terminal states are COMPLETED and FAILED. No transitions
        are allowed from these states.

        Returns:
            True if this state is terminal, False otherwise.

        Example:
            >>> CompositePipelineState.COMPLETED.is_terminal
            True
            >>> CompositePipelineState.ENRICHING.is_terminal
            False
        """
        return self in {CompositePipelineState.COMPLETED, CompositePipelineState.FAILED}

    @property
    def is_active(self) -> bool:
        """Check if this is an active (in-progress) state.

        Active states indicate that work is currently being performed:
        SEED_RUNNING, ENRICHING, MERGING.

        Returns:
            True if this state represents active execution.

        Example:
            >>> CompositePipelineState.SEED_RUNNING.is_active
            True
            >>> CompositePipelineState.SEED_COMPLETED.is_active
            False
        """
        return self in {
            CompositePipelineState.SEED_RUNNING,
            CompositePipelineState.ENRICHING,
            CompositePipelineState.MERGING,
        }

    @property
    def is_success(self) -> bool:
        """Check if this state represents successful completion.

        Returns:
            True only for COMPLETED state.

        Example:
            >>> CompositePipelineState.COMPLETED.is_success
            True
            >>> CompositePipelineState.FAILED.is_success
            False
        """
        return self == CompositePipelineState.COMPLETED

    @property
    def allowed_transitions(self) -> frozenset[CompositePipelineState]:
        """Get the set of states that can be transitioned to from this state.

        Returns:
            Frozenset of allowed target states.

        Example:
            >>> CompositePipelineState.SEED_RUNNING.allowed_transitions
            frozenset({<CompositePipelineState.SEED_COMPLETED: 'seed_completed'>,
                      <CompositePipelineState.FAILED: 'failed'>})
        """
        allowed_values = _STATE_TRANSITIONS.get(self.value, frozenset())
        return frozenset(CompositePipelineState(v) for v in allowed_values)

    def can_transition_to(self, target: CompositePipelineState) -> bool:
        """Check if transition to target state is valid.

        Args:
            target: The target state to transition to.

        Returns:
            True if transition is allowed, False otherwise.

        Example:
            >>> state = CompositePipelineState.SEED_COMPLETED
            >>> state.can_transition_to(CompositePipelineState.ENRICHING)
            True
            >>> state.can_transition_to(CompositePipelineState.MERGING)
            False
        """
        return target in self.allowed_transitions

    def validate_transition(self, target: CompositePipelineState) -> None:
        """Validate transition to target state, raising on invalid.

        Use this method when transitioning states to ensure the FSM
        rules are enforced.

        Args:
            target: The target state to transition to.

        Raises:
            InvalidStateError: If transition is not allowed.

        Example:
            >>> state = CompositePipelineState.NOT_STARTED
            >>> state.validate_transition(CompositePipelineState.SEED_RUNNING)
            >>> # No exception raised
            >>> state.validate_transition(CompositePipelineState.MERGING)
            InvalidStateError: Invalid state transition: not_started -> merging
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
        """Create CompositePipelineState from string value.

        Args:
            value: String representation of state.

        Returns:
            CompositePipelineState enum value.

        Raises:
            ValueError: If value is not a valid state.

        Example:
            >>> CompositePipelineState.from_string("seed_running")
            <CompositePipelineState.SEED_RUNNING: 'seed_running'>
        """
        try:
            return cls(value.lower())
        except ValueError:
            valid = ", ".join(s.value for s in cls)
            raise ValueError(
                f"Invalid composite pipeline state: {value}. Valid: {valid}"
            ) from None

    def to_metric_value(self) -> int:
        """Convert state to numeric value for metrics.

        Returns integer representation suitable for Prometheus gauge.
        Values progress from 0 (NOT_STARTED) through pipeline stages,
        with terminal states at the end.

        Returns:
            Integer metric value (0-7).

        Example:
            >>> CompositePipelineState.NOT_STARTED.to_metric_value()
            0
            >>> CompositePipelineState.COMPLETED.to_metric_value()
            6
        """
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
    """Check if a state transition is valid.

    Module-level function for transition validation without accessing
    the enum instance directly.

    Args:
        current: Current pipeline state.
        target: Target state to transition to.

    Returns:
        True if transition is allowed, False otherwise.

    Example:
        >>> can_transition(
        ...     CompositePipelineState.SEED_COMPLETED,
        ...     CompositePipelineState.ENRICHING
        ... )
        True
    """
    return current.can_transition_to(target)


def validate_transition(
    current: CompositePipelineState,
    target: CompositePipelineState,
) -> None:
    """Validate a state transition, raising on invalid.

    Module-level function for transition validation that raises
    InvalidStateError on invalid transitions.

    Args:
        current: Current pipeline state.
        target: Target state to transition to.

    Raises:
        InvalidStateError: If transition is not allowed.

    Example:
        >>> validate_transition(
        ...     CompositePipelineState.NOT_STARTED,
        ...     CompositePipelineState.SEED_RUNNING
        ... )
        >>> # No exception - transition is valid
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
    return {
        state: state.allowed_transitions
        for state in CompositePipelineState
    }
