"""Incremental workflow execution metadata helpers."""

from __future__ import annotations

from bioetl.domain.workflow import WorkflowConfig, WorkflowStepConfig


def extract_incremental_metadata(
    config: WorkflowConfig,
) -> tuple[int | None, int | None]:
    """Extract incremental state from the first pipeline step."""
    for step in config.steps:
        if isinstance(step, WorkflowStepConfig):
            offset = step.run_options.start_offset
            return (0 if offset is None else offset, step.run_options.limit)
    return (None, None)


__all__ = ["extract_incremental_metadata"]
