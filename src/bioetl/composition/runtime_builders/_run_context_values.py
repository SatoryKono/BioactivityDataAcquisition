"""Runtime context value normalization for manifest builders."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineRunContext

def resolve_run_context_values(
    ctx: PipelineRunContext,
) -> tuple[str, str]:
    """Resolve run type and execution context values from context."""
    raw_run_type = getattr(ctx, "run_type", "incremental")
    run_type_value = str(getattr(raw_run_type, "value", raw_run_type))
    raw_execution_context = getattr(ctx, "execution_context", "isolated")
    execution_context_value = str(
        getattr(raw_execution_context, "value", raw_execution_context)
    )
    return run_type_value, execution_context_value

__all__ = ["resolve_run_context_values"]
