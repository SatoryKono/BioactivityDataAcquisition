"""Composite pipeline FSM state definitions.

Defines the finite state machine states for composite pipeline execution.
Used for checkpoint tracking and resume capability.

See ADR-026 for architectural decisions.
"""

from __future__ import annotations

from enum import Enum


class CompositePipelineState(str, Enum):
    """Finite state machine states for composite pipeline execution.

    State transitions:
    - NOT_STARTED → SEED_RUNNING (seed pipeline begins)
    - SEED_RUNNING → SEED_COMPLETED (seed pipeline finishes)
    - SEED_RUNNING → FAILED (seed pipeline fails)
    - SEED_COMPLETED → ENRICHING (enrichment begins)
    - ENRICHING → ENRICHMENT_COMPLETED (all enrichers finish)
    - ENRICHING → FAILED (critical enricher fails)
    - ENRICHMENT_COMPLETED → MERGING (merge begins)
    - MERGING → COMPLETED (merge finishes successfully)
    - MERGING → FAILED (merge fails)

    Any state can transition to FAILED on unrecoverable errors.

    Example:
        >>> state = CompositePipelineState.NOT_STARTED
        >>> state.is_terminal
        False
        >>> CompositePipelineState.COMPLETED.is_terminal
        True
    """

    NOT_STARTED = "NOT_STARTED"
    """Initial state before any execution."""

    SEED_RUNNING = "SEED_RUNNING"
    """Seed pipeline is currently executing."""

    SEED_COMPLETED = "SEED_COMPLETED"
    """Seed pipeline completed successfully."""

    ENRICHING = "ENRICHING"
    """Enrichment pipelines are running."""

    ENRICHMENT_COMPLETED = "ENRICHMENT_COMPLETED"
    """All enrichment pipelines completed."""

    MERGING = "MERGING"
    """Merge operation is in progress."""

    COMPLETED = "COMPLETED"
    """Composite pipeline finished successfully."""

    FAILED = "FAILED"
    """Composite pipeline failed with unrecoverable error."""

    @property
    def is_terminal(self) -> bool:
        """Check if this is a terminal state (no further transitions)."""
        return self in (CompositePipelineState.COMPLETED, CompositePipelineState.FAILED)

    @property
    def is_resumable(self) -> bool:
        """Check if execution can be resumed from this state.

        Resumable states have completed work that can be skipped on resume.
        """
        return self in (
            CompositePipelineState.SEED_COMPLETED,
            CompositePipelineState.ENRICHING,
            CompositePipelineState.ENRICHMENT_COMPLETED,
        )

    def to_metric_value(self) -> int:
        """Convert to numeric value for Prometheus metric.

        Higher values indicate more progress through the pipeline.
        FAILED is -1 to distinguish from NOT_STARTED.
        """
        return {
            CompositePipelineState.NOT_STARTED: 0,
            CompositePipelineState.SEED_RUNNING: 1,
            CompositePipelineState.SEED_COMPLETED: 2,
            CompositePipelineState.ENRICHING: 3,
            CompositePipelineState.ENRICHMENT_COMPLETED: 4,
            CompositePipelineState.MERGING: 5,
            CompositePipelineState.COMPLETED: 6,
            CompositePipelineState.FAILED: -1,
        }[self]

    def can_transition_to(self, target: CompositePipelineState) -> bool:
        """Check if transition to target state is valid.

        Args:
            target: Target state to transition to.

        Returns:
            True if transition is valid according to FSM rules.
        """
        # Any state can transition to FAILED
        if target == CompositePipelineState.FAILED:
            return True

        # Terminal states cannot transition
        if self.is_terminal:
            return False

        valid_transitions: dict[CompositePipelineState, set[CompositePipelineState]] = {
            CompositePipelineState.NOT_STARTED: {CompositePipelineState.SEED_RUNNING},
            CompositePipelineState.SEED_RUNNING: {
                CompositePipelineState.SEED_COMPLETED
            },
            CompositePipelineState.SEED_COMPLETED: {CompositePipelineState.ENRICHING},
            CompositePipelineState.ENRICHING: {
                CompositePipelineState.ENRICHMENT_COMPLETED
            },
            CompositePipelineState.ENRICHMENT_COMPLETED: {
                CompositePipelineState.MERGING
            },
            CompositePipelineState.MERGING: {CompositePipelineState.COMPLETED},
        }

        return target in valid_transitions.get(self, set())
