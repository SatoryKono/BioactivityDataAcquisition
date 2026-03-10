"""Protocol for FSM helper dependency used by composite runner mixins."""

from __future__ import annotations

from typing import Protocol

from bioetl.application.composite.checkpoint import CompositeCheckpointState
from bioetl.domain.composite.state import CompositePipelineState


class FSMStateHelperPort(Protocol):
    """FSM helper contract for state validation/logging and resume handling."""

    def log_fsm_transition(
        self,
        from_state: CompositePipelineState,
        to_state: CompositePipelineState,
        stage: str,
        **extra: object,
    ) -> None: ...

    def validate_fsm_transition(
        self,
        from_state: CompositePipelineState,
        to_state: CompositePipelineState,
        allow_resume: bool = False,
    ) -> bool: ...

    def handle_resume_from_failed(
        self, state: CompositeCheckpointState
    ) -> CompositeCheckpointState: ...

    def log_resume_context(self, state: CompositeCheckpointState) -> None: ...


__all__ = ["FSMStateHelperPort"]
