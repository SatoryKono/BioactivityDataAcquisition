"""Pipeline debug port for interactive pipeline inspection.

Defines the contract for pipeline debugging and step-through execution.
Allows inspecting intermediate state at each lifecycle phase.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

__all__ = [
    "BreakpointHit",
    "DebugAction",
    "PipelineDebugPort",
    "PipelineSnapshot",
    "StageBreakpoint",
]


class StageBreakpoint(StrEnum):
    """Pipeline stages where breakpoints can be set."""

    AFTER_PREFLIGHT = "after_preflight"
    AFTER_BRONZE = "after_bronze"
    AFTER_SILVER = "after_silver"
    AFTER_GOLD = "after_gold"
    AFTER_DQ = "after_dq"
    ON_ERROR = "on_error"
    ON_QUARANTINE = "on_quarantine"


class DebugAction(StrEnum):
    """Actions available at a breakpoint."""

    CONTINUE = "continue"
    SKIP_STAGE = "skip_stage"
    INSPECT = "inspect"
    ABORT = "abort"
    DUMP_STATE = "dump_state"


@dataclass(frozen=True, slots=True)
class PipelineSnapshot:
    """Immutable snapshot of pipeline state at a breakpoint.

    Attributes:
        stage: Current lifecycle stage name.
        records_fetched: Total records fetched so far.
        records_bronze: Records written to bronze layer.
        records_silver: Records written to silver layer.
        records_gold: Records written to gold layer.
        records_quarantined: Records quarantined due to errors.
        dq_issues: Summary of data quality issues.
        sample_records: Sample records from current batch.
        metadata: Additional stage-specific metadata.
    """

    stage: str
    records_fetched: int = 0
    records_bronze: int = 0
    records_silver: int = 0
    records_gold: int = 0
    records_quarantined: int = 0
    dq_issues: dict[str, int] = field(default_factory=dict)
    sample_records: list[dict[str, Any]] = field(  # Any: raw API records
        default_factory=list
    )
    metadata: dict[str, Any] = field(  # Any: stage-specific metadata
        default_factory=dict
    )


@dataclass(frozen=True, slots=True)
class BreakpointHit:
    """Event emitted when a breakpoint is triggered.

    Attributes:
        breakpoint: Which breakpoint was hit.
        snapshot: Pipeline state at the breakpoint.
        message: Human-readable description of why breakpoint triggered.
    """

    breakpoint: StageBreakpoint
    snapshot: PipelineSnapshot
    message: str = ""


@runtime_checkable
class PipelineDebugPort(Protocol):
    """Port for interactive pipeline debugging.

    Implementations control how breakpoints are handled:
    - CLI interactive mode: prompts user for action
    - Programmatic mode: auto-continues or logs
    - Test mode: records snapshots for assertions
    """

    def is_breakpoint_enabled(self, breakpoint: StageBreakpoint) -> bool:
        """Check if a breakpoint is active.

        Args:
            breakpoint: The stage breakpoint to check.

        Returns:
            True if execution should pause at this breakpoint.
        """
        ...

    def on_breakpoint(self, hit: BreakpointHit) -> DebugAction:
        """Handle a breakpoint hit and return the action to take.

        Args:
            hit: The breakpoint event with pipeline state snapshot.

        Returns:
            Action to take (continue, skip, inspect, abort, dump).
        """
        ...

    def on_snapshot(self, snapshot: PipelineSnapshot) -> None:
        """Record a pipeline snapshot for later inspection.

        Called at each stage regardless of breakpoints.

        Args:
            snapshot: Current pipeline state snapshot.
        """
        ...
