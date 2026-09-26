"""No-op implementation of PipelineDebugPort (Null Object Pattern)."""

from __future__ import annotations

from bioetl.domain.ports.runtime.pipeline_debug import (
    BreakpointHit,
    DebugAction,
    PipelineSnapshot,
    StageBreakpoint,
)

__all__ = ["NoOpDebug"]


class NoOpDebug:
    """No-op debugger that never pauses execution.

    Used in production mode where no interactive debugging is needed.
    """

    def is_breakpoint_enabled(self, breakpoint: StageBreakpoint) -> bool:
        """Always returns False — no breakpoints in production."""
        _ = breakpoint
        return False

    def on_breakpoint(self, hit: BreakpointHit) -> DebugAction:
        """Always continues — no pausing in production."""
        _ = hit
        return DebugAction.CONTINUE

    def on_snapshot(self, snapshot: PipelineSnapshot) -> None:
        """No-op — snapshots discarded in production."""
        _ = snapshot
