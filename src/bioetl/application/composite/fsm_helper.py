"""FSM helpers for composite pipeline state transitions and resume flow."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.composite.checkpoint.transition_service import (
    apply_recovery_checkpoint_transition,
)
from bioetl.domain.ports import ClockPort

if TYPE_CHECKING:
    from bioetl.application.composite.checkpoint import CompositeCheckpointState
    from bioetl.domain.composite.config import CompositeConfig
    from bioetl.domain.composite.state import CompositePipelineState
    from bioetl.domain.ports import LoggerPort


@dataclass(frozen=True, slots=True)
class ResumePhaseInfo:
    """Resolved resume target for a failed composite checkpoint."""

    phase: CompositePipelineState
    description: str


ResumePhasePlan = ResumePhaseInfo


def _resolve_resume_phase(
    *,
    seed_completed: bool,
    completed_count: int,
    total_enrichers: int,
    merge_completed: bool,
) -> ResumePhaseInfo:
    """Resolve the FSM phase that should handle resume-from-failed."""
    from bioetl.domain.composite.state import CompositePipelineState

    if not seed_completed:
        return ResumePhaseInfo(
            phase=CompositePipelineState.NOT_STARTED,
            description="seed (seed not completed)",
        )
    if completed_count < total_enrichers:
        return ResumePhaseInfo(
            phase=CompositePipelineState.ENRICHING,
            description=(
                f"enrichment ({completed_count}/{total_enrichers} enrichers completed)"
            ),
        )
    if merge_completed:
        return ResumePhaseInfo(
            phase=CompositePipelineState.MERGING,
            description="cross_validation (merge completed)",
        )
    return ResumePhaseInfo(
        phase=CompositePipelineState.ENRICHMENT_COMPLETED,
        description="merge (all enrichers completed)",
    )


class FSMStateHelperService:
    """FSM transition, resume, and logging helper for composite execution."""

    def __init__(
        self,
        config: CompositeConfig,
        logger: LoggerPort,
        run_id: str,
    ) -> None:
        """Initialize the FSM helper."""
        self._config = config
        self._logger = logger
        self._run_id = run_id

    def log_fsm_transition(
        self,
        from_state: CompositePipelineState,
        to_state: CompositePipelineState,
        stage: str,
        **extra: object,
    ) -> None:
        """Log FSM state transition.

        Args:
            from_state: Previous FSM state.
            to_state: New FSM state.
            stage: Pipeline stage identifier (e.g., 'seed_start', 'seed_complete').
            **extra: Additional context for logging.
        """
        self._logger.info(
            "FSM state transition",
            from_state=from_state.value,
            to_state=to_state.value,
            composite=self._config.name,
            run_id=self._run_id,
            stage=stage,
            **extra,
        )

    def validate_fsm_transition(
        self,
        from_state: CompositePipelineState,
        to_state: CompositePipelineState,
        allow_resume: bool = False,
    ) -> bool:
        """Validate an FSM state transition and warn instead of failing hard."""
        from bioetl.domain.composite.state import CompositePipelineState

        if allow_resume and from_state == CompositePipelineState.FAILED:
            self._logger.debug(
                "FSM resume transition from FAILED",
                from_state=from_state.value,
                to_state=to_state.value,
                composite=self._config.name,
            )
            return True

        # Check if transition is valid according to FSM rules
        if not from_state.can_transition_to(to_state):
            self._logger.warning(
                "Invalid FSM transition detected",
                from_state=from_state.value,
                to_state=to_state.value,
                allowed_transitions=[s.value for s in from_state.allowed_transitions],
                composite=self._config.name,
                run_id=self._run_id,
                note="This may indicate a programming error in the Runner",
            )
            return False

        return True

    def handle_resume_from_failed(
        self,
        state: CompositeCheckpointState,
        *,
        clock: ClockPort | None = None,
    ) -> CompositeCheckpointState:
        """Map FAILED checkpoint state to the correct resume FSM phase."""
        total_enrichers = len(self._config.enrichers)
        completed_count = len(state.completed_enrichers)
        resume_plan = _resolve_resume_phase(
            seed_completed=state.seed_completed,
            completed_count=completed_count,
            total_enrichers=total_enrichers,
            merge_completed=state.merge_completed,
        )
        resume_phase = resume_plan.phase
        phase_description = resume_plan.description

        self._logger.info(
            "Checkpoint indicates previous failure, resuming from phase",
            composite=self._config.name,
            run_id=self._run_id,
            previous_state=state.state.value,
            resume_phase=resume_phase.value,
            phase_description=phase_description,
            seed_completed=state.seed_completed,
            completed_enrichers=completed_count,
            total_enrichers=total_enrichers,
        )

        # allow_resume=True permits transitions from terminal FAILED state.
        self.validate_fsm_transition(state.state, resume_phase, allow_resume=True)
        self.log_fsm_transition(
            from_state=state.state,
            to_state=resume_phase,
            stage="resume_from_failed",
            phase_description=phase_description,
        )

        return apply_recovery_checkpoint_transition(
            state,
            resume_phase,
            reason="resume_from_failed",
            clock=clock,
        )

    def log_resume_context(self, state: CompositeCheckpointState) -> None:
        """Log the detailed resume context for a checkpoint-backed restart."""
        total_enrichers = len(self._config.enrichers)
        completed_count = len(state.completed_enrichers)
        remaining_count = total_enrichers - completed_count

        self._logger.info(
            "Resuming from checkpoint",
            composite=self._config.name,
            run_id=self._run_id,
            last_state=state.state.value,
            seed_completed=state.seed_completed,
            completed_enrichers_count=completed_count,
            total_enrichers_count=total_enrichers,
            remaining_enrichers_count=remaining_count,
            completed_enrichers=(
                list(state.completed_enrichers) if completed_count > 0 else None
            ),
        )


__all__ = [
    "FSMStateHelperService",
    "ResumePhaseInfo",
    "ResumePhasePlan",
]
