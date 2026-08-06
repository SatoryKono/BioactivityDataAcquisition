"""Seed-phase helpers for CompositeRunnerStageMixin."""

from __future__ import annotations

from bioetl.application.composite.checkpoint import (
    CompositeCheckpointState,
    apply_recovery_checkpoint_transition,
)
from bioetl.application.composite.runner_pkg.runner_constants import (
    PIPELINE_EXECUTION_ERRORS,
)
from bioetl.application.composite.runner_pkg.runner_stage_types import (
    _CompositeRunnerStageHostProtocol,
)
from bioetl.domain.composite.result import SeedResult
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.exceptions import BioETLError

__all__ = [
    "execute_seed_phase",
    "resume_seed_phase",
    "run_seed_with_fsm",
]


def resume_seed_phase(
    host: _CompositeRunnerStageHostProtocol,
    state: CompositeCheckpointState,
) -> CompositeCheckpointState:
    """Normalize resumed seed state and emit resume logging."""
    host._logger.info(
        "Seed already completed, resuming from checkpoint",
        composite=host._config.name,
        run_id=host._run_id_str,
    )
    if state.state != CompositePipelineState.SEED_COMPLETED:
        previous_state = state.state
        state = apply_recovery_checkpoint_transition(
            state,
            CompositePipelineState.SEED_COMPLETED,
            reason="seed_resume_completed_checkpoint",
            clock=getattr(host, "_clock", None),
        )
        host._fsm.log_fsm_transition(
            from_state=previous_state,
            to_state=CompositePipelineState.SEED_COMPLETED,
            stage="seed_resume",
        )
    return state


async def run_seed_with_fsm(
    host: _CompositeRunnerStageHostProtocol,
    state: CompositeCheckpointState,
) -> tuple[CompositeCheckpointState, SeedResult]:
    """Run seed pipeline with FSM state transitions."""
    state = await host._start_seed_phase(state)

    try:
        seed_result = await host._call_run_seed()
    except (*PIPELINE_EXECUTION_ERRORS, BioETLError) as error:
        await host._handle_seed_phase_exception(state, error)
        raise

    state = await host._complete_seed_phase(state, seed_result)
    return state, seed_result


async def execute_seed_phase(
    host: _CompositeRunnerStageHostProtocol,
    state: CompositeCheckpointState,
) -> tuple[CompositeCheckpointState, SeedResult]:
    """Execute the seed phase or resume from checkpoint."""
    if not state.seed_completed:
        return await host._run_seed_with_fsm(state)

    state = host._resume_seed_phase(state)
    return state, SeedResult(pipeline_name=host._config.seed.pipeline, resumed=True)
