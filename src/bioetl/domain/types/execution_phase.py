"""Execution phases and FSM for composite pipeline execution."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from bioetl.domain.types.execution_phase_transitions import build_transition_table


class ExecutionPhase(Enum):
    """Phases of composite pipeline execution."""

    NOT_STARTED = "not_started"
    PREFLIGHT = "preflight"
    DEPENDENCY_EXECUTION = "dependency_execution"
    ENRICHMENT = "enrichment"
    MERGE = "merge"
    CROSS_VALIDATION = "cross_validation"
    WRITE_FINALIZE = "write_finalize"
    COMPLETED_SUCCESS = "completed_success"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED_VALIDATION = "failed_validation"
    FAILED_EXECUTION = "failed_execution"
    FAILED_RECOVERY = "failed_recovery"
    TERMINATED = "terminated"


class PhaseTransition(Enum):
    """Valid transitions between execution phases."""

    START_PREFLIGHT = "start_preflight"
    PREFLIGHT_TO_DEPENDENCIES = "preflight_to_dependencies"
    DEPENDENCIES_TO_ENRICHMENT = "dependencies_to_enrichment"
    ENRICHMENT_TO_MERGE = "enrichment_to_merge"
    MERGE_TO_CROSS_VALIDATION = "merge_to_cross_validation"
    CROSS_VALIDATION_TO_WRITE = "cross_validation_to_write"
    WRITE_TO_SUCCESS = "write_to_success"
    ANY_TO_FAILED = "any_to_failed"
    ANY_TO_TERMINATED = "any_to_terminated"


class TransitionPolicy(Enum):
    """Policies for phase transitions."""

    ALLOW_RETRY = "allow_retry"
    REQUIRE_COMPENSATION = "require_compensation"
    CONTINUE_DEGRADED = "continue_degraded"
    BLOCK_CONTINUATION = "block_continuation"


class ExecutionOutcome(Enum):
    """Final outcomes of composite execution."""

    SUCCESS = "success"
    SUCCESS_WITH_WARNINGS = "success_with_warnings"
    FAILED_VALIDATION = "failed_validation"
    FAILED_EXECUTION = "failed_execution"
    FAILED_RECOVERY = "failed_recovery"
    TERMINATED = "terminated"
    TIMEOUT = "timeout"


TERMINAL_PHASES = {
    ExecutionPhase.COMPLETED_SUCCESS,
    ExecutionPhase.COMPLETED_WITH_WARNINGS,
    ExecutionPhase.FAILED_VALIDATION,
    ExecutionPhase.FAILED_EXECUTION,
    ExecutionPhase.FAILED_RECOVERY,
    ExecutionPhase.TERMINATED,
}


PHASE_OUTCOME_MAP = {
    ExecutionPhase.COMPLETED_SUCCESS: ExecutionOutcome.SUCCESS,
    ExecutionPhase.COMPLETED_WITH_WARNINGS: ExecutionOutcome.SUCCESS_WITH_WARNINGS,
    ExecutionPhase.FAILED_VALIDATION: ExecutionOutcome.FAILED_VALIDATION,
    ExecutionPhase.FAILED_EXECUTION: ExecutionOutcome.FAILED_EXECUTION,
    ExecutionPhase.FAILED_RECOVERY: ExecutionOutcome.FAILED_RECOVERY,
    ExecutionPhase.TERMINATED: ExecutionOutcome.TERMINATED,
}


@dataclass(frozen=True)
class PhaseTransitionRule:
    """Rule governing a phase transition."""

    from_phase: ExecutionPhase
    to_phase: ExecutionPhase
    transition: PhaseTransition
    policy: TransitionPolicy
    requires_validation: bool = True
    allows_retry: bool = False
    compensation_required: bool = False
    degraded_mode_allowed: bool = False


@dataclass(frozen=True)
class ExecutionFSMConfig:
    """Configuration for execution FSM."""

    strict_validation: bool = True
    allow_degraded_mode: bool = False
    max_retry_attempts: int = 0
    timeout_seconds: int | None = None


class CompositeFSM:
    """Finite State Machine for composite pipeline execution."""

    def __init__(self, config: ExecutionFSMConfig | None = None):
        self.config = config or ExecutionFSMConfig()
        self.current_phase = ExecutionPhase.NOT_STARTED
        self.transition_history: list[PhaseTransition] = []
        self.transition_table: dict[ExecutionPhase, list[PhaseTransitionRule]] = {}
        self._setup_transition_table()

    def _setup_transition_table(self) -> None:
        """Setup valid phase transitions."""
        self.transition_table = build_transition_table(
            execution_phase=ExecutionPhase,
            phase_transition=PhaseTransition,
            transition_policy=TransitionPolicy,
            phase_transition_rule=PhaseTransitionRule,
        )

    def get_current_phase(self) -> ExecutionPhase:
        """Get the current execution phase."""
        return self.current_phase

    def get_transition_history(self) -> list[PhaseTransition]:
        """Get the history of phase transitions."""
        return self.transition_history

    def can_transition(
        self, transition: PhaseTransition, validation_passed: bool = True
    ) -> bool:
        """Check if a transition is allowed from current phase."""
        if self.is_terminal_state():
            return False  # Terminal states cannot transition

        valid_transitions = self.transition_table.get(self.current_phase, [])
        for rule in valid_transitions:
            if rule.transition == transition:
                return not (rule.requires_validation and not validation_passed)
        return False

    def transition(
        self, transition: PhaseTransition, validation_passed: bool = True
    ) -> ExecutionPhase:
        """Attempt to transition to a new phase."""
        if not self.can_transition(transition, validation_passed):
            raise ValueError(
                f"Invalid transition: {self.current_phase.value} -> {transition.value}"
            )

        # Find the transition rule
        valid_transitions = self.transition_table.get(self.current_phase, [])
        transition_rule = next(
            (rule for rule in valid_transitions if rule.transition == transition), None
        )

        if not transition_rule:
            raise ValueError(f"No transition rule found for {transition.value}")

        # Update state
        self.transition_history.append(transition)
        self.current_phase = transition_rule.to_phase

        return self.current_phase

    def get_valid_transitions(self) -> list[PhaseTransition]:
        """Get all valid transitions from current phase."""
        if self.is_terminal_state():
            return []  # Terminal states have no transitions

        return [
            rule.transition
            for rule in self.transition_table.get(self.current_phase, [])
        ]

    def is_terminal_state(self) -> bool:
        """Check if current phase is a terminal state."""
        return self.current_phase in TERMINAL_PHASES

    def get_execution_outcome(self) -> ExecutionOutcome | None:
        """Get the final execution outcome if in terminal state."""
        if not self.is_terminal_state():
            return None

        return PHASE_OUTCOME_MAP.get(self.current_phase)

    def reset(self) -> None:
        """Reset FSM to initial state."""
        self.current_phase = ExecutionPhase.NOT_STARTED
        self.transition_history = []


def create_composite_fsm(config: ExecutionFSMConfig | None = None) -> CompositeFSM:
    """Factory function for CompositeFSM."""
    return CompositeFSM(config)
