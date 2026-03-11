"""Backward-compatible root facade for composite runner exports.

Compatibility note for architecture guards:
- FSM ownership remains in the leaf runner implementation.
- State transitions still use ``with_state(`` and ``_log_fsm_transition`` in the
  runner package implementation.
"""

from bioetl.application.composite.runner_pkg.runner import (
    CompositePipelineRunner,
    CompositePipelineRunnerService,
    CompositeRuntimeConfig,
)
from bioetl.domain.composite.state import CompositePipelineState

__all__ = [
    "CompositePipelineRunner",
    "CompositePipelineRunnerService",
    "CompositePipelineState",
    "CompositeRuntimeConfig",
]
