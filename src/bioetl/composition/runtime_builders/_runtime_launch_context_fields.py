"""Shared launch-context field extraction for runtime snapshots."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineRunContext

def build_runtime_launch_field_snapshot(
    ctx: PipelineRunContext,
    *,
    run_type_value: str,
    execution_context_value: str | None = None,
) -> dict[str, object]:
    """Extract canonical launch-context fields shared by manifest snapshots."""
    snapshot: dict[str, object] = {
        "pipeline_name": str(getattr(ctx, "pipeline_name", "unknown")),
        "run_type": run_type_value,
        "resume": getattr(ctx, "resume", False),
        "dry_run": getattr(ctx, "dry_run", False),
        "limit": getattr(ctx, "limit", None),
        "query": getattr(ctx, "query", None),
        "start_offset": getattr(ctx, "start_offset", None),
        "log_level": getattr(ctx, "log_level", "INFO"),
        "ignore_yaml_filter": getattr(ctx, "ignore_yaml_filter", False),
        "skip_gold": getattr(ctx, "skip_gold", False),
        "exact_replay": getattr(ctx, "exact_replay", False),
    }
    if execution_context_value is not None:
        snapshot["execution_context"] = execution_context_value
    return snapshot

__all__ = ["build_runtime_launch_field_snapshot"]
