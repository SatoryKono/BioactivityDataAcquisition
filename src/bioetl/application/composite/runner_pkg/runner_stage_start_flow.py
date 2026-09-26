"""Shared phase-start choreography for composite runner stages."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Protocol

from bioetl.application.composite.checkpoint import CompositeCheckpointState
from bioetl.application.composite.lifecycle_observer_service import (
    CompositeLifecycleObserverService,
)
from bioetl.domain.composite import CompositeConfig
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.ports import LoggerPort

__all__ = ["start_composite_phase"]


class _CompositePhaseStartHostProtocol(Protocol):
    _config: CompositeConfig
    _logger: LoggerPort
    _observer: CompositeLifecycleObserverService
    _run_id_str: str

    def _transition_state_with_fsm_log(
        self,
        state: CompositeCheckpointState,
        to_state: CompositePipelineState,
        *,
        stage: str,
        validate: bool = True,
        **transition_kwargs: object,
    ) -> CompositeCheckpointState: ...

    async def _call_save_checkpoint_safe(
        self,
        state: CompositeCheckpointState,
        operation: str,
    ) -> bool: ...


async def start_composite_phase(
    host: _CompositePhaseStartHostProtocol,
    state: CompositeCheckpointState,
    *,
    to_state: CompositePipelineState,
    stage: str,
    checkpoint_operation: str,
    phase_name: str,
    transition_details: Mapping[str, object] | None = None,
    log_details: Mapping[str, object] | None = None,
    on_started: Callable[[], None] | None = None,
) -> CompositeCheckpointState:
    """Execute the shared start choreography for one composite phase."""
    next_validate = True
    extra_transition_kwargs = dict(transition_details or {})
    validate_value = extra_transition_kwargs.pop("validate", True)
    if isinstance(validate_value, bool):
        next_validate = validate_value
    next_state = host._transition_state_with_fsm_log(
        state,
        to_state,
        stage=stage,
        validate=next_validate,
        **extra_transition_kwargs,
    )
    await host._call_save_checkpoint_safe(next_state, checkpoint_operation)
    if on_started is not None:
        on_started()
    host._observer.emit_phase_started(
        composite_name=host._config.name,
        run_id=host._run_id_str,
        phase_name=phase_name,
        details=dict(log_details or {}),
    )
    return next_state
